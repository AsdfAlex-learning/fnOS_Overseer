import importlib
from web.backend.api.v1 import bp, require_super_admin
from core.config import ConfigManager
from web.backend.models.data_models import ok, err
from pathlib import Path

flask = importlib.import_module("flask")
request = flask.request
jsonify = flask.jsonify

# Hardware TDP environment variables
TDP_ENV_PREFIXES = [
    'HARDWARE_TDP_CPU',
    'HARDWARE_TDP_HDD_IDLE',
    'HARDWARE_TDP_HDD_ACTIVE',
    'HARDWARE_TDP_SSD',
    'HARDWARE_TDP_NVME',
    'HARDWARE_TDP_MEMORY'
]

# Home Assistant environment variables
HA_ENV_PREFIXES = [
    'HA_ENABLED',
    'HA_POWER_SOURCE',
    'HA_ENTITY_POWER',
    'HA_ENTITY_CPU',
    'MQTT_BROKER',
    'MQTT_PORT',
    'MQTT_TOPIC',
    'MQTT_USERNAME',
    'MQTT_PASSWORD',
    'HA_API_URL',
    'HA_API_TOKEN',
    'EXTERNAL_POWER_API',
    'EXTERNAL_POWER_POLL_INTERVAL'
]


@bp.get("/config")
@require_super_admin
def get_cfg():
    return jsonify(ok(ConfigManager().get_config(mask=True)))


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
    # SMTP, EMAIL, FNOS, Home Assistant, Hardware TDP
    env_prefixes = (
        "SMTP_", "EMAIL_", "FNOS_", "HA_", "MQTT_",
        "HARDWARE_TDP_", "EXTERNAL_", "API_"
    )

    yaml_updates = {}
    env_updates = {}

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

            # Handle hardware_tdp section specially
            if 'hardware_tdp' in yaml_updates or any(k.startswith('HARDWARE_TDP_') for k in yaml_updates):
                if 'hardware_tdp' not in current_yaml:
                    current_yaml['hardware_tdp'] = {}

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
                    # Top-level keys
                    current_yaml[k] = v

            yaml_path.write_text(
                _yaml.safe_dump(current_yaml, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )

        # Reload config manager
        from core.config import ConfigManager
        _GLOBAL = ConfigManager()

        return jsonify(ok(_GLOBAL.get_config(mask=True)))

    except Exception as e:
        import logging
        logging.error(f"Update config failed: {e}", exc_info=True)
        return jsonify(err(500, "update_failed")), 500
