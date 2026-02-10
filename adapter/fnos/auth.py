from typing import Optional
from core.config.config_manager import get_value
from .api_client import APIClient

class Auth:
    def __init__(self, client: Optional[APIClient] = None):
        self.client = client or APIClient()
        self.check_path = get_value("FNOS_AUTH_CHECK_PATH", "/api/v1/admin/me")

    def is_super_admin(self) -> bool:
        data = self.client.get(self.check_path)
        if not data:
            return False
        role = data.get("role") or data.get("is_admin")
        if isinstance(role, bool):
            return role
        return str(role).lower() in ("admin", "superadmin", "super_admin")
