import importlib
from web.backend.models.data_models import ok, err
from core.auth import require_super_admin, require_api_token

from flask import Blueprint, jsonify

bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")

# Register API routes - Import after bp definition to avoid circular import
from . import config, monitor, report, webhook, ha
