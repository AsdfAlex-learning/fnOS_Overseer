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
    env_path = cm.env_path

    # Define prefixes for keys that should go to .env
    env_prefixes = ("SMTP_", "EMAIL_", "FNOS_")

    env_updates = {}
    yaml_updates = {}

    for k, v in data.items():
        if not isinstance(k, str):
            continue

        # Check if key belongs to .env
        if k.upper().startswith(env_prefixes):
            env_updates[k] = v
        else:
            # Assume it belongs to yaml
            yaml_updates[k] = v

    try:
        # Update .env using dotenv
        if env_updates:
            dotenv = importlib.import_module("dotenv")
            # Create .env if not exists
            if not env_path.exists():
                env_path.touch()

            for k, v in env_updates.items():
                dotenv.set_key(env_path, k, str(v))

        # Update config.yaml
        if yaml_updates:
            import yaml as _yaml

            current_yaml = cm.yaml_cfg if isinstance(cm.yaml_cfg, dict) else {}

            for k, v in yaml_updates.items():
                # Handle dot notation for nested keys (e.g. performance.collect_interval)
                if "." in k:
                    parts = k.split(".")
                    target = current_yaml
                    for p in parts[:-1]:
                        if p not in target or not isinstance(target[p], dict):
                            target[p] = {}
                        target = target[p]
                    target[parts[-1]] = v
                else:
                    current_yaml[k] = v

            yaml_path.write_text(
                _yaml.safe_dump(current_yaml, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )

        # Reload config manager
        # Since we modified files, we need to re-instantiate or clear global cache if any
        # The get_config() function creates a new ConfigManager instance if _GLOBAL is None,
        # but here we want to force reload.
        # Actually ConfigManager() constructor reloads everything.
        # But we need to update the _GLOBAL instance used by get_config
        from core.config import config_manager

        config_manager._GLOBAL = ConfigManager()

        return jsonify(ok(config_manager.get_config(mask=True)))
    except Exception as e:
        # It's better to log error here
        print(f"Update config failed: {e}")
        return jsonify(err(500, "update_failed")), 500
