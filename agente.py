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

from openai import OpenAI, APIError, APIConnectionError, RateLimitError

logger = logging.getLogger(__name__)

# ============================================================
# CLASE INTERNA - Gestión de memoria
# ============================================================

@dataclass
class ConversacionMemoria:
    """Gestor robusto de memoria con límites"""
    
    mensajes: List[Dict] = field(default_factory=list)
    max_mensajes: int = 20
    max_tokens_estimados: int = 2000
    lock: Lock = field(default_factory=Lock)
    
    def agregar_mensaje(self, rol: str, contenido: str) -> bool:
        """Agrega mensaje con validación"""
        with self.lock:
            if not contenido or not isinstance(contenido, str):
                return False
            
            contenido = contenido.strip()
            if not contenido or rol not in ["user", "assistant", "system"]:
                return False
            
            # Estimar tokens
            tokens_nuevos = len(contenido) // 4
            tokens_totales = sum(len(m.get("content", "")) // 4 for m in self.mensajes)
            
            # Si excede límite, borrar antiguos
            if tokens_totales + tokens_nuevos > self.max_tokens_estimados:
                self.mensajes = self.mensajes[-5:] if len(self.mensajes) > 5 else self.mensajes
            
            self.mensajes.append({
                "role": rol,
                "content": contenido,
                "timestamp": datetime.now().isoformat()
            })
            
            if len(self.mensajes) > self.max_mensajes:
                self.mensajes = self.mensajes[-self.max_mensajes:]
            
            return True
    
    def obtener_contexto(self) -> List[Dict]:
        """Retorna mensajes para API"""
        with self.lock:
            return [
                {"role": m["role"], "content": m["content"]}
                for m in self.mensajes
            ]
    
    def limpiar(self):
        """Limpia memoria"""
        with self.lock:
            self.mensajes = []
    
    def get_size(self) -> int:
        """Retorna tamaño estimado en tokens"""
        with self.lock:
            return sum(len(m.get("content", "")) // 4 for m in self.mensajes)


# ============================================================
# VARIABLES GLOBALES (API compatible con original)
# ============================================================

_memoria = ConversacionMemoria()
instrucciones_extra = ""
_cliente_openai = None


def _init_cliente():
    """Inicializa cliente OpenAI (lazy init)"""
    global _cliente_openai
    if _cliente_openai is None:
        _cliente_openai = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=os.environ.get("NVIDIA_API_KEY", ""),
            timeout=30.0
        )
    return _cliente_openai


# ============================================================
# FUNCIONES PÚBLICAS (mismo interface que original)
# ============================================================

def limpiar_memoria():
    """Limpia la memoria conversación"""
    global _memoria
    _memoria.limpiar()
    logger.info("Memoria limpiada")


def get_memoria_size() -> int:
    """Obtiene tamaño estimado de memoria en tokens"""
    global _memoria
    return _memoria.get_size()


def set_instrucciones(texto: str):
    """Establece instrucciones extra para el agente"""
    global instrucciones_extra
    instrucciones_extra = texto


def pensar(
    mensaje: str,
    modelo: str = "meta/llama-3.1-8b-instruct",
    check_cancel: Optional[Callable] = None,
    callback_confirmar_archivo: Optional[Callable] = None,
    callback_terminal: Optional[Callable] = None
) -> Generator[Tuple[str, bool, Any], None, None]:
    """
    FUNCIÓN PRINCIPAL - Genera respuesta del agente
    
    Yields:
        (fragmento, terminado, comando_output)
    
    Mantiene API original pero con mejoras internas:
    - Reintentos automáticos
    - Manejo robusto de errores
    - Memory-safe
    """
    
    global _memoria, instrucciones_extra
    
    # Validar entrada
    if not mensaje or not isinstance(mensaje, str):
        yield "❌ Mensaje vacío", True, None
        return
    
    if len(mensaje) > 10000:
        yield "❌ Mensaje muy largo (>10k caracteres)", True, None
        return
    
    _memoria.agregar_mensaje("user", mensaje)
    
    # Contexto del agente (igual que original)
    from herramientas import listar_arbol, get_directorio_base
    
    arbol = listar_arbol()
    directorio_actual = get_directorio_base()

    contexto = f"""Eres un agente programador autónomo. Tu directorio de trabajo es: {directorio_actual}

ÁRBOL ACTUAL DEL PROYECTO:
{arbol}

============================================================
SISTEMA DE COMANDOS — USA ESTAS PALABRAS CLAVE EXACTAS
============================================================
Para ejecutar una acción REAL, debes escribir la palabra clave en su propia línea.
Si solo describes lo que harías, NO se ejecutará absolutamente nada.

CREAR CARPETA — escribe exactamente en una línea:
CARPETA: nombre_carpeta

CREAR O EDITAR ARCHIVO — escribe exactamente:
ARCHIVO: ruta/relativa/archivo.ext
(contenido del archivo aquí, sin bloques ```markdown```)

Ejemplo: para crear proyecto/index.html:
ARCHIVO: proyecto/index.html
<!DOCTYPE html>
<html><body><h1>Hola</h1></body></html>

LEER ARCHIVO:
COMANDO: leer ruta/archivo.py

EJECUTAR COMANDO DEL SISTEMA:
COMANDO: ejecutar git status

BUSCAR EN INTERNET:
COMANDO: buscar_web consulta aquí

============================================================
REGLAS OBLIGATORIAS:
- SIEMPRE emite los comandos de arriba para realizar acciones reales.
- NUNCA escribas "voy a crear..." o "he creado..." sin haber escrito el comando CARPETA: o ARCHIVO:.
- Si el usuario dice "dentro de proyecto", la ruta DEBE ser "proyecto/index.html", NO solo "index.html".
- El código va DIRECTAMENTE después de ARCHIVO:, sin bloques ```markdown```.
- Piensa dentro de <pensar>...</pensar> y luego emite el comando.
- Cuando acabes, confirma brevemente y DETENTE.
============================================================

INSTRUCCIONES EXTRA DEL USUARIO:
{instrucciones_extra}"""

    # Actualizar sistema message
    if not _memoria.mensajes or _memoria.mensajes[0]["role"] != "system":
        with _memoria.lock:
            _memoria.mensajes.insert(0, {"role": "system", "content": contexto})
    else:
        with _memoria.lock:
            _memoria.mensajes[0]["content"] = contexto
    
    # Reintentos con backoff exponencial
    max_reintentos = 3
    for intento in range(max_reintentos):
        try:
            cliente = _init_cliente()
            respuesta = cliente.chat.completions.create(
                model=modelo,
                messages=_memoria.obtener_contexto(),
                max_tokens=1024,
                stream=True,
                temperature=0.7
            )
            
            # Procesar stream
            yield from _procesar_stream(respuesta, check_cancel, callback_confirmar_archivo, callback_terminal)
            return  # ✅ Éxito
        
        except RateLimitError:
            wait_time = (2 ** intento) * 5
            logger.warning(f"Rate limit (intento {intento+1}). Esperando {wait_time}s...")
            
            if intento == max_reintentos - 1:
                yield f"⏱️ Límite de rata excedido. Intente en 1 minuto.", True, None
            else:
                time.sleep(wait_time)
        
        except APIConnectionError as e:
            logger.error(f"Conexión fallida (intento {intento+1}): {e}")
            
            if intento == max_reintentos - 1:
                yield "🔌 Error de conexión. Verifique internet.", True, None
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
                if intento == max_reintentos - 1:
                    yield f"❌ Error API: {str(e)[:100]}", True, None
        
        except Exception as e:
            logger.exception("Error inesperado en pensar()")
            if intento == max_reintentos - 1:
                yield f"❌ Error inesperado: {type(e).__name__}", True, None


def _procesar_stream(respuesta, check_cancel, callback_confirmar, callback_terminal) -> Generator:
    """Procesa stream con validación"""
    
    global _memoria
    texto_completo = ""
    
    try:
        for chunk in respuesta:
            if check_cancel and check_cancel():
                yield "\n[Cancelado por usuario]", False, None
                return
            
            try:
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
        
        # Guardar en memoria
        _memoria.agregar_mensaje("assistant", texto_completo)
        
        # Procesar acciones
        comando_output = procesar_acciones(
            texto_completo,
            callback_confirmar,
            callback_terminal
        )
        
        yield "", True, comando_output
    
    except Exception as e:
        logger.exception("Error procesando stream")
        yield f"❌ Error en stream: {type(e).__name__}", True, None


# ============================================================
# PROCESAMIENTO DE ACCIONES (igual que original)
# ============================================================

def procesar_acciones(texto, callback_confirmar_archivo, callback_terminal):
    """Procesa comandos ARCHIVO, CARPETA, COMANDO"""
    
    from herramientas import (
        escribir_archivo, crear_carpeta, leer_archivo, 
        ejecutar_comando, buscar_web, get_directorio_base
    )
    
    respuestas = []
    requiere_respuesta = False

    # Procesar ARCHIVO
    bloques_archivos = re.split(r"(?i)\*?\*?ARCHIVO:\*?\*?\s*", texto)
    for bloque in bloques_archivos[1:]:
        datos = bloque.split("\n", 1)
        if len(datos) == 2:
            nombre = datos[0].replace("`", "").replace("*", "").strip()
            codigo = datos[1].replace("</pensar>", "").strip()
            
            # Limpiar bloques markdown
            if codigo.startswith("```"):
                partes = codigo.split("\n```")
                if len(partes) > 1:
                    codigo = partes[0].split("\n", 1)[-1]
            codigo = codigo.strip()
            
            # Comprobar si existe
            ruta_completa = os.path.join(get_directorio_base(), nombre)
            if os.path.exists(ruta_completa) and callback_confirmar_archivo:
                aceptado = callback_confirmar_archivo(nombre, codigo)
                if aceptado:
                    escribir_archivo(nombre, codigo)
                    respuestas.append(f"He modificado el archivo '{nombre}'")
            else:
                escribir_archivo(nombre, codigo)
                respuestas.append(f"He creado el archivo '{nombre}'")
            
    # Procesar COMANDO y CARPETA
    lineas = texto.split('\n')
    for linea in lineas:
        linea_stripped = linea.strip()
        
        # CARPETA
        match_carpeta = re.search(r"\*?\*?CARPETA:\*?\*?\s*[`\*]?(.+?)[`\*]?$", linea_stripped, re.IGNORECASE)
        if match_carpeta:
            carpeta = match_carpeta.group(1).strip()
            if carpeta:
                res = crear_carpeta(carpeta)
                respuestas.append(f"He ejecutado la creación de carpeta. Resultado:\n{res}")
        
        # LEER
        match_leer = re.search(r"\*?\*?COMANDO:\s*leer\s*[`\*]?(.+?)[`\*]?$", linea_stripped, re.IGNORECASE)
        if match_leer:
            archivo = match_leer.group(1).strip()
            contenido = leer_archivo(archivo)
            respuestas.append(f"He leído '{archivo}'. Contenido:\n\n{contenido}")
            requiere_respuesta = True
        
        # BUSCAR WEB
        match_web = re.search(r"\*?\*?COMANDO:\s*buscar_web\s*[`\*]?(.+?)[`\*]?$", linea_stripped, re.IGNORECASE)
        if match_web:
            consulta = match_web.group(1).strip()
            resultado = buscar_web(consulta)
            respuestas.append(f"He buscado en la web '{consulta}'. Resultados:\n\n{resultado}")
            requiere_respuesta = True
        
        # EJECUTAR
        match_ejec = re.search(r"\*?\*?COMANDO:\s*ejecutar\s*[`\*]?(.+?)[`\*]?$", linea_stripped, re.IGNORECASE)
        if match_ejec:
            comando = match_ejec.group(1).strip()
            resultado = ejecutar_comando(comando, callback_terminal)
            respuestas.append(f"He ejecutado '{comando}'. Resultado:\n{resultado}")
            requiere_respuesta = True
    
    if respuestas:
        return "\n\n".join(respuestas), requiere_respuesta
    
    return None, False