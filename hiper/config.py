import json
import os
from typing import Dict

_DEFAULT_DATA_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", "hiper")
_CONFIG_FILE = os.path.join(_DEFAULT_DATA_DIR, "config.json")
_CONFIG_CACHE: Dict[str, str] | None = None


def _load_config() -> Dict[str, str]:
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE

    cache: Dict[str, str] = {}
    if os.path.exists(_CONFIG_FILE):
        try:
            with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except Exception as e:
            print(f"Error: cannot load config file {_CONFIG_FILE}: {e}")

    _CONFIG_CACHE = cache  # type: ignore
    return cache


def _save_config(cfg: Dict[str, str]) -> None:
    global _CONFIG_CACHE
    os.makedirs(_DEFAULT_DATA_DIR, exist_ok=True)

    with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    _CONFIG_CACHE = cfg  # type: ignore


def get_config(key: str, default: str = "") -> str:
    cfg = _load_config()
    return cfg.get(key, default)


def set_config(key: str, value: str):
    cfg = _load_config()
    cfg[key] = value
    _save_config(cfg)


def get_data_dir() -> str:
    savedir = get_config("savedir")
    if savedir and os.path.isabs(savedir):
        return savedir
    return _DEFAULT_DATA_DIR
