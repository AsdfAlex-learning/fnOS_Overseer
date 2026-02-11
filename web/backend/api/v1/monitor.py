import importlib
flask = importlib.import_module("flask")
jsonify = flask.jsonify
from web.backend.api.v1 import bp, require_super_admin
from core.monitor import CPUMonitor, StorageMonitor, PowerCalculator
from web.backend.models.data_models import ok

cpu = CPUMonitor()
storage = StorageMonitor()
power = PowerCalculator(cpu, storage)

@bp.get("/monitor/cpu")
@require_super_admin
def cpu_info():
    info = cpu.get_cpu_info()
    usage = cpu.get_cpu_usage(interval=0.2)
    p = cpu.estimate_cpu_power(usage)
    return jsonify(ok({"info": info, "usage_percent": usage, "power_watts": p}))

@bp.get("/monitor/storage")
@require_super_admin
def storage_info():
    return jsonify(ok(storage.get_storage_overview()))

@bp.get("/monitor/power")
@require_super_admin
def total_power():
    return jsonify(ok(power.estimate_total_power()))
