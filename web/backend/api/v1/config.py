import importlib
flask = importlib.import_module("flask")
request = flask.request
jsonify = flask.jsonify
from web.backend.api.v1 import bp, require_super_admin
from core.config.config_manager import get_config, ConfigManager
from web.backend.models.data_models import ok, err
from pathlib import Path

@bp.get("/config")
@require_super_admin
def get_cfg():
    return jsonify(ok(get_config(mask=True)))

@bp.post("/config")
@require_super_admin
def update_cfg():
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify(err(400, "bad_request")), 400
    cm = ConfigManager()
    yaml_path = cm.yaml_path
    try:
        import yaml as _yaml
        current = cm.yaml_cfg if isinstance(cm.yaml_cfg, dict) else {}
        for k, v in data.items():
            if isinstance(k, str):
                current[k] = v
        yaml_path.write_text(_yaml.safe_dump(current, allow_unicode=True, sort_keys=False), encoding="utf-8")
        cm = ConfigManager()
        return jsonify(ok(get_config(mask=True)))
    except Exception:
        return jsonify(err(500, "update_failed")), 500
