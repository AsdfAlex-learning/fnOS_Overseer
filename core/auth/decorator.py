"""
Authentication decorators for Flask routes.

This module provides decorators for protecting API endpoints with various
authentication mechanisms:
- require_super_admin: Requires fnOS super admin session
- require_api_token: Requires API token (for webhooks, etc.)
"""
import os
from functools import wraps
import logging
from typing import Optional
import importlib

flask = importlib.import_module("flask")
request = flask.request
jsonify = flask.jsonify

from .auth_config import auth_config
from adapter.fnos.auth import Auth
from web.backend.models.data_models import err

logger = logging.getLogger(__name__)


def require_super_admin(f):
    """
    Decorator: Requires fnOS super admin authentication.

    This decorator validates that requester is a fnOS super admin by:
    1. Checking if authentication is enabled (via AuthConfig runtime lock)
    2. Extracting client's session token from Cookie or Authorization header
    3. Calling fnOS official API to validate user's role

    Usage:
        @bp.get("/api/sensitive")
        @require_super_admin
        def sensitive_endpoint():
            return jsonify({"data": "protected"})
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        # Layer 1: Check if auth is enabled (runtime locked)
        if not auth_config.requires_auth:
            logger.debug(f"Auth disabled, allowing request to {request.path}")
            return f(*args, **kwargs)

        # Layer 2: Extract client's session token
        # fnOS typically uses session cookie, but also support Authorization header
        session_token = _extract_session_token()

        if not session_token:
            logger.warning(f"Auth failed: No session token provided for {request.path}")
            return jsonify(err(403, "No authentication provided")), 403

        # Layer 3: Validate with fnOS official API
        # Use client's session token, not internal FNOS_SUPER_TOKEN
        auth = Auth()
        is_admin = auth.is_super_admin_with_session(session_token)

        if not is_admin:
            logger.warning(
                f"Auth failed: User is not super admin for {request.path} "
                f"(from {request.remote_addr})"
            )
            return jsonify(err(403, "Forbidden: Super admin required")), 403

        # Auth successful
        logger.debug(f"Auth passed for {request.path}")
        return f(*args, **kwargs)

    return wrapper


def require_api_token(f):
    """
    Decorator: Requires API token authentication.

    This decorator validates requests using a static API token, useful for:
    - Webhook endpoints
    - Service-to-service communication
    - Internal monitoring tools

    The token is validated against WEBHOOK_TOKEN environment variable.

    Usage:
        @bp.post("/webhook/external")
        @require_api_token
        def webhook_endpoint():
            return jsonify({"status": "received"})
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        # Get expected token from environment
        expected_token = os.getenv("WEBHOOK_TOKEN", "")

        # If no token is configured, skip validation (dev mode)
        if not expected_token:
            logger.warning(f"WEBHOOK_TOKEN not configured, skipping validation for {request.path}")
            return f(*args, **kwargs)

        # Extract token from multiple sources
        provided_token = _extract_api_token()

        if not provided_token:
            logger.warning(f"Auth failed: No API token provided for {request.path}")
            return jsonify(err(401, "Unauthorized: API token required")), 401

        # Validate token
        if provided_token != expected_token:
            logger.warning(f"Auth failed: Invalid API token for {request.path} from {request.remote_addr}")
            return jsonify(err(401, "Unauthorized: Invalid API token")), 401

        # Token valid
        logger.debug(f"API token auth passed for {request.path}")
        return f(*args, **kwargs)

    return wrapper


def _extract_session_token() -> Optional[str]:
    """
    Extract session token from request.

    Checks multiple sources in order of preference:
    1. Cookie named 'session' (fnOS standard)
    2. Cookie named 'session_id' (alternative)
    3. Authorization header with 'Bearer <token>' format

    Returns:
        The session token string, or None if not found.
    """
    # Check cookies first (most common for fnOS)
    session_cookie = request.cookies.get("session") or request.cookies.get("session_id")
    if session_cookie:
        return session_cookie

    # Fallback to Authorization header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]

    return None


def _extract_api_token() -> Optional[str]:
    """
    Extract API token from request.

    Checks multiple sources:
    1. X-Webhook-Token header
    2. Authorization header (Bearer token)
    3. token query parameter

    Returns:
        The API token string, or None if not found.
    """
    # Check X-Webhook-Token header
    token = request.headers.get("X-Webhook-Token")
    if token:
        return token

    # Check Authorization header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]

    # Check query parameter (least secure, but useful for testing)
    token = request.args.get("token")
    if token:
        return token

    return None
