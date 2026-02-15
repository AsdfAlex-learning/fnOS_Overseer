"""
Authentication Configuration with Runtime Locking

This module provides a security configuration that is initialized once at startup
and cannot be modified at runtime. This prevents configuration tampering attacks.
"""
import os
import logging

logger = logging.getLogger(__name__)


class AuthConfig:
    """
    Runtime-locked security configuration.

    The configuration is read from environment variables at initialization
    and stored in private attributes that cannot be modified at runtime.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Prevent re-initialization
        if hasattr(self, '_initialized'):
            return

        # Read configuration from environment at startup only
        self._require_auth = self._parse_bool_env("FNOS_REQUIRE_AUTH", "true")
        self._is_production = os.getenv("APP_ENV", "production").lower() not in ("dev", "development")
        self._fnos_base_url = os.getenv("FNOS_BASE_URL", "")
        self._auth_check_path = os.getenv("FNOS_AUTH_CHECK_PATH", "/api/v1/admin/me")

        # Log configuration for audit
        if not self._require_auth:
            logger.warning("SECURITY: Authentication is DISABLED via FNOS_REQUIRE_AUTH")
        elif not self._is_production:
            logger.warning("SECURITY: Running in DEVELOPMENT mode, auth checks may be logged")
        else:
            logger.info("SECURITY: Running in PRODUCTION mode with authentication enabled")

        self._initialized = True

    @staticmethod
    def _parse_bool_env(key: str, default: str) -> bool:
        """Parse boolean environment variable."""
        value = os.getenv(key, default).lower()
        return value in ("1", "true", "yes", "on", "enabled")

    # Read-only properties (runtime locked)
    @property
    def requires_auth(self) -> bool:
        """Whether authentication is required."""
        return self._require_auth

    @property
    def is_production(self) -> bool:
        """Whether running in production mode."""
        return self._is_production

    @property
    def fnos_base_url(self) -> str:
        """fnOS base URL for API calls."""
        return self._fnos_base_url

    @property
    def auth_check_path(self) -> str:
        """Path to the auth check endpoint."""
        return self._auth_check_path

    @property
    def security_summary(self) -> dict:
        """Return security configuration summary (for debugging)."""
        return {
            "requires_auth": self._requires_auth,
            "is_production": self._is_production,
            "fnos_base_url": self._fnos_base_url,
            "auth_check_path": self._auth_check_path,
        }


# Global singleton instance, initialized at module import
auth_config = AuthConfig()
