import os
import re
import logging
import json
import time
from typing import Generator, List, Dict, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Lock
import traceback

from openai import OpenAI, APIError, APIConnectionError, RateLimitError

logger = logging.getLogger(__name__)


@dataclass
class ConversacionMemoria:
    """Gestor robusto de memoria con límites y persistencia"""
    
    mensajes: List[Dict] = field(default_factory=list)
    max_mensajes: int = 20  # Mantener últimos 20 turnos
    max_tokens_estimados: int = 2000
    directorio_cache: Path = field(default_factory=lambda: Path.home() / ".cache/chatbot")
    lock: Lock = field(default_factory=Lock)
    
    def __post_init__(self):
        self.directorio_cache.mkdir(parents=True, exist_ok=True)
    
    def agregar_mensaje(self, rol: str, contenido: str) -> bool:
        """Agrega mensaje con validación de límites"""
        
        with self.lock:  # ✅ Thread-safe
            # Validar entrada
            if not contenido or not isinstance(contenido, str):
                return False
            
            contenido = contenido.strip()
            if not contenido:
                return False
            
            if rol not in ["user", "assistant", "system"]:
                raise ValueError(f"Rol inválido: {rol}")
            
            # Estimar tokens (1 token ≈ 4 caracteres)
            tokens_nuevos = len(contenido) // 4
            tokens_totales = sum(len(m.get("content", "")) // 4 for m in self.mensajes)
            
            # Si excede límite, borrar mensajes antiguos
            if tokens_totales + tokens_nuevos > self.max_tokens_estimados:
                # Mantener últimos 5 mensajes + el nuevo
                self.mensajes = self.mensajes[-5:] if len(self.mensajes) > 5 else self.mensajes
            
            self.mensajes.append({
                "role": rol,
                "content": contenido,
                "timestamp": datetime.now().isoformat()
            })
            
            # Mantener límite de mensajes
            if len(self.mensajes) > self.max_mensajes:
                self.mensajes = self.mensajes[-self.max_mensajes:]
            
            logger.debug(
                f"Mensaje agregado - rol: {rol}, "
                f"mensajes totales: {len(self.mensajes)}, "
                f"tokens estimados: {self._contar_tokens()}"
            )
            
            return True
    
    def obtener_contexto(self) -> List[Dict]:
        """Retorna mensajes para API (sin timestamps)"""
        with self.lock:
            return [
                {"role": m["role"], "content": m["content"]}
                for m in self.mensajes
            ]
    
    def _contar_tokens(self) -> int:
        """Cuenta tokens estimados"""
        return sum(len(m.get("content", "")) // 4 for m in self.mensajes)
    
    def limpiar(self):
        """Limpia memoria"""
        with self.lock:
            self.mensajes = []
        logger.info("Memoria limpiada")
    
    def guardar_snapshot(self, nombre: str = "conversacion") -> str:
        """Persiste conversación para recuperación"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            ruta = self.directorio_cache / f"{nombre}_{timestamp}.json"
            
            with open(ruta, 'w', encoding='utf-8') as f:
                json.dump(self.mensajes, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Snapshot guardado: {ruta}")
            return str(ruta)
        except Exception as e:
            logger.exception("Error guardando snapshot")
            return ""
    
    def get_stats(self) -> Dict:
        """Estadísticas de memoria"""
        with self.lock:
            tokens = self._contar_tokens()
            return {
                "mensajes": len(self.mensajes),
                "tokens_estimados": tokens,
                "porcentaje_lleno": (tokens / self.max_tokens_estimados) * 100,
                "sistema_ok": tokens < self.max_tokens_estimados
            }


class ParserAcciones:
    """Parser robusto de acciones del agente"""
    
    PATRON_ARCHIVO = re.compile(
        r'^ARCHIVO:\s*([^\n]+)\n(.*?)(?=^(?:ARCHIVO:|CARPETA:|COMANDO:)|\Z)',
        re.MULTILINE | re.DOTALL | re.IGNORECASE
    )
    
    PATRON_CARPETA = re.compile(
        r'^CARPETA:\s*([^\n]+)',
        re.MULTILINE | re.IGNORECASE
    )
    
    PATRON_COMANDO = re.compile(
        r'^COMANDO:\s*(leer|ejecutar|buscar_web)\s+([^\n]+)',
        re.MULTILINE | re.IGNORECASE
    )
    
    @dataclass
    class Comando:
        tipo: str  # 'archivo', 'carpeta', 'comando'
        parametro: str
        contenido: Optional[str] = None
    
    @classmethod
    def parsear(cls, texto: str) -> List['ParserAcciones.Comando']:
        """Parsea texto y extrae comandos"""
        comandos = []
        
        # Parsear ARCHIVO
        for match in cls.PATRON_ARCHIVO.finditer(texto):
            ruta = match.group(1).strip().strip('`*"')
            contenido = match.group(2).strip()
            
            # Limpiar bloques markdown
            contenido = re.sub(r'^```[\w]*\n?', '', contenido)
            contenido = re.sub(r'\n?```$', '', contenido)
            
            # Validar
            if ruta and len(ruta) < 255 and '..' not in ruta:
                comandos.append(cls.Comando(
                    tipo='archivo',
                    parametro=ruta,
                    contenido=contenido
                ))
        
        # Parsear CARPETA
        for match in cls.PATRON_CARPETA.finditer(texto):
            carpeta = match.group(1).strip().strip('`*"')
            if carpeta and '..' not in carpeta:
                comandos.append(cls.Comando(
                    tipo='carpeta',
                    parametro=carpeta
                ))
        
        # Parsear COMANDO
        for match in cls.PATRON_COMANDO.finditer(texto):
            accion = match.group(1).lower()
            param = match.group(2).strip().strip('`"')
            
            if param:
                comandos.append(cls.Comando(
                    tipo='comando',
                    parametro=accion,
                    contenido=param
                ))
        
        logger.debug(f"Parser: {len(comandos)} comandos encontrados")
        return comandos


class AgenteIA:
    """Agente IA con reintentos y manejo robusto de errores"""
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://integrate.api.nvidia.com/v1",
        max_reintentos: int = 3
    ):
        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=30.0
        )
        self.memoria = ConversacionMemoria()
        self.max_reintentos = max_reintentos
        self.instrucciones_extra = ""
    
    def set_instrucciones(self, texto: str):
        """Establece instrucciones extra para el agente"""
        self.instrucciones_extra = texto
    
    def pensar(
        self,
        mensaje: str,
        modelo: str = "meta/llama-3.1-8b-instruct",
        check_cancel: Optional[Callable] = None,
        callback_confirmar: Optional[Callable] = None,
        callback_terminal: Optional[Callable] = None
    ) -> Generator[Tuple[str, bool, Optional[Tuple]], None, None]:
        """
        Genera respuesta con reintentos y manejo de errores.
        
        Yields:
            (fragmento, terminado, comando_output)
        """
        
        # ✅ Validar entrada
        if not mensaje or not isinstance(mensaje, str):
            yield "❌ Mensaje vacío o inválido", True, None
            return
        
        if len(mensaje) > 10000:
            yield "❌ Mensaje muy largo (>10k caracteres)", True, None
            return
        
        self.memoria.agregar_mensaje("user", mensaje)
        
        # ✅ Reintentos con backoff exponencial
        for intento in range(self.max_reintentos):
            try:
                respuesta = self._llamar_api(modelo)
                yield from self._procesar_stream(
                    respuesta,
                    check_cancel,
                    callback_confirmar,
                    callback_terminal
                )
                return  # ✅ Éxito
            
            except RateLimitError:
                wait_time = (2 ** intento) * 5
                logger.warning(f"Rate limit (intento {intento+1}). Esperando {wait_time}s...")
                
                if intento == self.max_reintentos - 1:
                    yield f"⏱️ Límite de rata excedido. Intente en 1 minuto.", True, None
                else:
                    time.sleep(wait_time)
            
            except APIConnectionError as e:
                logger.error(f"Conexión fallida (intento {intento+1}): {e}")
                
                if intento == self.max_reintentos - 1:
                    yield "🔌 Error de conexión. Verifique su internet.", True, None
                else:
                    time.sleep(2 ** intento)
            
            except APIError as e:
                if e.status_code == 401:
                    yield "🔑 Error de autenticación. Verifique API key.", True, None
                    return
                elif e.status_code == 400:
                    yield f"❌ Solicitud inválida: {str(e)[:100]}", True, None
                    return
                else:
                    logger.error(f"API error {e.status_code}: {e}")
                    if intento == self.max_reintentos - 1:
                        yield f"❌ Error API: {str(e)[:100]}", True, None
            
            except Exception as e:
                logger.exception("Error inesperado en pensar()")
                if intento == self.max_reintentos - 1:
                    yield f"❌ Error inesperado: {type(e).__name__}", True, None
    
    def _llamar_api(self, modelo: str):
        """Llamada a API con timeout"""
        return self.client.chat.completions.create(
            model=modelo,
            messages=self.memoria.obtener_contexto(),
            max_tokens=1024,
            stream=True,
            temperature=0.7
        )
    
    def _procesar_stream(
        self,
        respuesta,
        check_cancel,
        callback_confirmar,
        callback_terminal
    ) -> Generator:
        """Procesa stream con validación de chunks"""
        
        texto_completo = ""
        
        try:
            for chunk in respuesta:
                # ✅ Chequear cancelación
                if check_cancel and check_cancel():
                    yield "\n[Cancelado por usuario]", False, None
                    return
                
                try:
                    # ✅ Validar chunk
                    if not chunk.choices or len(chunk.choices) == 0:
                        continue
                    
                    delta = chunk.choices[0].delta
                    if not delta or not hasattr(delta, 'content'):
                        continue
                    
                    if delta.content:
                        texto_completo += delta.content
                        yield delta.content, False, None
                
                except (AttributeError, IndexError) as e:
                    logger.warning(f"Chunk malformado: {e}")
                    continue
            
            # ✅ Guardar en memoria
            self.memoria.agregar_mensaje("assistant", texto_completo)
            
            # ✅ Procesar acciones
            comandos = ParserAcciones.parsear(texto_completo)
            comando_output = self._ejecutar_comandos(
                comandos,
                callback_confirmar,
                callback_terminal
            )
            
            yield "", True, comando_output
        
        except Exception as e:
            logger.exception("Error procesando stream")
            yield f"❌ Error en stream: {type(e).__name__}", True, None
    
    def _ejecutar_comandos(
        self,
        comandos: List[ParserAcciones.Comando],
        callback_confirmar,
        callback_terminal
    ) -> Tuple[str, bool]:
        """Ejecuta comandos con seguridad"""
        
        from herramientas_v2 import (
            escribir_archivo, crear_carpeta, leer_archivo, ejecutar_comando, buscar_web
        )
        
        respuestas = []
        requiere_respuesta = False
        
        for cmd in comandos:
            try:
                if cmd.tipo == 'archivo':
                    # Archivo existente?
                    from pathlib import Path as PathlibPath
                    ruta_completa = PathlibPath(os.getcwd()) / cmd.parametro
                    
                    if ruta_completa.exists() and callback_confirmar:
                        # Pedir confirmación
                        aceptado = callback_confirmar(cmd.parametro, cmd.contenido)
                        if not aceptado:
                            respuestas.append(f"⚠️ Modificación de {cmd.parametro} rechazada")
                            continue
                    
                    resultado = escribir_archivo(cmd.parametro, cmd.contenido or "")
                    respuestas.append(resultado)
                
                elif cmd.tipo == 'carpeta':
                    resultado = crear_carpeta(cmd.parametro)
                    respuestas.append(resultado)
                
                elif cmd.tipo == 'comando':
                    if cmd.parametro == 'leer':
                        resultado = leer_archivo(cmd.contenido)
                        respuestas.append(f"Contenido de {cmd.contenido}:\n{resultado}")
                        requiere_respuesta = True
                    
                    elif cmd.parametro == 'ejecutar':
                        resultado = ejecutar_comando(cmd.contenido, callback_terminal)
                        respuestas.append(f"Salida de '{cmd.contenido}':\n{resultado}")
                        requiere_respuesta = True
                    
                    elif cmd.parametro == 'buscar_web':
                        resultado = buscar_web(cmd.contenido)
                        respuestas.append(f"Resultados de '{cmd.contenido}':\n{resultado}")
                        requiere_respuesta = True
            
            except Exception as e:
                logger.exception(f"Error ejecutando comando {cmd.tipo}")
                respuestas.append(f"❌ Error en {cmd.tipo}: {type(e).__name__}")
        
        if respuestas:
            return "\n\n".join(respuestas), requiere_respuesta
        
        return None, False
    
    def get_memoria_stats(self) -> Dict:
        """Obtiene estadísticas de memoria"""
        return self.memoria.get_stats()
    
    def limpiar_memoria(self):
        """Limpia memoria conversación"""
        self.memoria.limpiar()
    
    def guardar_sesion(self, nombre: str = "sesion") -> str:
        """Guarda sesión actual"""
        return self.memoria.guardar_snapshot(nombre)