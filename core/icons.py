# Mapeo de extensiones a (emoji, color) para todos los tipos de archivo comunes
ICONOS_ARCHIVOS = {
    # Lenguajes de Programación
    ".py": ("🐍", "#2ecc71"),        # Python - Verde
    ".js": ("📜", "#f1c40f"),        # JavaScript - Amarillo
    ".ts": ("📘", "#3498db"),        # TypeScript - Azul
    ".tsx": ("⚛️", "#61dafb"),       # React TypeScript - Cian
    ".jsx": ("⚛️", "#61dafb"),       # React - Cian
    ".java": ("☕", "#e74c3c"),       # Java - Rojo
    ".cpp": ("⚙️", "#9b59b6"),       # C++ - Púrpura
    ".c": ("🔧", "#1abc9c"),         # C - Turquesa
    ".h": ("📋", "#95a5a6"),         # Header - Gris
    ".go": ("🐹", "#00add8"),        # Go - Azul claro
    ".rs": ("🦀", "#ce422b"),        # Rust - Rojo oscuro
    ".rb": ("💎", "#cc342d"),        # Ruby - Rojo
    ".php": ("🐘", "#777bb4"),       # PHP - Púrpura
    ".swift": ("🍎", "#fa7343"),     # Swift - Naranja
    ".kt": ("🅺", "#7f52ff"),        # Kotlin - Púrpura
    ".scala": ("📊", "#dc322f"),     # Scala - Rojo
    ".r": ("📈", "#276dc3"),         # R - Azul
    ".sql": ("🗄️", "#336791"),       # SQL - Azul oscuro
    ".sh": ("🐚", "#4eaa25"),        # Shell/Bash - Verde
    ".bash": ("🐚", "#4eaa25"),      # Bash - Verde
    ".zsh": ("🐚", "#1e90ff"),       # Zsh - Azul
    ".fish": ("🐠", "#4e90e1"),      # Fish - Azul
    ".pl": ("🐪", "#39457e"),        # Perl - Azul oscuro
    ".lua": ("🌙", "#000080"),       # Lua - Azul marino
    ".groovy": ("🔷", "#1e90ff"),    # Groovy - Azul
    ".gradle": ("🔶", "#02303a"),    # Gradle - Verde oscuro
    ".maven": ("🟫", "#d1003f"),     # Maven - Rojo
    
    # Web y Markup
    ".html": ("🌐", "#e67e22"),      # HTML - Naranja
    ".css": ("🎨", "#3498db"),       # CSS - Azul
    ".scss": ("🌈", "#c6538c"),      # SCSS - Rosa
    ".sass": ("🌈", "#c6538c"),      # SASS - Rosa
    ".less": ("◀️", "#1d365d"),       # LESS - Azul oscuro
    ".xml": ("📝", "#ffb13d"),       # XML - Amarillo oscuro
    ".svg": ("🖼️", "#ffb13d"),       # SVG - Amarillo
    ".wxml": ("📱", "#09b83e"),      # WeChat WXML - Verde
    ".vue": ("💚", "#42b983"),       # Vue - Verde
    ".jsx": ("⚛️", "#61dafb"),       # JSX - Cian
    
    # Configuración y Datos
    ".json": ("📋", "#ecf0f1"),      # JSON - Blanco grisáceo
    ".yaml": ("📑", "#cb171e"),      # YAML - Rojo
    ".yml": ("📑", "#cb171e"),       # YML - Rojo
    ".toml": ("🔨", "#9c4221"),      # TOML - Marrón
    ".ini": ("⚙️", "#34495e"),       # INI - Gris
    ".cfg": ("⚙️", "#34495e"),       # CONFIG - Gris
    ".conf": ("⚙️", "#34495e"),      # CONF - Gris
    ".env": ("🔐", "#2c3e50"),       # ENV - Gris oscuro
    ".properties": ("⚙️", "#34495e"), # Properties - Gris
    ".gradle": ("🔶", "#02303a"),    # Gradle - Verde oscuro
    ".xml": ("📝", "#ffb13d"),       # XML - Amarillo
    ".csv": ("📊", "#92c900"),       # CSV - Verde lima
    ".tsv": ("📊", "#92c900"),       # TSV - Verde lima
    ".parquet": ("📦", "#5091cd"),   # Parquet - Azul
    ".protobuf": ("🔹", "#3d7197"),  # Protocol Buffers - Azul
    ".proto": ("🔹", "#3d7197"),     # Proto - Azul
    
    # Documentos
    ".pdf": ("📕", "#d32f2f"),       # PDF - Rojo
    ".doc": ("📘", "#1f497d"),       # Word - Azul
    ".docx": ("📘", "#1f497d"),      # Word - Azul
    ".xls": ("📗", "#217346"),       # Excel - Verde
    ".xlsx": ("📗", "#217346"),      # Excel - Verde
    ".ppt": ("📙", "#d24726"),       # PowerPoint - Rojo
    ".pptx": ("📙", "#d24726"),      # PowerPoint - Rojo
    ".txt": ("📄", "#bdc3c7"),       # Texto - Gris
    ".md": ("📋", "#083fa1"),        # Markdown - Azul
    ".markdown": ("📋", "#083fa1"),  # Markdown - Azul
    ".rst": ("📜", "#0099cc"),       # ReStructuredText - Azul
    ".tex": ("📕", "#008000"),       # LaTeX - Verde
    ".odt": ("📄", "#0099ff"),       # OpenDocument - Azul
    
    # Multimedia
    ".mp3": ("🎵", "#1db954"),       # MP3 - Verde
    ".mp4": ("🎬", "#ff6b6b"),       # MP4 - Rojo
    ".avi": ("🎬", "#ff6b6b"),       # AVI - Rojo
    ".mkv": ("🎬", "#ff6b6b"),       # MKV - Rojo
    ".mov": ("🎬", "#a2aaad"),       # MOV - Gris
    ".webm": ("🎬", "#0099cc"),      # WebM - Azul
    ".flv": ("🎬", "#e74c3c"),       # FLV - Rojo
    ".wav": ("🔊", "#00a1ff"),       # WAV - Azul
    ".flac": ("🎶", "#f1c40f"),      # FLAC - Amarillo
    ".aac": ("🎵", "#1db954"),       # AAC - Verde
    ".ogg": ("🎵", "#f38630"),       # OGG - Naranja
    ".m4a": ("🎵", "#555555"),       # M4A - Gris
    ".jpg": ("🖼️", "#e67e22"),       # JPEG - Naranja
    ".jpeg": ("🖼️", "#e67e22"),      # JPEG - Naranja
    ".png": ("🖼️", "#3498db"),       # PNG - Azul
    ".gif": ("🎞️", "#f1c40f"),       # GIF - Amarillo
    ".bmp": ("🖼️", "#95a5a6"),       # BMP - Gris
    ".svg": ("🖌️", "#ffb13d"),       # SVG - Amarillo
    ".webp": ("🖼️", "#2b7489"),      # WebP - Azul oscuro
    ".ico": ("🎯", "#9b59b6"),       # ICO - Púrpura
    ".tiff": ("📸", "#e74c3c"),      # TIFF - Rojo
    
    # Comprimidos y Archivos
    ".zip": ("📦", "#f39c12"),       # ZIP - Naranja
    ".rar": ("📦", "#c0392b"),       # RAR - Rojo oscuro
    ".7z": ("📦", "#e67e22"),        # 7Z - Naranja
    ".tar": ("📦", "#c0392b"),       # TAR - Rojo
    ".gz": ("📦", "#27ae60"),        # GZIP - Verde
    ".bz2": ("📦", "#2980b9"),       # BZIP2 - Azul
    ".xz": ("📦", "#8e44ad"),        # XZ - Púrpura
    ".tgz": ("📦", "#34495e"),       # TAR.GZ - Gris
    
    # Ejecutables
    ".exe": ("⚡", "#0078d4"),       # EXE - Azul
    ".msi": ("📥", "#0078d4"),       # MSI - Azul
    ".dmg": ("🍎", "#a2aaad"),       # DMG - Gris
    ".app": ("🍎", "#555555"),       # APP - Gris
    ".deb": ("🐧", "#d70751"),       # DEB - Rojo
    ".rpm": ("🎩", "#e82609"),       # RPM - Rojo oscuro
    ".apk": ("📱", "#3ddc84"),       # APK - Verde
    ".jar": ("☕", "#e74c3c"),       # JAR - Rojo
    
    # Versionamiento
    ".git": ("🔀", "#f34f29"),       # Git - Rojo
    ".gitignore": ("👻", "#34495e"), # Gitignore - Gris
    ".gitmodules": ("🔗", "#f34f29"), # Git Modules - Rojo
    
    # Docker
    ".dockerfile": ("🐳", "#2496ed"), # Dockerfile - Azul
    "dockerfile": ("🐳", "#2496ed"),  # Dockerfile - Azul
    ".docker": ("🐳", "#2496ed"),     # Docker - Azul
    
    # Otros
    ".log": ("📋", "#95a5a6"),       # Log - Gris
    ".tmp": ("🗑️", "#7f8c8d"),       # Temporal - Gris
    ".bak": ("💾", "#2980b9"),       # Backup - Azul
    ".cache": ("💾", "#95a5a6"),     # Cache - Gris
    ".min.js": ("⚡", "#f1c40f"),     # Minificado JS - Amarillo
    ".min.css": ("⚡", "#3498db"),    # Minificado CSS - Azul
    ".map": ("🗺️", "#e74c3c"),       # Source Map - Rojo
    ".lock": ("🔒", "#c0392b"),      # Lock - Rojo oscuro
    ".d.ts": ("📘", "#3498db"),      # TypeScript Declarations - Azul
    ".spec.ts": ("🧪", "#9b59b6"),   # Test - Púrpura
    ".test.ts": ("🧪", "#9b59b6"),   # Test - Púrpura
    ".spec.js": ("🧪", "#9b59b6"),   # Test - Púrpura
    ".test.js": ("🧪", "#9b59b6"),   # Test - Púrpura
    ".e2e.ts": ("🧪", "#9b59b6"),    # E2E Test - Púrpura
    ".env.example": ("🔐", "#2c3e50"), # ENV Example - Gris oscuro
    ".editorconfig": ("✏️", "#34495e"), # Editor Config - Gris
    ".eslintrc": ("✔️", "#7cb342"),   # ESLint Config - Verde
    ".prettierrc": ("✨", "#e91e63"), # Prettier Config - Rosa
    ".npmrc": ("📦", "#cb3837"),      # NPM Config - Rojo
    ".yarnrc": ("📦", "#2c8ebb"),     # Yarn Config - Azul
    ".nvmrc": ("🔢", "#68a063"),      # NVM Config - Verde
    ".ruby-version": ("💎", "#cc342d"), # Ruby Version - Rojo
    ".python-version": ("🐍", "#2ecc71"), # Python Version - Verde
    ".travis.yml": ("✅", "#3eaaaf"), # Travis CI - Azul
    ".github": ("🐙", "#1f1f1f"),    # GitHub - Negro
    "makefile": ("🔨", "#b08968"),   # Makefile - Marrón
    "dockerfile": ("🐳", "#2496ed"), # Dockerfile - Azul
    ".license": ("📜", "#27ae60"),    # License - Verde
    ".readme": ("📖", "#1f497d"),     # README - Azul
}

def obtener_icono(nombre_archivo):
    """
    Obtiene el emoji y color para un archivo basado en su extensión.
    
    Args:
        nombre_archivo: El nombre del archivo (ej: 'script.py')
        
    Returns:
        Tupla (emoji, color_hex)
    """
    nombre_lower = nombre_archivo.lower()
    
    # Primero intenta con la extensión completa (ej: .min.js)
    for ext in [".min.js", ".min.css", ".d.ts", ".spec.ts", ".test.ts", ".spec.js", ".test.js", ".e2e.ts", ".env.example"]:
        if nombre_lower.endswith(ext):
            return ICONOS_ARCHIVOS.get(ext, ("📄", "#bdc3c7"))
    
    # Luego intenta con extensiones de dos partes (ej: .tar.gz)
    partes = nombre_lower.split(".")
    if len(partes) > 2:
        ext_compuesta = f".{partes[-2]}.{partes[-1]}"
        if ext_compuesta in ICONOS_ARCHIVOS:
            return ICONOS_ARCHIVOS[ext_compuesta]
    
    # Intenta con nombres especiales (Dockerfile, Makefile, etc)
    if nombre_lower in ICONOS_ARCHIVOS:
        return ICONOS_ARCHIVOS[nombre_lower]
    
    # Intenta con la extensión simple
    if len(partes) > 1:
        ext = f".{partes[-1]}"
        if ext in ICONOS_ARCHIVOS:
            return ICONOS_ARCHIVOS[ext]
    
    # Por defecto
    return ("📄", "#bdc3c7")