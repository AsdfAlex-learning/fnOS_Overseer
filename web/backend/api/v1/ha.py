"""
Home Assistant compatible API endpoints.

This module provides REST API endpoints compatible with Home Assistant's
RESTful Sensor platform. It exposes system metrics in a format that
Home Assistant can consume.
"""

import importlib
import logging
import os
from typing import Dict, Any, Optional
import json as json_lib

from flask import request, jsonify
from web.backend.api.v1 import bp
from core.auth import require_api_token
from web.backend.models.data_models import ok
from core.monitor import CPUMonitor, StorageMonitor, PowerCalculator

logger = logging.getLogger(__name__)

# Global instances (cached for performance)
_monitor_cache = {
    "last_update": 0,
    "cpu_monitor": None,
    "storage_monitor": None,
    "power_calculator": None,
}


def _get_monitor_components():
    """Initialize or get cached monitor components."""
    if _monitor_cache["last_update"] == 0 or _monitor_cache["cpu_monitor"] is None:

        _monitor_cache["cpu_monitor"] = CPUMonitor()
        _monitor_cache["storage_monitor"] = StorageMonitor()
        _monitor_cache["power_calculator"] = PowerCalculator(
            _monitor_cache["cpu_monitor"], _monitor_cache["storage_monitor"]
        )
        _monitor_cache["last_update"] = 1

    return (
        _monitor_cache["cpu_monitor"],
        _monitor_cache["storage_monitor"],
        _monitor_cache["power_calculator"],
    )


def _get_external_power() -> Optional[float]:
    """
    Get power from external monitoring source.

    Priority:
    1. Home Assistant sensors (via API call to HA)
    2. MQTT (if MQTT broker is configured)
    3. External API (if configured)

    Returns:
        Power value in watts, or None if external source not configured.
    """
    # Check if HA sensors are configured
    ha_entity_power = os.getenv("HA_ENTITY_POWER", "")
    ha_api_url = os.getenv("HA_API_URL", "http://supervisor/core/api")

    if ha_entity_power and ha_api_url:
        try:
            # Call Home Assistant API to get sensor state
            import requests

            headers = {
                "Authorization": f"Bearer {os.getenv('HA_API_TOKEN', '')}",
                "Content-Type": "application/json",
            }

            url = f"{ha_api_url}/states/{ha_entity_power}"
            response = requests.get(url, headers=headers, timeout=5)

            if response.status_code == 200:
                data = response.json()
                state = data.get("state", {})
                if isinstance(state, (float, int)):
                    return float(state)
                elif isinstance(state, dict):
                    attributes = state.get("attributes", {})
                    unit_of_measurement = attributes.get("unit_of_measurement", "")
                    if unit_of_measurement == "W" and isinstance(
                        attributes.get("state"), (float, int)
                    ):
                        return float(attributes.get("state", 0))

            logger.warning(f"HA sensor fetch failed: {response.status_code}")

        except Exception as e:
            logger.debug(f"External power fetch error: {e}")

    return None


@bp.get("/ha/power")
def ha_power():
    """
    Get total power consumption.

    Priority:
    1. External monitoring (HA sensors/MQTT/external API)
    2. Internal estimation (CPU + disk + memory)

    Compatible with Home Assistant REST Sensor:
    ```
    sensor:
      - name: fnOS Overseer Total Power
        unit_of_measurement: W
        state_class: measurement
        device_class: power
    ```
    """
    try:
        # Try to get external power first
        external_power = _get_external_power()

        if external_power is not None:
            # Use external monitoring data
            logger.debug(f"Using external power: {external_power}W")
            return jsonify(
                ok(
                    {
                        "state": external_power,
                        "attributes": {
                            "unit_of_measurement": "W",
                            "friendly_name": "fnOS Overseer Total Power",
                            "source": "external_monitoring",
                        },
                        "last_updated": importlib.import_module("datetime")
                        .datetime.now()
                        .isoformat(),
                    }
                )
            )

        # Fall back to internal estimation
        cpu_monitor, storage_monitor, power_calc = _get_monitor_components()

        # Get power calculation
        power_result = power_calc.estimate_total_power()
        total_watts = power_result["total_watts"]
        breakdown = power_result["breakdown"]
        disk_counts = power_result.get("disk_counts", {})

        return jsonify(
            ok(
                {
                    "state": total_watts,
                    "attributes": {
                        "unit_of_measurement": "W",
                        "friendly_name": "fnOS Overseer Total Power",
                        "source": "internal_estimation",
                        "cpu_watts": breakdown["cpu"],
                        "base_watts": breakdown["base"],
                        "disk_watts": breakdown["disk"],
                        "memory_watts": breakdown["memory"],
                        "disk_counts": disk_counts,
                    },
                    "last_updated": importlib.import_module("datetime")
                    .datetime.now()
                    .isoformat(),
                }
            )
        )

    except Exception as e:
        logger.error(f"Error in /ha/power: {e}", exc_info=True)
        return jsonify(
            ok(
                {
                    "state": 0,
                    "attributes": {"unit_of_measurement": "W", "error": str(e)},
                    "last_updated": importlib.import_module("datetime")
                    .datetime.now()
                    .isoformat(),
                }
            )
        )


@bp.get("/ha/cpu")
def ha_cpu():
    """
    Get CPU information and power.

    Compatible with Home Assistant REST Sensor.
    """
    try:
        cpu_monitor, _, _ = _get_monitor_components()

        cpu_info = cpu_monitor.get_cpu_info()
        cpu_usage = cpu_monitor.get_cpu_usage(interval=0.2)
        cpu_power = cpu_monitor.estimate_cpu_power(cpu_usage)

        return jsonify(
            ok(
                {
                    "state": cpu_usage,
                    "attributes": {
                        "unit_of_measurement": "%",
                        "friendly_name": "fnOS Overseer CPU Usage",
                        "model": cpu_info.get("model", "Unknown"),
                        "physical_cores": cpu_info.get("physical_cores", 0),
                        "logical_cores": cpu_info.get("logical_cores", 0),
                        "frequency_mhz": cpu_info.get("frequency_current", 0),
                        "power_watts": cpu_power,
                    },
                    "last_updated": importlib.import_module("datetime")
                    .datetime.now()
                    .isoformat(),
                }
            )
        )

    except Exception as e:
        logger.error(f"Error in /ha/cpu: {e}", exc_info=True)
        return jsonify(
            ok(
                {
                    "state": 0,
                    "attributes": {"unit_of_measurement": "%", "error": str(e)},
                    "last_updated": importlib.import_module("datetime")
                    .datetime.now()
                    .isoformat(),
                }
            )
        )


@bp.get("/ha/storage")
def ha_storage():
    """
    Get storage information.

    Compatible with Home Assistant REST Sensor.
    """
    try:
        _, storage_monitor, _ = _get_monitor_components()

        storage = storage_monitor.get_storage_overview()

        # Calculate total usage
        total_gb = sum(s["usage"]["total_gb"] for s in storage)
        used_gb = sum(s["usage"]["used_gb"] for s in storage)

        return jsonify(
            ok(
                {
                    "state": round(used_gb / total_gb * 100, 2) if total_gb > 0 else 0,
                    "attributes": {
                        "unit_of_measurement": "%",
                        "friendly_name": "fnOS Overseer Storage Usage",
                        "total_gb": total_gb,
                        "used_gb": used_gb,
                        "free_gb": total_gb - used_gb,
                        "devices": storage,
                    },
                    "last_updated": importlib.import_module("datetime")
                    .datetime.now()
                    .isoformat(),
                }
            )
        )

    except Exception as e:
        logger.error(f"Error in /ha/storage: {e}", exc_info=True)
        return jsonify(
            ok(
                {
                    "state": 0,
                    "attributes": {"unit_of_measurement": "%", "error": str(e)},
                    "last_updated": importlib.import_module("datetime")
                    .datetime.now()
                    .isoformat(),
                }
            )
        )


@bp.get("/ha/sensors")
def ha_sensors():
    """
    Get all sensors in a single call (batch endpoint).

    This is useful for Home Assistant to fetch multiple sensors at once.

    Returns:
        {
          "power": {...},
          "cpu": {...},
          "storage": {...}
        }
    """
    try:
        # Get individual sensors
        # (This would normally call the individual endpoints, but for efficiency
        # we can inline the logic here)

        cpu_monitor, storage_monitor, power_calc = _get_monitor_components()

        # CPU
        cpu_info = cpu_monitor.get_cpu_info()
        cpu_usage = cpu_monitor.get_cpu_usage(interval=0.2)
        cpu_power = cpu_monitor.estimate_cpu_power(cpu_usage)

        # Storage
        storage = storage_monitor.get_storage_overview()
        total_gb = sum(s["usage"]["total_gb"] for s in storage)
        used_gb = sum(s["usage"]["used_gb"] for s in storage)

        # Power
        power_result = power_calc.estimate_total_power()
        external_power = _get_external_power()
        if external_power is not None:
            total_watts = external_power
            power_source = "external_monitoring"
        else:
            total_watts = power_result["total_watts"]
            power_source = "internal_estimation"

        return jsonify(
            ok(
                {
                    "power": {
                        "state": total_watts,
                        "attributes": power_result["breakdown"],
                    },
                    "cpu": {
                        "state": cpu_usage,
                        "attributes": {
                            "model": cpu_info.get("model", "Unknown"),
                            "physical_cores": cpu_info.get("physical_cores", 0),
                            "logical_cores": cpu_info.get("logical_cores", 0),
                            "frequency_mhz": cpu_info.get("frequency_current", 0),
                            "power_watts": cpu_power,
                        },
                    },
                    "storage": {
                        "state": (
                            round(used_gb / total_gb * 100, 2) if total_gb > 0 else 0
                        ),
                        "attributes": {
                            "total_gb": total_gb,
                            "used_gb": used_gb,
                            "free_gb": total_gb - used_gb,
                            "devices": storage,
                        },
                    },
                }
            )
        )

    except Exception as e:
        logger.error(f"Error in /ha/sensors: {e}", exc_info=True)
        return jsonify(
            ok(
                {
                    "error": str(e),
                    "last_updated": importlib.import_module("datetime")
                    .datetime.now()
                    .isoformat(),
                }
            )
        )


@bp.get("/ha/status")
def ha_status():
    """
    Get system and component status.

    Useful for Home Assistant to check if fnOS_Overseer is running properly.
    """
    from core.config.config_manager import auth_config

    return jsonify(
        ok(
            {
                "status": "ok",
                "attributes": {
                    "friendly_name": "fnOS Overseer Status",
                    "version": os.getenv("APP_VERSION", "1.0.0"),
                    "environment": os.getenv("APP_ENV", "unknown"),
                    "auth_required": auth_config.requires_auth,
                    "is_production": auth_config.is_production,
                    "power_source": os.getenv("HA_POWER_SOURCE", "internal"),
                    "last_updated": importlib.import_module("datetime")
                    .datetime.now()
                    .isoformat(),
                },
            }
        )
    )
