# Artraxer AI Agent Premium

Un entorno de desarrollo integrado (IDE) impulsado por IA para trabajar como agente programador autónomo. El proyecto combina una interfaz moderna con una capa de herramientas segura para leer, escribir, ejecutar comandos y gestionar archivos de forma controlada.

## Qué mejora se aplicó

- Se consolidó la lógica de seguridad en una implementación reutilizable y compatible.
- Se preservó la interfaz pública original para no romper el flujo actual del proyecto.
- Se añadió una guía de configuración básica y un ejemplo de variables de entorno.
- Se dejó la base preparada para crecer con nuevos módulos sin romper la arquitectura existente.

## Requisitos

- Python 3.10 o superior
- Clave de API de NVIDIA en la variable de entorno NVIDIA_API_KEY
- Dependencias principales: customtkinter, openai, pygments, duckduckgo-search

## Instalación

1. Clona este repositorio.
2. Instala las dependencias:
   ```bash
   pip install customtkinter openai pygments duckduckgo-search
   ```
3. Copia el archivo de ejemplo de entorno:
   ```bash
   cp .env.example .env
   ```
4. Completa tu NVIDIA_API_KEY en el archivo .env.
5. Ejecuta la aplicación:
   ```bash
   python main.py
   ```

## Estructura del proyecto

- main.py: punto de entrada principal y wrapper compatible con la UI.
- agente.py: wrapper de compatibilidad hacia la capa de runtime del agente.
- herramientas.py: wrapper de compatibilidad hacia la capa de servicios seguros.
- herramientas_v2.py: implementación de referencia para operaciones seguras del sistema.
- modelos.py: catálogo de modelos NVIDIA NIM.
- iconos.py: mapeo visual de iconos por tipo de archivo.
- core/: capa interna por responsabilidades (seguridad, servicios, runtime y modelos).
- ui/: capa de presentación y experiencia de usuario.

## Verificación

La base fue revisada con la suite de pruebas disponible:

```bash
python -m unittest discover -s tests -q
```
