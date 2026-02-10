import psutil
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StorageMonitor:
    def __init__(self):
        pass

    def get_partitions(self):
        """
        Get all mounted partitions.
        """
        try:
            return psutil.disk_partitions()
        except Exception as e:
            logger.error(f"Failed to get disk partitions: {e}")
            return []

    def get_disk_usage(self, path='/'):
        """
        Get disk usage for a specific path.
        """
        try:
            usage = psutil.disk_usage(path)
            return {
                "total_gb": round(usage.total / (1024**3), 2),
                "used_gb": round(usage.used / (1024**3), 2),
                "free_gb": round(usage.free / (1024**3), 2),
                "percent": usage.percent
            }
        except Exception as e:
            logger.error(f"Failed to get disk usage for {path}: {e}")
            return None

    def get_io_counters(self, perdisk=True):
        """
        Get disk I/O statistics.
        """
        try:
            io = psutil.disk_io_counters(perdisk=perdisk)
            if perdisk:
                result = {}
                for disk, counters in io.items():
                    result[disk] = {
                        "read_bytes": counters.read_bytes,
                        "write_bytes": counters.write_bytes,
                        "read_count": counters.read_count,
                        "write_count": counters.write_count
                    }
                return result
            else:
                return {
                    "read_bytes": io.read_bytes,
                    "write_bytes": io.write_bytes,
                    "read_count": io.read_count,
                    "write_count": io.write_count
                }
        except Exception as e:
            logger.error(f"Failed to get IO counters: {e}")
            return {}
    
    def get_storage_overview(self):
        """
        Get a summary of storage status.
        """
        partitions = self.get_partitions()
        overview = []
        for p in partitions:
            # Filter for physical devices (approximate)
            if 'loop' in p.device:
                continue
                
            usage = self.get_disk_usage(p.mountpoint)
            if usage:
                overview.append({
                    "device": p.device,
                    "mountpoint": p.mountpoint,
                    "fstype": p.fstype,
                    "usage": usage
                })
        return overview
