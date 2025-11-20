import json
from copy import deepcopy
from pathlib import Path
from threading import Lock
from typing import Any, Dict

DEFAULT_SETTINGS: Dict[str, Any] = {
    "sourceType": None,
    "rtspUrl": "",
    "videoPath": "",
    "videoFileName": "",
    "detectionTarget": "vehicles",
    "detectionModel": "yolo11l.pt",
    "widgets": {
        "videoWidget": True,
        "accessButton": True,
    },
}

SETTINGS_DIR = Path("config")
SETTINGS_FILE = SETTINGS_DIR / "detection_settings.json"

_settings_lock = Lock()


def _ensure_settings_file() -> None:
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    if not SETTINGS_FILE.exists():
        SETTINGS_FILE.write_text(
            json.dumps(DEFAULT_SETTINGS, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _merge_settings(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    result = deepcopy(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge_settings(result.get(key, {}), value)
        else:
            result[key] = value
    return result


def load_detection_settings() -> Dict[str, Any]:
    _ensure_settings_file()
    raw = SETTINGS_FILE.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {}
    merged = _merge_settings(DEFAULT_SETTINGS, data)
    return merged


def save_detection_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    with _settings_lock:
        SETTINGS_FILE.write_text(
            json.dumps(settings, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return settings


def update_detection_settings(partial: Dict[str, Any]) -> Dict[str, Any]:
    with _settings_lock:
        current = load_detection_settings()
        updated = _merge_settings(current, partial)
        save_detection_settings(updated)
        return updated


def reset_detection_settings() -> Dict[str, Any]:
    with _settings_lock:
        save_detection_settings(DEFAULT_SETTINGS)
        return deepcopy(DEFAULT_SETTINGS)


def get_public_detection_settings(settings: Dict[str, Any] | None = None) -> Dict[str, Any]:
    data = settings or load_detection_settings()
    public = deepcopy(data)
    public["rtspUrl"] = "***" if public.get("rtspUrl") else ""
    return public


