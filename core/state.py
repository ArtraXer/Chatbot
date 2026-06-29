import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

_config_path = None
_history_path = None
_tasks_path = None


def _base_dir() -> Path:
    home_dir = os.environ.get("HOME") or str(Path.home())
    return Path(home_dir) / ".chatbot_ai"


def _ensure_dir() -> Path:
    base = _base_dir()
    base.mkdir(parents=True, exist_ok=True)
    return base


def _get_config_path() -> Path:
    global _config_path
    if _config_path is None:
        _config_path = _ensure_dir() / "settings.json"
    return _config_path


def _get_history_path() -> Path:
    global _history_path
    if _history_path is None:
        _history_path = _ensure_dir() / "history.json"
    return _history_path


def _get_tasks_path() -> Path:
    global _tasks_path
    if _tasks_path is None:
        _tasks_path = _ensure_dir() / "tasks.json"
    return _tasks_path


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return default


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def load_settings() -> Dict[str, Any]:
    default = {
        "model": "meta/llama-3.1-8b-instruct",
        "safe_mode": True,
        "workdir": "",
        "theme": "dark",
    }
    data = _read_json(_get_config_path(), default)
    if not isinstance(data, dict):
        data = {}
    return {**default, **data}


def save_settings(settings: Dict[str, Any]) -> None:
    _write_json(_get_config_path(), settings)


def load_conversations() -> List[Dict[str, Any]]:
    data = _read_json(_get_history_path(), [])
    if not isinstance(data, list):
        return []
    return data


def append_conversation(message: Dict[str, Any]) -> None:
    if not isinstance(message, dict):
        return
    history = load_conversations()
    entry = dict(message)
    entry.setdefault("timestamp", datetime.now().isoformat())
    history.append(entry)
    if len(history) > 100:
        history = history[-100:]
    _write_json(_get_history_path(), history)


def load_tasks() -> List[Dict[str, Any]]:
    data = _read_json(_get_tasks_path(), [])
    if not isinstance(data, list):
        return []
    return data


def append_task(tipo: str, detalle: str, estado: str = "completado") -> None:
    tasks = load_tasks()
    tasks.append(
        {
            "tipo": tipo,
            "detalle": detalle,
            "estado": estado,
            "timestamp": datetime.now().isoformat(),
        }
    )
    if len(tasks) > 40:
        tasks = tasks[-40:]
    _write_json(_get_tasks_path(), tasks)


def clear_tasks() -> None:
    _write_json(_get_tasks_path(), [])


def clear_history() -> None:
    _write_json(_get_history_path(), [])
