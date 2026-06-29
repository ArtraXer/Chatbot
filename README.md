# Artraxer AI Agent Premium

Un entorno de desarrollo integrado (IDE) impulsado por Inteligencia Artificial, diseñado para trabajar como un agente programador autónomo. Utiliza modelos avanzados a través de la API de NVIDIA NIM para leer, escribir, y ejecutar código directamente en tu sistema de manera interactiva.

## Características

*   **Agente Autónomo:** Ejecuta instrucciones como crear archivos, carpetas, buscar en la web y ejecutar comandos en terminal.
*   **Integración con NVIDIA NIM:** Soporte multi-modelo para los LLMs más avanzados del mercado (Llama 3.1 70B, DeepSeek, Mistral Large, etc.).
*   **Editor y Visor de Código:** Previsualización de archivos en tiempo real con sintaxis resaltada y explorador de archivos tipo árbol.
*   **Prevención de Errores (Safety):** El usuario debe confirmar cualquier acción destructiva o modificación de archivos existentes.
*   **Diseño Premium UI:** Interfaz construida en Python con `customtkinter`, ofreciendo un tema oscuro profesional y responsivo.

## Requisitos

*   Python 3.10 o superior
*   Clave de API de NVIDIA (`NVIDIA_API_KEY`)
*   Librerías principales: `customtkinter`, `openai`, `pygments`

## Instalación y Ejecución

1.  Clona este repositorio o descarga los archivos.
2.  Instala las dependencias necesarias.
3.  Asegúrate de que la variable de entorno `NVIDIA_API_KEY` esté configurada en tu sistema.
4.  Ejecuta el programa principal:

```bash
python main.py
```

## Estructura de Archivos

*   `main.py`: Punto de entrada de la aplicación y lógica de la Interfaz Gráfica (UI).
*   `agente.py`: Lógica del agente LLM, prompts del sistema y parsing de comandos.
*   `herramientas.py`: Funciones de sistema que el agente utiliza para interactuar con tu PC (leer/escribir archivos, ejecutar comandos).
*   `modelos.py`: Catálogo validado de modelos de NVIDIA NIM compatibles con la aplicación.
*   `iconos.py`: Gestión de iconos visuales para el explorador de archivos.
