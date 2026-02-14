import importlib
import logging
import os
import hashlib

flask = importlib.import_module("flask")
request = flask.request
jsonify = flask.jsonify
from web.backend.api.v1 import bp
from web.backend.models.data_models import ok, err
from core.behavior import process_user_behavior

logger = logging.getLogger(__name__)


def _verify_webhook_token():
    """
    Verify webhook request using API Token.
    Token can be passed via:
    1. X-Webhook-Token header
    2. Authorization header (Bearer token)
    3. token query parameter
    """
    expected_token = os.getenv("WEBHOOK_TOKEN", "")

    # If no token is configured, skip verification (for development)
    if not expected_token:
        logger.warning("WEBHOOK_TOKEN not configured, skipping verification")
        return True

    # Try to get token from various sources
    provided_token = (
        request.headers.get("X-Webhook-Token") or
        (request.headers.get("Authorization", "").replace("Bearer ", "")) or
        request.args.get("token", "")
    )

    if not provided_token:
        logger.warning("Webhook request missing token")
        return False

    # Compare tokens (use timing-safe comparison in production)
    if provided_token == expected_token:
        return True

    logger.warning("Webhook token mismatch")
    return False


@bp.post("/webhook/fnos/user_behavior")
def fnos_webhook():
    """
    Endpoint to receive raw user behavior data from fnOS Webhook.
    Requires WEBHOOK_TOKEN for authentication (unless not configured).
    """
    # Verify webhook token
    if not _verify_webhook_token():
        return jsonify(err(401, "Unauthorized")), 401

    try:
        # Attempt to parse JSON payload
        data = request.get_json(force=True, silent=True)

        if not data:
            # Fallback for form data or other content types if needed,
            # but webhooks are usually JSON.
            # If data is None, it means parsing failed or body is empty.
            logger.warning("Received webhook with no JSON data")
            return jsonify(err(400, "Invalid JSON payload or empty body")), 400

        logger.info(f"Received webhook payload: {data}")

        # Process the data through the core behavior analyzer
        # This function logs the raw data and provides a hook for user customization
        process_user_behavior(data)

        return jsonify(ok({"message": "Webhook received and processed"})), 200

    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        return jsonify(err(500, f"Internal Server Error: {str(e)}")), 500
