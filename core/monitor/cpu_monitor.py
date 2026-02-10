import psutil
import json
import os
import platform
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CPUMonitor:
    def __init__(self, tdp_db_path=None):
        if tdp_db_path is None:
            # Default to hardware_tdp.json in the same directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            tdp_db_path = os.path.join(current_dir, "hardware_tdp.json")

        self.tdp_db_path = tdp_db_path
        self.tdp_data = self._load_tdp_db()
        self.cpu_model = self._get_cpu_model()
        self.cpu_tdp = self._get_cpu_tdp()

    def _load_tdp_db(self):
        try:
            if os.path.exists(self.tdp_db_path):
                with open(self.tdp_db_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                logger.warning(f"TDP database not found at {self.tdp_db_path}")
                return {}
        except Exception as e:
            logger.error(f"Failed to load TDP database: {e}")
            return {}

    def _get_cpu_model(self):
        try:
            # Platform specific CPU model retrieval
            system = platform.system()
            if system == "Darwin":
                # macOS
                command = "sysctl -n machdep.cpu.brand_string"
                return os.popen(command).read().strip()
            elif system == "Linux":
                # Linux
                command = "cat /proc/cpuinfo | grep 'model name' | uniq | cut -d: -f2"
                return os.popen(command).read().strip()
            elif system == "Windows":
                return platform.processor()
            else:
                return "Unknown CPU"
        except Exception as e:
            logger.error(f"Failed to get CPU model: {e}")
            return "Unknown CPU"

    def _get_cpu_tdp(self):
        cpu_db = self.tdp_data.get("cpu", {})
        # Simple string matching (can be improved with fuzzy match or regex)
        for model, tdp in cpu_db.items():
            if model in self.cpu_model:
                return tdp

        logger.info(f"CPU model '{self.cpu_model}' not found in DB, using default.")
        return cpu_db.get("default", 15)

    def get_cpu_info(self):
        return {
            "model": self.cpu_model,
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_cores": psutil.cpu_count(logical=True),
            "frequency_current": psutil.cpu_freq().current if psutil.cpu_freq() else 0,
            "tdp": self.cpu_tdp,
        }

    def get_cpu_usage(self, interval: float = 1.0):
        """
        Get CPU usage percentage.
        :param interval: blocking interval in seconds
        :return: float percentage
        """
        return psutil.cpu_percent(interval=interval)

    def estimate_cpu_power(self, usage_percent=None):
        """
        Estimate real-time CPU power consumption.
        Formula: Idle Power + (TDP - Idle Power) * (Usage% / 100) * Load_Factor
        Simplified: TDP * (0.2 + 0.8 * usage_percent / 100)
        Assuming idle power is roughly 20% of TDP.
        """
        if usage_percent is None:
            usage_percent = self.get_cpu_usage(interval=0.1)  # Non-blocking roughly

        # Simplified linear model
        # Base power (idle) assumption: 20% of TDP
        idle_ratio = 0.2
        active_ratio = 1.0 - idle_ratio

        estimated_power = self.cpu_tdp * (
            idle_ratio + active_ratio * (usage_percent / 100.0)
        )
        return round(estimated_power, 2)
