from typing import Optional
from core.config.config_manager import get_value
from .api_client import APIClient

class Auth:
    def __init__(self, client: Optional[APIClient] = None):
        self.client = client or APIClient()
        self.check_path = get_value("FNOS_AUTH_CHECK_PATH", "/api/v1/admin/me")

    def is_super_admin(self) -> bool:
        """
        Validate if fnOS_Overseer itself has super admin permissions.

        This uses the internal FNOS_SUPER_TOKEN from environment to check
        if fnOS_Overseer is authorized to call fnOS APIs.
        """
        data = self.client.get(self.check_path)
        if not data:
            return False
        role = data.get("role") or data.get("is_admin")
        if isinstance(role, bool):
            return role
        return str(role).lower() in ("admin", "superadmin", "super_admin")

    def is_super_admin_with_session(self, session_token: Optional[str]) -> bool:
        """
        Validate if a user (with given session token) is a super admin.

        This validates the CLIENT's session token against fnOS's official API,
        not the internal FNOS_SUPER_TOKEN used by fnOS_Overseer itself.

        Args:
            session_token: The client's session identifier from Cookie or Authorization header

        Returns:
            True if the user is a super admin, False otherwise
        """
        if not session_token:
            return False

        # Create a temporary client using the client's session token
        # instead of the internal FNOS_SUPER_TOKEN
        temp_client = APIClient(
            base_url=get_value("FNOS_BASE_URL", "http://localhost:8000"),
            token=session_token  # Use client's token
        )

        data = temp_client.get(self.check_path)
        if not data:
            return False

        role = data.get("role") or data.get("is_admin")
        if isinstance(role, bool):
            return role

        return str(role).lower() in ("admin", "superadmin", "super_admin")
