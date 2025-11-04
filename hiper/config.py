import json
import os
from typing import Optional, Dict, Any


_DEFAULT_DATA_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", "hiper")
# Config file always stays in default location
_CONFIG_FILE = os.path.join(_DEFAULT_DATA_DIR, "config.json")
_CONFIG_CACHE: Optional[Dict[str, Any]] = None


def _load_config() -> Dict[str, Any]:
    """Load config file (always from default location), with caching"""
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE
    
    _CONFIG_CACHE = {}
    if os.path.exists(_CONFIG_FILE):
        try:
            with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
                _CONFIG_CACHE = json.load(f)
        except Exception:
            pass
    return _CONFIG_CACHE


def _save_config(cfg: Dict[str, Any]) -> None:
    """Save config file (always in default location)"""
    global _CONFIG_CACHE
    # Config file always in default location
    os.makedirs(_DEFAULT_DATA_DIR, exist_ok=True)
    
    try:
        with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        _CONFIG_CACHE = cfg
    except Exception:
        pass


def get_config(key: str, default: Any = None) -> Any:
    """Get a config value"""
    cfg = _load_config()
    return cfg.get(key, default)


def set_config(key: str, value: Any) -> None:
    """Set a config value and save"""
    cfg = _load_config()
    cfg[key] = value
    _save_config(cfg)


def get_data_dir() -> str:
    """Get the data directory (from config or default)"""
    # Config file is always in default location, but savedir setting
    # controls where data files (sessions CSV, etc.) are saved
    savedir = get_config("savedir")
    if savedir and os.path.isabs(savedir):
        return savedir
    return _DEFAULT_DATA_DIR


def invalidate_cache() -> None:
    """Invalidate config cache (e.g., after external changes)"""
    global _CONFIG_CACHE
    _CONFIG_CACHE = None

