"""
Power consumption calculator with external monitoring source support.

This module calculates system power consumption with the following priority:
1. External monitoring (HA sensors / MQTT / external API)
2. Internal estimation (CPU + disk + memory)
"""
import logging
import os
from typing import Dict, Optional, Any

from core.monitor.cpu_monitor import CPUMonitor
from core.monitor.storage_monitor import StorageMonitor
from .disk_detector import get_disk_detector, DiskType

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PowerCalculator:
    def __init__(self, cpu_monitor=None, storage_monitor=None):
        self.cpu_monitor = cpu_monitor if cpu_monitor else CPUMonitor()
        self.storage_monitor = storage_monitor if storage_monitor else StorageMonitor()
        self.disk_detector = get_disk_detector()

        # Load constants from TDP DB or use defaults
        self.tdp_data = self.cpu_monitor.tdp_data  # Reusing the loaded DB
        self.base_system_power = self.tdp_data.get('base_system', 10)

        # Load hardware TDP from config (user configurable)
        # These override the TDP DB if user provides values
        self.cpu_tdp = os.getenv("HARDWARE_TDP_CPU", "")
        self.hdd_idle_power = os.getenv("HARDWARE_TDP_HDD_IDLE", "")
        self.hdd_active_power = os.getenv("HARDWARE_TDP_HDD_ACTIVE", "")
        self.ssd_power = os.getenv("HARDWARE_TDP_SSD", "")
        self.nvme_power = os.getenv("HARDWARE_TDP_NVME", "")
        self.memory_power = os.getenv("HARDWARE_TDP_MEMORY", "")

        self.disk_power_map = self.tdp_data.get('disk', {
            "default_hdd": 6.5,
            "default_ssd": 2.5,
            "default_nvme": 3.5,
            "idle_hdd": 0.8
        })

        # Use configured values if provided, otherwise use defaults
        self.hdd_idle = float(self.hdd_idle_power) if self.hdd_idle_power else self.disk_power_map.get('default_hdd', 6.5)
        self.hdd_active = float(self.hdd_active_power) if self.hdd_active_power else self.disk_power_map.get('default_hdd', 6.5)
        self.ssd = float(self.ssd_power) if self.ssd_power else self.disk_power_map.get('default_ssd', 2.5)
        self.nvme = float(self.nvme_power) if self.nvme_power else self.disk_power_map.get('default_nvme', 3.5)
        self.mem_stick = float(self.memory_power) if self.memory_power else self.tdp_data.get('memory', {}).get('ddr4_stick', 3.0)

        # Determine if external monitoring is configured
        self.power_source = os.getenv("HA_POWER_SOURCE", "internal").lower()
        logger.info(f"Power source configured: {self.power_source}")

    def _get_tdp_cpu(self) -> float:
        """Get CPU TDP from user config or default."""
        if self.cpu_tdp:
            return float(self.cpu_tdp)
        # Fallback to DB or default
        return float(self.cpu_monitor.cpu_tdp if hasattr(self.cpu_monitor, 'cpu_tdp') else 15)

    def estimate_cpu_power(self, usage_percent=None) -> float:
        """
        Estimate real-time CPU power consumption.

        Formula: Idle Power + (TDP - Idle Power) * (Usage% / 100) * Load_Factor
        Simplified: TDP * (0.2 + 0.8 * usage_percent / 100)
        Assuming idle power is roughly 20% of TDP.
        """
        if usage_percent is None:
            usage_percent = self.cpu_monitor.get_cpu_usage(interval=0.1)  # Non-blocking roughly

        cpu_tdp = self._get_tdp_cpu()
        idle_ratio = 0.2
        active_ratio = 1.0 - idle_ratio

        estimated_power = cpu_tdp * (idle_ratio + active_ratio * (usage_percent / 100.0))
        return round(estimated_power, 2)

    def estimate_disk_power(self, disk_count_hdd=0, disk_count_ssd=0, disk_count_nvme=0, active=True) -> float:
        """
        Estimate disk power based on counts and types.

        Args:
            disk_count_hdd: Number of HDD disks
            disk_count_ssd: Number of SATA SSD disks
            disk_count_nvme: Number of NVMe SSD disks
            active: Whether disks are active (idle disks use less power)

        Returns:
            Estimated power in watts
        """
        power = 0

        # HDD Power
        hdd_power_unit = self.hdd_active if active else self.hdd_idle
        power += disk_count_hdd * hdd_power_unit

        # SSD Power (SATA)
        ssd_power_unit = self.ssd
        power += disk_count_ssd * ssd_power_unit

        # NVMe Power
        nvme_power_unit = self.nvme
        power += disk_count_nvme * nvme_power_unit

        return power

    def estimate_total_power(
        self,
        cpu_usage_percent=None,
        disk_config=None,
        use_external: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calculate total system power.

        Args:
            cpu_usage_percent: Optional CPU usage override.
            disk_config: Dict with counts e.g. {'hdd': 2, 'ssd': 1, 'nvme': 1}
                           If None, auto-detect disk types using DiskDetector.
            use_external: External power monitoring data (from HA/MQTT/API).
                           If provided, uses this value and skips internal calculation.

        Returns:
            Dict with total power and breakdown by component.
        """
        # Check for external power monitoring data first (highest priority)
        if use_external:
            external_power = use_external.get('power_watts')
            if external_power and isinstance(external_power, (int, float)):
                logger.debug(f"Using external power: {external_power}W")
                return {
                    "total_watts": round(float(external_power), 2),
                    "breakdown": {
                        "source": "external_monitoring",
                        "total": round(float(external_power), 2),
                        "external_data": use_external
                    },
                    "disk_counts": use_external.get('disk_counts', {})
                }

        # Internal estimation
        logger.debug("Using internal power estimation")

        # 1. CPU Power
        cpu_power = self.estimate_cpu_power(cpu_usage_percent)

        # 2. Disk Power
        if disk_config is None:
            # Auto-detect disk types using DiskDetector
            try:
                disk_counts = self.disk_detector.get_disk_counts()
                detection_summary = self.disk_detector.get_detection_summary()

                if detection_summary['unknown_types'] > 0:
                    logger.warning(
                        f"Using estimated power for {detection_summary['unknown_types']} "
                        f"unknown disk type(s). Results may be inaccurate."
                    )

                logger.info(
                    f"Disk power calculation: "
                    f"HDD={disk_counts['hdd']}, SSD={disk_counts['ssd']}, NVMe={disk_counts['nvme']}"
                )

            except Exception as e:
                logger.error(f"Failed to detect disk types: {e}", exc_info=True)
                # Fallback to conservative estimate (assume all detected are SSD)
                partitions = self.storage_monitor.get_partitions()
                device_count = len(set(
                    p.device for p in partitions
                    if '/dev/' in p.device and 'loop' not in p.device
                ))
                disk_counts = {'hdd': 0, 'ssd': device_count, 'nvme': 0}
                logger.warning(f"Using fallback: {disk_counts['ssd']} SSDs detected")
        else:
            # Use provided disk configuration
            disk_counts = disk_config

        disk_power = self.estimate_disk_power(
            disk_count_hdd=disk_counts.get('hdd', 0),
            disk_count_ssd=disk_counts.get('ssd', 0),
            disk_count_nvme=disk_counts.get('nvme', 0)
        )

        # 3. Memory Power (Use configured value)
        mem_power = self.mem_stick * 2  # Assume 2 sticks

        # 4. Total
        total_power = self.base_system_power + cpu_power + disk_power + mem_power

        return {
            "total_watts": round(total_power, 2),
            "breakdown": {
                "source": "internal_estimation",
                "total": round(total_power, 2),
                "base": self.base_system_power,
                "cpu": cpu_power,
                "disk": disk_power,
                "memory": mem_power
            },
            "disk_counts": disk_counts
        }
