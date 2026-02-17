import logging

from flask import request, jsonify
from web.backend.api.v1 import bp
from web.backend.models.data_models import ok, err
from core.behavior import process_user_behavior
from core.auth import require_api_token

logger = logging.getLogger(__name__)


@bp.post("/webhook/fnos/user_behavior")
@require_api_token
def fnos_webhook():
    """
    Endpoint to receive raw user behavior data from fnOS Webhook.

    Requires WEBHOOK_TOKEN for authentication (via @require_api_token decorator).
    The token can be passed via:
    1. X-Webhook-Token header
    2. Authorization header (Bearer token)
    3. token query parameter
    """
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
