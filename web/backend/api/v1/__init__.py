import os
from functools import wraps
import importlib
from web.backend.models.data_models import ok, err
from adapter.fnos.auth import Auth

flask = importlib.import_module("flask")
Blueprint = flask.Blueprint
jsonify = flask.jsonify

bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")


def require_super_admin(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = os.getenv("FNOS_SUPER_TOKEN", "")
        if token:
            if not Auth().is_super_admin():
                return jsonify(err(403, "forbidden")), 403
        return f(*args, **kwargs)

    return wrapper


# Register API routes - Import after bp definition to avoid circular import
from . import config, monitor, report, webhook
