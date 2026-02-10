from datetime import datetime, date
from typing import Optional, Dict, Any
from core.monitor import CPUMonitor, StorageMonitor, PowerCalculator

try:
    from adapter.fnos import log_parser as fnos_log_parser
except Exception:
    fnos_log_parser = None

class DailyReportBuilder:
    def __init__(self):
        self.cpu_monitor = CPUMonitor()
        self.storage_monitor = StorageMonitor()
        self.power_calc = PowerCalculator(self.cpu_monitor, self.storage_monitor)

    def build(self, for_date: Optional[date] = None) -> Dict[str, Any]:
        now = datetime.now()
        d = for_date or now.date()
        cpu_info = self.cpu_monitor.get_cpu_info()
        cpu_usage = self.cpu_monitor.get_cpu_usage(interval=0.5)
        power = self.power_calc.estimate_total_power(cpu_usage_percent=cpu_usage)
        storage = self.storage_monitor.get_storage_overview()
        logs = {"login_events": [], "user_actions": []}
        if fnos_log_parser:
            try:
                logs["login_events"] = fnos_log_parser.parse_login_events(d)
            except Exception:
                logs["login_events"] = []
            try:
                logs["user_actions"] = fnos_log_parser.parse_user_actions(d)
            except Exception:
                logs["user_actions"] = []
        return {
            "meta": {
                "date": d.isoformat(),
                "generated_at": now.isoformat()
            },
            "cpu": {
                "info": cpu_info,
                "usage_percent": cpu_usage
            },
            "power": power,
            "storage": storage,
            "logs": logs
        }
