import logging
from core.monitor.cpu_monitor import CPUMonitor
from core.monitor.storage_monitor import StorageMonitor

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PowerCalculator:
    def __init__(self, cpu_monitor=None, storage_monitor=None):
        self.cpu_monitor = cpu_monitor if cpu_monitor else CPUMonitor()
        self.storage_monitor = storage_monitor if storage_monitor else StorageMonitor()
        
        # Load constants from TDP DB or use defaults
        self.tdp_data = self.cpu_monitor.tdp_data # Reusing the loaded DB
        self.base_system_power = self.tdp_data.get('base_system', 10)
        
        self.disk_power_map = self.tdp_data.get('disk', {
            "default_hdd": 6.5,
            "default_ssd": 2.5,
            "default_nvme": 3.5,
            "idle_hdd": 0.8
        })
        
        self.memory_power_map = self.tdp_data.get('memory', {
            "ddr4_stick": 3.0,
            "ddr5_stick": 2.5
        })

    def estimate_disk_power(self, disk_count_hdd=0, disk_count_ssd=0, disk_count_nvme=0, active=True):
        """
        Estimate disk power based on counts and types.
        Note: Detecting disk type (HDD/SSD) automatically is hard without specific tools (like smartctl or lsblk -d -o rota).
        For now, we might rely on config or heuristic, but this method allows passing counts directly.
        """
        power = 0
        
        # HDD Power
        hdd_power_unit = self.disk_power_map.get('default_hdd', 6.5) if active else self.disk_power_map.get('idle_hdd', 0.8)
        power += disk_count_hdd * hdd_power_unit
        
        # SSD Power (SATA)
        ssd_power_unit = self.disk_power_map.get('default_ssd', 2.5)
        power += disk_count_ssd * ssd_power_unit
        
        # NVMe Power
        nvme_power_unit = self.disk_power_map.get('default_nvme', 3.5)
        power += disk_count_nvme * nvme_power_unit
        
        return power

    def estimate_total_power(self, cpu_usage_percent=None, disk_config=None):
        """
        Calculate total system power.
        :param cpu_usage_percent: Optional CPU usage override.
        :param disk_config: Dict with counts e.g. {'hdd': 2, 'ssd': 1, 'nvme': 1}
        """
        # 1. CPU Power
        cpu_power = self.cpu_monitor.estimate_cpu_power(cpu_usage_percent)
        
        # 2. Disk Power
        # In a real scenario, we'd try to auto-detect disk types. 
        # For this base version, we'll assume a simple count based on mounted physical devices if config not provided.
        if disk_config is None:
            # Very rough estimation based on mounted partitions
            # This is not accurate for RAID pools etc, but a starting point.
            # Ideally this should come from the Adapter layer or Config.
            partitions = self.storage_monitor.get_partitions()
            # Count unique devices (e.g. /dev/sda, /dev/sdb)
            devices = set()
            for p in partitions:
                if '/dev/' in p.device and 'loop' not in p.device:
                    # simplistic extraction of device name like /dev/sda
                    # Note: this might count partitions as devices depending on OS
                    # better to use psutil.disk_io_counters() keys
                    devices.add(p.device)
            
            # Assume all detected are HDDs for safety (higher power estimate) if unknown
            disk_config = {'hdd': len(devices), 'ssd': 0, 'nvme': 0}
        
        disk_power = self.estimate_disk_power(
            disk_count_hdd=disk_config.get('hdd', 0),
            disk_count_ssd=disk_config.get('ssd', 0),
            disk_count_nvme=disk_config.get('nvme', 0)
        )
        
        # 3. Memory Power (Static estimation for now)
        # Assuming 2 sticks of DDR4 as default if not configurable
        mem_power = 2 * self.memory_power_map.get('ddr4_stick', 3.0)
        
        # 4. Total
        total_power = self.base_system_power + cpu_power + disk_power + mem_power
        
        return {
            "total_watts": round(total_power, 2),
            "breakdown": {
                "base": self.base_system_power,
                "cpu": cpu_power,
                "disk": disk_power,
                "memory": mem_power
            }
        }
