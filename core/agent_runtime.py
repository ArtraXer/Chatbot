import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

from openai import APIConnectionError, APIError, OpenAI, RateLimitError

from core.services import workspace_service

logger = logging.getLogger(__name__)


@dataclass
class ConversacionMemoria:
    """Gestor robusto de memoria con límites."""

    mensajes: List[Dict] = field(default_factory=list)
    max_mensajes: int = 20
    max_tokens_estimados: int = 2000
    lock: Lock = field(default_factory=Lock)

    def agregar_mensaje(self, rol: str, contenido: str) -> bool:
        with self.lock:
            if not contenido or not isinstance(contenido, str):
                return False
            contenido = contenido.strip()
            if not contenido or rol not in {"user", "assistant", "system"}:
                return False

            tokens_nuevos = len(contenido) // 4
            tokens_totales = sum(len(m.get("content", "")) // 4 for m in self.mensajes)
            if tokens_totales + tokens_nuevos > self.max_tokens_estimados:
                self.mensajes = self.mensajes[-5:] if len(self.mensajes) > 5 else self.mensajes

            self.mensajes.append({"role": rol, "content": contenido, "timestamp": datetime.now().isoformat()})
            if len(self.mensajes) > self.max_mensajes:
                self.mensajes = self.mensajes[-self.max_mensajes :]
            return True

    def obtener_contexto(self) -> List[Dict]:
        with self.lock:
            return [{"role": m["role"], "content": m["content"]} for m in self.mensajes]

    def limpiar(self) -> None:
        with self.lock:
            self.mensajes = []

    def get_size(self) -> int:
        with self.lock:
            return sum(len(m.get("content", "")) // 4 for m in self.mensajes)


_memoria = ConversacionMemoria()
instrucciones_extra = ""
_cliente_openai = None


def _init_cliente() -> OpenAI:
    global _cliente_openai
    if _cliente_openai is None:
        _cliente_openai = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=os.environ.get("NVIDIA_API_KEY", ""),
            timeout=30.0,
        )
    return _cliente_openai


def limpiar_memoria() -> None:
    _memoria.limpiar()
    logger.info("Memoria limpiada")


def get_memoria_size() -> int:
    return _memoria.get_size()


def set_instrucciones(texto: str) -> None:
    global instrucciones_extra
    instrucciones_extra = texto


def pensar(
    mensaje: str,
    modelo: str = "meta/llama-3.1-8b-instruct",
    check_cancel: Optional[Callable[[], bool]] = None,
    callback_confirmar_archivo: Optional[Callable[[str, str], bool]] = None,
    callback_terminal: Optional[Callable[[str], None]] = None,
) -> Generator[Tuple[str, bool, Any], None, None]:
    global _memoria, instrucciones_extra

    if not mensaje or not isinstance(mensaje, str):
        yield "❌ Mensaje vacío", True, None
        return
    if len(mensaje) > 10000:
        yield "❌ Mensaje muy largo (>10k caracteres)", True, None
        return

    _memoria.agregar_mensaje("user", mensaje)

    arbol = workspace_service.tree()
    directorio_actual = workspace_service.get_base_dir()

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

    if not _memoria.mensajes or _memoria.mensajes[0]["role"] != "system":
        with _memoria.lock:
            _memoria.mensajes.insert(0, {"role": "system", "content": contexto})
    else:
        with _memoria.lock:
            _memoria.mensajes[0]["content"] = contexto

    for intento in range(3):
        try:
            cliente = _init_cliente()
            respuesta = cliente.chat.completions.create(
                model=modelo,
                messages=_memoria.obtener_contexto(),
                max_tokens=1024,
                stream=True,
                temperature=0.7,
            )
            yield from _procesar_stream(respuesta, check_cancel, callback_confirmar_archivo, callback_terminal)
            return
        except RateLimitError:
            wait_time = (2 ** intento) * 5
            logger.warning("Rate limit (intento %s). Esperando %ss...", intento + 1, wait_time)
            if intento == 2:
                yield "⏱️ Límite de rata excedido. Intente en 1 minuto.", True, None
            else:
                time.sleep(wait_time)
        except APIConnectionError as exc:
            logger.error("Conexión fallida (intento %s): %s", intento + 1, exc)
            if intento == 2:
                yield "🔌 Error de conexión. Verifique internet.", True, None
            else:
                time.sleep(2 ** intento)
        except APIError as exc:
            if getattr(exc, "status_code", None) == 401:
                yield "🔑 Error de autenticación. Verifique API key.", True, None
                return
            if getattr(exc, "status_code", None) == 400:
                yield f"❌ Solicitud inválida: {str(exc)[:100]}", True, None
                return
            logger.error("API error %s: %s", getattr(exc, "status_code", None), exc)
            if intento == 2:
                yield f"❌ Error API: {str(exc)[:100]}", True, None
        except Exception as exc:
            logger.exception("Error inesperado en pensar()")
            if intento == 2:
                yield f"❌ Error inesperado: {type(exc).__name__}", True, None


def _procesar_stream(respuesta, check_cancel, callback_confirmar, callback_terminal) -> Generator:
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
                if not delta or not hasattr(delta, "content"):
                    continue
                if delta.content:
                    texto_completo += delta.content
                    yield delta.content, False, None
            except (AttributeError, IndexError) as exc:
                logger.warning("Chunk malformado: %s", exc)
                continue

        _memoria.agregar_mensaje("assistant", texto_completo)
        comando_output = procesar_acciones(texto_completo, callback_confirmar, callback_terminal)
        yield "", True, comando_output
    except Exception as exc:
        logger.exception("Error procesando stream")
        yield f"❌ Error en stream: {type(exc).__name__}", True, None


def procesar_acciones(texto, callback_confirmar_archivo, callback_terminal):
    respuestas = []
    requiere_respuesta = False

    bloques_archivos = re.split(r"(?i)\*?\*?ARCHIVO:\*?\*?\s*", texto)
    for bloque in bloques_archivos[1:]:
        datos = bloque.split("\n", 1)
        if len(datos) == 2:
            nombre = datos[0].replace("`", "").replace("*", "").strip()
            codigo = datos[1].replace("</pensar>", "").strip()
            if codigo.startswith("```"):
                partes = codigo.split("\n```")
                if len(partes) > 1:
                    codigo = partes[0].split("\n", 1)[-1]
            codigo = codigo.strip()

            ruta_completa = workspace_service.resolve_path(nombre)
            if ruta_completa.exists() and callback_confirmar_archivo:
                aceptado = callback_confirmar_archivo(nombre, codigo)
                if aceptado:
                    workspace_service.write_text(nombre, codigo)
                    respuestas.append(f"He modificado el archivo '{nombre}'")
            else:
                workspace_service.write_text(nombre, codigo)
                respuestas.append(f"He creado el archivo '{nombre}'")

    for linea in texto.split("\n"):
        linea_stripped = linea.strip()

        match_carpeta = re.search(r"\*?\*?CARPETA:\*?\*?\s*[\`\*]?(.+?)[\`\*]?$", linea_stripped, re.IGNORECASE)
        if match_carpeta:
            carpeta = match_carpeta.group(1).strip()
            if carpeta:
                res = workspace_service.make_dir(carpeta)
                respuestas.append(f"He ejecutado la creación de carpeta. Resultado:\n{res}")

        match_leer = re.search(r"\*?\*?COMANDO:\s*leer\s*[\`\*]?(.+?)[\`\*]?$", linea_stripped, re.IGNORECASE)
        if match_leer:
            archivo = match_leer.group(1).strip()
            contenido = workspace_service.read_text(archivo)
            respuestas.append(f"He leído '{archivo}'. Contenido:\n\n{contenido}")
            requiere_respuesta = True

        match_web = re.search(r"\*?\*?COMANDO:\s*buscar_web\s*[\`\*]?(.+?)[\`\*]?$", linea_stripped, re.IGNORECASE)
        if match_web:
            consulta = match_web.group(1).strip()
            resultado = buscar_web(consulta)
            respuestas.append(f"He buscado en la web '{consulta}'. Resultados:\n\n{resultado}")
            requiere_respuesta = True

        match_ejec = re.search(r"\*?\*?COMANDO:\s*ejecutar\s*[\`\*]?(.+?)[\`\*]?$", linea_stripped, re.IGNORECASE)
        if match_ejec:
            comando = match_ejec.group(1).strip()
            resultado = workspace_service.run_command(comando, callback_terminal)
            respuestas.append(f"He ejecutado '{comando}'. Resultado:\n{resultado}")
            requiere_respuesta = True

    if respuestas:
        return "\n\n".join(respuestas), requiere_respuesta
    return None, False


def buscar_web(consulta: str) -> str:
    try:
        if not consulta or len(consulta) > 500:
            return "No se encontraron resultados en la web."
        from duckduckgo_search import DDGS

        resultados = []
        with DDGS() as ddgs:
            for resultado in ddgs.text(consulta, max_results=3):
                titulo = resultado.get("title", "Sin título")
                url = resultado.get("href", "")
                cuerpo = resultado.get("body", "")
                resultados.append(f"[{titulo}]({url})\n{cuerpo}\n")
        if not resultados:
            return "No se encontraron resultados en la web."
        return "\n".join(resultados)
    except ImportError:
        return "No se encontraron resultados en la web."
    except Exception as exc:
        logger.error("Error buscando %s: %s", consulta, exc)
        return "No se encontraron resultados en la web."
