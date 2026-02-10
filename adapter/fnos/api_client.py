import importlib
from typing import Any, Dict, Optional
from urllib.parse import urljoin
from core.config.config_manager import get_value

class APIClient:
    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None):
        self.base_url = base_url or get_value("FNOS_BASE_URL", "http://localhost:8000")
        self.token = token or get_value("FNOS_SUPER_TOKEN", "")
        self._requests = importlib.import_module("requests")
        self.session = self._requests.Session()
        if self.token:
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        try:
            url = urljoin(self.base_url, path)
            r = self.session.get(url, params=params, timeout=5)
            if r.status_code >= 200 and r.status_code < 300:
                return r.json()
            return None
        except Exception:
            return None

    def post(self, path: str, json: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        try:
            url = urljoin(self.base_url, path)
            r = self.session.post(url, json=json, timeout=5)
            if r.status_code >= 200 and r.status_code < 300:
                return r.json()
            return None
        except Exception:
            return None
