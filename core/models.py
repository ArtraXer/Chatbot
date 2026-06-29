# CATÁLOGO COMPLETO DE MODELOS NVIDIA NIM
# Actualizado: Junio 2026
# Fuente: https://build.nvidia.com/models
# 140+ modelos disponibles en diferentes categorías

MODELOS_NVIDIA = {
    # ============================================================
    # MODELOS DE PROPÓSITO GENERAL / REASONING (Recomendados)
    # ============================================================
    "general": {
        "minimax": [
            {
                "id": "minimaxai/minimax-m3",
                "nombre": "MiniMax M3 Preview",
                "descripcion": "Multimodal MoE con reasoning, coding y tool-calling avanzados",
                "parametros": "230B",
                "contexto": "32K tokens",
                "endpoint_gratis": True,
                "casos_uso": ["reasoning", "coding", "tool-calling"]
            },
            {
                "id": "minimaxai/minimax-m2.7",
                "nombre": "MiniMax M2.7",
                "descripcion": "Modelo text-to-text con excelente rendimiento en coding y reasoning",
                "parametros": "230B",
                "contexto": "32K tokens",
                "endpoint_gratis": True,
                "casos_uso": ["reasoning", "coding", "office_tasks"]
            }
        ],
        "deepseek": [
            {
                "id": "deepseek-ai/deepseek-r1-distill-llama-70b",
                "nombre": "DeepSeek R1 Distill Llama 70B",
                "descripcion": "Versión destilada de R1 con reasoning avanzado",
                "parametros": "70B",
                "contexto": "128K tokens",
                "endpoint_gratis": True,
                "casos_uso": ["reasoning", "math", "coding"]
            },
            {
                "id": "deepseek-ai/deepseek-v4-pro",
                "nombre": "DeepSeek V4 Pro",
                "descripcion": "Modelo MoE con 1M context para coding y agentes",
                "parametros": "284B (MoE)",
                "contexto": "1M tokens",
                "endpoint_gratis": True,
                "casos_uso": ["coding", "agentic", "long_context"]
            },
            {
                "id": "deepseek-ai/deepseek-v4-flash",
                "nombre": "DeepSeek V4 Flash",
                "descripcion": "Versión rápida de DeepSeek V4",
                "parametros": "284B (MoE)",
                "contexto": "1M tokens",
                "endpoint_gratis": True,
                "casos_uso": ["coding", "fast_inference"]
            },
            {
                "id": "deepseek-ai/deepseek-3.2-exp",
                "nombre": "DeepSeek 3.2 Exp",
                "descripcion": "DeepSeek 3.2 Experimental con capacidades mejoradas",
                "parametros": "37B",
                "contexto": "32K tokens",
                "endpoint_gratis": True,
                "casos_uso": ["code_generation", "chat"]
            }
        ],
        "glm": [
            {
                "id": "z-ai/glm-5.1",
                "nombre": "GLM-5.1",
                "descripcion": "Flagship LLM para workflows agentic, coding y reasoning",
                "parametros": "744B",
                "contexto": "200K tokens",
                "endpoint_gratis": False,
                "casos_uso": ["agentic_ai", "coding", "reasoning"]
            },
            {
                "id": "z-ai/glm-4.7",
                "nombre": "GLM-4.7",
                "descripcion": "Modelo multilingüe con soporte para function calling",
                "parametros": "100B",
                "contexto": "128K tokens",
                "endpoint_gratis": True,
                "casos_uso": ["multilingual", "function_calling"]
            }
        ],
        "qwen": [
            {
                "id": "qwen/qwen-3.5-72b",
                "nombre": "Qwen 3.5 72B",
                "descripcion": "Modelo capaz con reasoning mejorado",
                "parametros": "72B",
                "contexto": "128K tokens",
                "endpoint_gratis": True,
                "casos_uso": ["general", "reasoning"]
            },
            {
                "id": "qwen/qwen-3-coder-480b",
                "nombre": "Qwen 3 Coder 480B",
                "descripcion": "Modelo especializado para coding y agentic workflows",
                "parametros": "480B",
                "contexto": "64K tokens",
                "endpoint_gratis": True,
                "casos_uso": ["coding", "agentic"]
            }
        ],
        "kimi": [
            {
                "id": "moonshotai/kimi-k2.6",
                "nombre": "Kimi K2.6",
                "descripcion": "Modelo MoE 1T con long-horizon coding y tool use",
                "parametros": "1T",
                "contexto": "200K tokens",
                "endpoint_gratis": False,
                "casos_uso": ["multimodal", "coding", "tool_use"]
            },
            {
                "id": "moonshotai/kimi-k2.5",
                "nombre": "Kimi K2.5",
                "descripcion": "Versión anterior con context windows largos",
                "parametros": "200B+",
                "contexto": "200K tokens",
                "endpoint_gratis": True,
                "casos_uso": ["long_context", "tool_use"]
            }
        ],
        "mistral": [
            {
                "id": "mistralai/mistral-large-2",
                "nombre": "Mistral Large 2",
                "descripcion": "SOTA general purpose model",
                "parametros": "675B",
                "contexto": "128K tokens",
                "endpoint_gratis": True,
                "casos_uso": ["general", "coding", "reasoning"]
            },
            {
                "id": "mistralai/mistral-medium-3.5-128b",
                "nombre": "Mistral Medium 3.5 128B",
                "descripcion": "Modelo de alto rendimiento para text generation y coding",
                "parametros": "128B",
                "contexto": "128K tokens",
                "endpoint_gratis": True,
                "casos_uso": ["coding", "text_generation", "agentic"]
            },
            {
                "id": "mistralai/mixtral-8x22b",
                "nombre": "Mixtral 8x22B",
                "descripcion": "Modelo MoE eficiente con soporte function calling",
                "parametros": "141B (MoE)",
                "contexto": "65K tokens",
                "endpoint_gratis": True,
                "casos_uso": ["efficient", "coding", "function_calling"]
            }
        ],
        "meta_llama": [
            {
                "id": "meta/llama-4-maverick-70b",
                "nombre": "Meta Llama 4 Maverick 70B",
                "descripcion": "Último modelo de Meta con capabilities mejoradas",
                "parametros": "70B",
                "contexto": "128K tokens",
                "endpoint_gratis": True,
                "casos_uso": ["general", "reasoning", "coding"]
            },
            {
                "id": "meta/llama-3.1-405b",
                "nombre": "Meta Llama 3.1 405B",
                "descripcion": "El modelo abierto más grande con 405B parámetros",
                "parametros": "405B",
                "contexto": "128K tokens",
                "endpoint_gratis": False,
                "casos_uso": ["frontier_reasoning", "coding", "multilingual"]
            },
            {
                "id": "meta/llama-3.1-70b",
                "nombre": "Meta Llama 3.1 70B",
                "descripcion": "Balance óptimo entre rendimiento y velocidad",
                "parametros": "70B",
                "contexto": "128K tokens",
                "endpoint_gratis": True,
                "casos_uso": ["general", "coding", "reasoning"]
            },
            {
                "id": "meta/llama-3.1-8b",
                "nombre": "Meta Llama 3.1 8B",
                "descripcion": "Modelo ligero y rápido para edge/mobile",
                "parametros": "8B",
                "contexto": "128K tokens",
                "endpoint_gratis": True,
                "casos_uso": ["edge", "fast_inference", "mobile"]
            },
            {
                "id": "meta/llama-3.3-70b",
                "nombre": "Meta Llama 3.3 70B",
                "descripcion": "Versión mejorada de Llama 3.1 70B",
                "parametros": "70B",
                "contexto": "128K tokens",
                "endpoint_gratis": True,
                "casos_uso": ["general", "coding", "function_calling"]
            }
        ],
        "nvidia_nemotron": [
            {
                "id": "nvidia/nemotron-3-ultra-550b-a55b",
                "nombre": "Nemotron 3 Ultra 550B",
                "descripcion": "Hybrid Mamba-Transformer MoE con 1M context",
                "parametros": "550B (MoE)",
                "contexto": "1M tokens",
                "endpoint_gratis": False,
                "casos_uso": ["agentic_reasoning", "coding", "planning", "tool_calling"]
            },
            {
                "id": "nvidia/nemotron-3.5-super-120b",
                "nombre": "Nemotron 3.5 Super 120B",
                "descripcion": "Modelo eficiente que solo activa 12B parámetros",
                "parametros": "120B (solo 12B activos)",
                "contexto": "128K tokens",
                "endpoint_gratis": True,
                "casos_uso": ["efficient_inference", "coding"]
            }
        ]
    },
    
    # ============================================================
    # MODELOS MULTIMODALES
    # ============================================================
    "multimodal": {
        "vision_language": [
            {
                "id": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
                "nombre": "Nemotron 3 Nano Omni 30B",
                "descripcion": "Modelo omni-modal que entiende imágenes, vídeo, speech y texto",
                "parametros": "30B",
                "contexto": "128K tokens",
                "endpoint_gratis": True,
                "casos_uso": ["image_to_text", "video_understanding", "speech"]
            },
            {
                "id": "moonshotai/kimi-k2.6",
                "nombre": "Kimi K2.6 Multimodal",
                "descripcion": "Multimodal MoE para video y text understanding",
                "parametros": "1T",
                "contexto": "200K tokens",
                "endpoint_gratis": False,
                "casos_uso": ["video_understanding", "image_understanding"]
            },
            {
                "id": "minimaxai/minimax-m3",
                "nombre": "MiniMax M3 (Vision)",
                "descripcion": "Multimodal MoE con capabilidades de vision",
                "parametros": "230B",
                "contexto": "32K tokens",
                "endpoint_gratis": True,
                "casos_uso": ["multimodal", "vision", "reasoning"]
            }
        ],
        "text_to_image": [
            {
                "id": "qwen/qwen-image",
                "nombre": "Qwen-Image",
                "descripcion": "Modelo text-to-image con renderizado multilingual mejorado",
                "parametros": "-",
                "contexto": "-",
                "endpoint_gratis": False,
                "casos_uso": ["text_to_image", "multilingual_text_rendering"]
            },
            {
                "id": "qwen/qwen-image-edit",
                "nombre": "Qwen-Image-Edit",
                "descripcion": "Modelo de edición de imágenes con text editing multilingual",
                "parametros": "-",
                "contexto": "-",
                "endpoint_gratis": True,
                "casos_uso": ["image_editing", "text_editing"]
            }
        ]
    },
    
    # ============================================================
    # MODELOS ESPECIALIZADOS
    # ============================================================
    "especializados": {
        "coding": [
            {
                "id": "stepfun-ai/step-3.7-flash",
                "nombre": "Step 3.7 Flash",
                "descripcion": "Sparse MoE multimodal para enterprise y coding",
                "parametros": "-",
                "contexto": "-",
                "endpoint_gratis": True,
                "casos_uso": ["coding", "enterprise", "agentic"]
            }
        ],
        "ocr": [
            {
                "id": "nvidia/nemotron-ocr-v2",
                "nombre": "Nemotron OCR v2",
                "descripcion": "Modelo multilingual para reconocimiento de texto",
                "parametros": "-",
                "contexto": "-",
                "endpoint_gratis": True,
                "casos_uso": ["ocr", "text_recognition", "table_extraction"]
            }
        ],
        "content_safety": [
            {
                "id": "nvidia/nemotron-3.5-content-safety",
                "nombre": "Nemotron 3.5 Content Safety",
                "descripcion": "Modelo multilingual y multimodal para detectar contenido unsafe",
                "parametros": "-",
                "contexto": "-",
                "endpoint_gratis": True,
                "casos_uso": ["safety", "moderation", "content_filtering"]
            },
            {
                "id": "nvidia/nemotron-3-content-safety",
                "nombre": "Nemotron 3 Content Safety",
                "descripcion": "Versión anterior mejorada para safety",
                "parametros": "-",
                "contexto": "-",
                "endpoint_gratis": True,
                "casos_uso": ["safety", "moderation"]
            }
        ],
        "video": [
            {
                "id": "nvidia/cosmos3-nano",
                "nombre": "Cosmos 3 Nano",
                "descripcion": "Genera vídeos physics-aware desde prompts o imágenes",
                "parametros": "-",
                "contexto": "-",
                "endpoint_gratis": True,
                "casos_uso": ["video_generation", "autonomous_vehicles"]
            },
            {
                "id": "nvidia/cosmos3-nano-reasoner",
                "nombre": "Cosmos 3 Nano Reasoner",
                "descripcion": "Vision language model para entender videos/imágenes con reasoning",
                "parametros": "-",
                "contexto": "-",
                "endpoint_gratis": True,
                "casos_uso": ["video_understanding", "reasoning"]
            },
            {
                "id": "nvidia/synthetic-video-detector",
                "nombre": "Synthetic Video Detector",
                "descripcion": "Detecta vídeos AI-generados (sintéticos)",
                "parametros": "-",
                "contexto": "-",
                "endpoint_gratis": True,
                "casos_uso": ["deepfake_detection", "broadcast"]
            },
            {
                "id": "nvidia/active-speaker-detection",
                "nombre": "Active Speaker Detection",
                "descripcion": "Detecta y trackea identidades de speakers en vídeo",
                "parametros": "-",
                "contexto": "-",
                "endpoint_gratis": False,
                "casos_uso": ["speaker_detection", "broadcast"]
            },
            {
                "id": "nvidia/lipsync",
                "nombre": "LipSync",
                "descripcion": "Sincroniza labios en vídeo con audio (lip dubbing)",
                "parametros": "-",
                "contexto": "-",
                "endpoint_gratis": True,
                "casos_uso": ["video_editing", "broadcast"]
            },
            {
                "id": "nvidia/relighting",
                "nombre": "Relighting",
                "descripcion": "Re-ilumina personas en vídeo con lighting target",
                "parametros": "-",
                "contexto": "-",
                "endpoint_gratis": True,
                "casos_uso": ["video_editing", "hdri"]
            }
        ],
        "speech": [
            {
                "id": "resembleai/chatterbox-multilingual-tts",
                "nombre": "Chatterbox Multilingual TTS",
                "descripcion": "Voces naturales y expresivas en 23 idiomas",
                "parametros": "-",
                "contexto": "-",
                "endpoint_gratis": True,
                "casos_uso": ["tts", "voice_agents", "multilingual"]
            }
        ],
        "quantum": [
            {
                "id": "nvidia/ising-calibration-1-35b-a3b",
                "nombre": "Ising Calibration 1 35B",
                "descripcion": "Open VLM para quantum computer calibration",
                "parametros": "35B",
                "contexto": "-",
                "endpoint_gratis": True,
                "casos_uso": ["quantum", "chart_understanding"]
            }
        ]
    },
    
    # ============================================================
    # MODELOS ADICIONALES (Google, Otros Proveedores)
    # ============================================================
    "otros_proveedores": {
        "google": [
            {
                "id": "google/diffusiongemma-26b-a4b-it",
                "nombre": "Diffusion Gemma 26B",
                "descripcion": "Diffusion-based LLM para parallel token generation",
                "parametros": "26B",
                "contexto": "8K tokens",
                "endpoint_gratis": True,
                "casos_uso": ["diffusion_llm", "real_time_text"]
            }
        ]
    }
}

# ============================================================
# LISTAS DE ACCESO RÁPIDO
# ============================================================

MODELOS_POR_CASO_USO = {
    "general": [
        "mistralai/mistral-large-2",
        "meta/llama-3.1-70b",
        "meta/llama-4-maverick-70b",
        "qwen/qwen-3.5-72b"
    ],
    "coding": [
        "deepseek-ai/deepseek-v4-flash",
        "qwen/qwen-3-coder-480b",
        "mistralai/mistral-medium-3.5-128b",
        "meta/llama-3.1-70b"
    ],
    "reasoning": [
        "deepseek-ai/deepseek-r1-distill-llama-70b",
        "minimax/minimax-m2.7",
        "z-ai/glm-5.1",
        "mistralai/mistral-large-2"
    ],
    "agentic": [
        "nvidia/nemotron-3-ultra-550b-a55b",
        "z-ai/glm-5.1",
        "moonshotai/kimi-k2.6",
        "meta/llama-3.3-70b"
    ],
    "multimodal": [
        "minimax/minimax-m3",
        "moonshotai/kimi-k2.6",
        "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
    ],
    "long_context": [
        "deepseek-ai/deepseek-v4-pro",
        "moonshotai/kimi-k2.6",
        "meta/llama-3.1-405b"
    ],
    "edge": [
        "meta/llama-3.1-8b",
        "nvidia/nemotron-3.5-super-120b"
    ],
    "ocr": [
        "nvidia/nemotron-ocr-v2"
    ],
    "video": [
        "nvidia/cosmos3-nano",
        "nvidia/cosmos3-nano-reasoner"
    ],
    "tts": [
        "resembleai/chatterbox-multilingual-tts"
    ]
}

MODELOS_GRATIS = [
    "meta/llama-3.1-8b-instruct",
    "meta/llama-3.1-70b-instruct",
    "meta/llama-3.3-70b-instruct",
    "mistralai/mistral-large-2-instruct",
    "nvidia/nemotron-4-340b-instruct",
    "deepseek-ai/deepseek-v4-flash",
    "minimaxai/minimax-m2.7",
    "minimaxai/minimax-m3",
    "google/diffusiongemma-26b-a4b-it",
    "stepfun-ai/step-3.7-flash"
]

# ============================================================
# FUNCIONES DE UTILIDAD
# ============================================================

def obtener_modelo(modelo_id):
    """
    Obtiene información detallada de un modelo por su ID.
    
    Args:
        modelo_id: ID del modelo (ej: 'meta/llama-3.1-70b')
        
    Returns:
        Dict con información del modelo o None si no existe
    """
    for categoria, subcategorias in MODELOS_NVIDIA.items():
        if isinstance(subcategorias, dict):
            for subcategoria, modelos in subcategorias.items():
                if isinstance(modelos, list):
                    for modelo in modelos:
                        if modelo.get("id") == modelo_id:
                            return modelo
    return None

def listar_modelos_por_categoria(categoria):
    """
    Lista todos los modelos de una categoría.
    
    Args:
        categoria: Nombre de la categoría ('general', 'multimodal', etc)
        
    Returns:
        Lista de modelos en esa categoría
    """
    if categoria not in MODELOS_NVIDIA:
        return []
    
    resultados = []
    subcategorias = MODELOS_NVIDIA[categoria]
    
    for subcategoria, modelos in subcategorias.items():
        if isinstance(modelos, list):
            resultados.extend(modelos)
    
    return resultados

def filtrar_modelos_gratis():
    """
    Retorna solo los modelos con endpoint gratis.
    
    Returns:
        Lista de modelos gratis
    """
    modelos_gratis_lista = []
    for modelo_id in MODELOS_GRATIS:
        modelo = obtener_modelo(modelo_id)
        if modelo:
            modelos_gratis_lista.append(modelo)
    return modelos_gratis_lista

def obtener_modelos_por_uso(caso_uso):
    """
    Obtiene modelos recomendados para un caso de uso específico.
    
    Args:
        caso_uso: Caso de uso ('coding', 'reasoning', 'general', etc)
        
    Returns:
        Lista de modelos recomendados
    """
    if caso_uso not in MODELOS_POR_CASO_USO:
        return []
    
    resultados = []
    for modelo_id in MODELOS_POR_CASO_USO[caso_uso]:
        modelo = obtener_modelo(modelo_id)
        if modelo:
            resultados.append(modelo)
    
    return resultados

def buscar_modelos(query):
    """
    Busca modelos por nombre o descripción.
    
    Args:
        query: Texto a buscar
        
    Returns:
        Lista de modelos que coinciden
    """
    query_lower = query.lower()
    resultados = []
    
    for categoria, subcategorias in MODELOS_NVIDIA.items():
        if isinstance(subcategorias, dict):
            for subcategoria, modelos in subcategorias.items():
                if isinstance(modelos, list):
                    for modelo in modelos:
                        if (query_lower in modelo.get("nombre", "").lower() or 
                            query_lower in modelo.get("descripcion", "").lower() or
                            query_lower in modelo.get("id", "").lower()):
                            resultados.append(modelo)
    
    return resultados

def obtener_estadisticas():
    """
    Retorna estadísticas del catálogo de modelos.
    
    Returns:
        Dict con conteos y estadísticas
    """
    total_modelos = 0
    modelos_gratis_count = len(MODELOS_GRATIS)
    categorias = {}
    
    for categoria, subcategorias in MODELOS_NVIDIA.items():
        if isinstance(subcategorias, dict):
            for subcategoria, modelos in subcategorias.items():
                if isinstance(modelos, list):
                    total_modelos += len(modelos)
                    if categoria not in categorias:
                        categorias[categoria] = 0
                    categorias[categoria] += len(modelos)
    
    return {
        "total_modelos": total_modelos,
        "modelos_gratis": modelos_gratis_count,
        "modelos_pagos": total_modelos - modelos_gratis_count,
        "categorias": categorias,
        "porcentaje_gratis": round((modelos_gratis_count / total_modelos * 100), 2) if total_modelos > 0 else 0
    }