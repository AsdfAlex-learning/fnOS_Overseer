from typing import Dict, Any, Optional
from core.config.config_manager import get_value
from .api_client import APIClient
import psutil

class HardwareReader:
    def __init__(self, client: Optional[APIClient] = None):
        self.client = client or APIClient()
        self.hw_path = get_value("FNOS_HW_PATH", "/api/v1/hardware")

    def get_hardware_info(self) -> Dict[str, Any]:
        data = self.client.get(self.hw_path) or {}
        if not data:
            data = {}
        cpu = {
            "model": psutil.cpu_freq().current if psutil.cpu_freq() else 0,
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_cores": psutil.cpu_count(logical=True),
        }
        mem = psutil.virtual_memory()
        memory = {
            "total_gb": round(mem.total / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "percent": mem.percent,
        }
        storage = []
        for p in psutil.disk_partitions():
            try:
                u = psutil.disk_usage(p.mountpoint)
                storage.append({
                    "device": p.device,
                    "mountpoint": p.mountpoint,
                    "fstype": p.fstype,
                    "total_gb": round(u.total / (1024**3), 2),
                    "used_gb": round(u.used / (1024**3), 2),
                    "percent": u.percent,
                })
            except Exception:
                continue
        base = {"cpu": cpu, "memory": memory, "storage": storage}
        if isinstance(data, dict):
            base.update(data)
        return base
