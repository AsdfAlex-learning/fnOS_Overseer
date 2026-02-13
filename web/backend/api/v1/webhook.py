import importlib
import logging

flask = importlib.import_module("flask")
request = flask.request
jsonify = flask.jsonify
from web.backend.api.v1 import bp
from web.backend.models.data_models import ok, err
from core.behavior import process_user_behavior

logger = logging.getLogger(__name__)

@bp.post("/webhook/fnos/user_behavior")
def fnos_webhook():
    """
    Endpoint to receive raw user behavior data from fnOS Webhook.
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
        logger.error(f"Error processing webhook: {e}")
        return jsonify(err(500, f"Internal Server Error: {str(e)}")), 500
