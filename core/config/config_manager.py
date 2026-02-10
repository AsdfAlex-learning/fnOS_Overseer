import os
from pathlib import Path
from typing import Any, Dict, Optional, Union
import importlib

SENSITIVE_KEYS = ("PASS", "PASSWORD", "TOKEN", "SECRET", "KEY", "PWD")
DEFAULT_ENV_KEYS = (
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USER",
    "SMTP_PASS",
    "SMTP_TLS",
    "EMAIL_FROM",
    "EMAIL_TO",
)


def _mask_value(v: Any) -> Any:
    if v is None:
        return None
    s = str(v)
    if len(s) <= 4:
        return "****"
    return s[:2] + "****" + s[-2:]


def _mask_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, dict):
            out[k] = _mask_dict(v)
        else:
            if any(x in k.upper() for x in SENSITIVE_KEYS):
                out[k] = _mask_value(v)
            else:
                out[k] = v
    return out


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        yaml = importlib.import_module("yaml")
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if isinstance(data, dict):
            return data
        return {}
    except Exception:
        return {}


def _load_dotenv(env_path: Path) -> None:
    try:
        dotenv = importlib.import_module("dotenv")
        dotenv.load_dotenv(dotenv_path=str(env_path))
    except Exception:
        pass


def _collect_env(extra_keys: Optional[list] = None) -> Dict[str, Any]:
    keys: set[str] = set(DEFAULT_ENV_KEYS)
    for k in os.environ.keys():
        if k.startswith("FNOS_"):
            keys.add(k)
    if extra_keys:
        for k in extra_keys:
            keys.add(k)
    out: Dict[str, Any] = {}
    for k in keys:
        v = os.getenv(k)
        if v is not None:
            out[k] = v
    return out


class ConfigManager:
    def __init__(
        self,
        yaml_path: Optional[Union[str, Path]] = None,
        env_path: Optional[Union[str, Path]] = None,
    ):
        base_dir = Path(__file__).resolve().parent
        project_root = base_dir.parent.parent
        if yaml_path is None:
            yaml_path = project_root / "config.yaml"
        if env_path is None:
            env_path = project_root / ".env"
        self.yaml_path = (
            Path(yaml_path) if not isinstance(yaml_path, Path) else yaml_path
        )
        self.env_path = Path(env_path) if not isinstance(env_path, Path) else env_path
        _load_dotenv(self.env_path)
        self.yaml_cfg = _load_yaml(self.yaml_path)
        self.env_cfg = _collect_env()

    def to_dict(self, mask: bool = True) -> Dict[str, Any]:
        merged = {
            "yaml": self.yaml_cfg,
            "env": self.env_cfg,
        }
        return _mask_dict(merged) if mask else merged

    def get(self, key: str, default: Any = None) -> Any:
        if key in self.env_cfg:
            return self.env_cfg.get(key, default)
        return self.yaml_cfg.get(key, default)


_GLOBAL: Optional[ConfigManager] = None


def get_config(mask: bool = True) -> Dict[str, Any]:
    global _GLOBAL
    if _GLOBAL is None:
        _GLOBAL = ConfigManager()
    return _GLOBAL.to_dict(mask=mask)


def get_value(key: str, default: Any = None) -> Any:
    global _GLOBAL
    if _GLOBAL is None:
        _GLOBAL = ConfigManager()
    return _GLOBAL.get(key, default)
