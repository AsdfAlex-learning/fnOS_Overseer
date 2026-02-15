"""
Disk type detection for Linux-based NAS systems.

This module provides methods to detect disk types (HDD/SSD/NVMe) using:
1. Linux /sys filesystem (preferred, no root required)
2. lsblk command (medium reliability)
3. smartctl command (requires root/privileged)

For fnOS (Linux-based NAS), this should work with privileged Docker containers.
"""
import os
import logging
from typing import Dict, List, Optional, Tuple
import subprocess

logger = logging.getLogger(__name__)


class DiskType:
    """Disk type enumeration."""
    UNKNOWN = "unknown"
    HDD = "hdd"
    SSD = "ssd"
    NVME = "nvme"


class DiskDetector:
    """Detect disk types using multiple methods with fallback."""

    def __init__(self):
        self._cache = {}  # Cache detection results

    def detect_disk_types(self) -> Dict[str, str]:
        """
        Detect types of all disks in the system.

        Returns:
            Dict mapping device names (sda, sdb, nvme0n1, etc.) to disk types
            Possible types: 'hdd', 'ssd', 'nvme', 'unknown'
        """
        devices = self._get_all_devices()
        results = {}

        for device in devices:
            # Normalize device name (e.g., sda from /dev/sda, nvme0n1 from /dev/nvme0n1)
            device_name = self._normalize_device_name(device)

            # Check cache first
            if device_name in self._cache:
                results[device_name] = self._cache[device_name]
                continue

            # Try detection methods in order of preference
            disk_type = self._detect_by_sys_file(device_name)
            if disk_type == DiskType.UNKNOWN:
                disk_type = self._detect_by_lsblk(device_name)
            if disk_type == DiskType.UNKNOWN:
                disk_type = self._detect_by_smartctl(device_name)
            if disk_type == DiskType.UNKNOWN:
                disk_type = self._detect_by_naming(device_name)

            # Cache and store result
            self._cache[device_name] = disk_type
            results[device_name] = disk_type

            if disk_type != DiskType.UNKNOWN:
                logger.info(f"Detected disk {device_name} as {disk_type}")
            else:
                logger.warning(f"Could not determine disk type for {device_name}")

        return results

    def _get_all_devices(self) -> List[str]:
        """Get all block devices in the system."""
        devices = []

        # Method 1: Scan /sys/block
        sys_block = "/sys/block"
        if os.path.exists(sys_block):
            for device in os.listdir(sys_block):
                # Skip partitions and loop devices
                if not device.isdigit() and not device.startswith("loop"):
                    devices.append(device)

        # Method 2: Scan /dev/ as fallback
        if not devices:
            try:
                dev_entries = os.listdir("/dev")
                for entry in dev_entries:
                    # Include sd*, nvme*, vd* (common disk names)
                    if any(entry.startswith(prefix) for prefix in ["sd", "nvme", "vd"]):
                        # Skip partitions (e.g., sda1)
                        if not any(c.isdigit() and c != entry[-1] for c in entry):
                            devices.append(entry)
            except (PermissionError, OSError) as e:
                logger.warning(f"Could not scan /dev: {e}")

        return devices

    def _normalize_device_name(self, device: str) -> str:
        """
        Normalize device name to base device.

        Examples:
            sda -> sda
            sda1 -> sda
            nvme0n1 -> nvme0
            nvme0 -> nvme0
        """
        # Remove partition numbers
        # For nvme: nvme0n1 -> nvme0
        if "n" in device:
            idx = device.index("n")
            return device[:idx]

        # For regular: sda1 -> sda
        import re
        match = re.match(r"([a-z]+)[0-9]*", device)
        if match:
            return match.group(1)

        return device

    def _detect_by_sys_file(self, device: str) -> str:
        """
        Detect disk type using /sys filesystem (preferred method).

        This method does NOT require root privileges.

        Checks /sys/block/<device>/queue/rotational
        - 0 = SSD (non-rotational)
        - 1 = HDD (rotational)
        - File not found = unknown
        """
        sys_path = f"/sys/block/{device}/queue/rotational"

        if not os.path.exists(sys_path):
            return DiskType.UNKNOWN

        try:
            with open(sys_path, "r") as f:
                rotational = f.read().strip()

            if rotational == "0":
                # Check if it's NVMe
                if device.startswith("nvme"):
                    return DiskType.NVME
                return DiskType.SSD
            elif rotational == "1":
                return DiskType.HDD
            else:
                logger.warning(f"Unexpected rotational value for {device}: {rotational}")
                return DiskType.UNKNOWN

        except (PermissionError, IOError) as e:
            logger.debug(f"Could not read {sys_path}: {e}")
            return DiskType.UNKNOWN

    def _detect_by_lsblk(self, device: str) -> str:
        """
        Detect disk type using lsblk command.

        This method usually works without root privileges
        but may have limited output on some systems.

        Checks ROTA (ROTATional) column:
        - 0 = SSD/NVMe
        - 1 = HDD
        """
        try:
            # Run lsblk to get rotational info
            result = subprocess.run(
                ["lsblk", "-d", "-n", "-o", "NAME,ROTA"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                logger.debug(f"lsblk failed: {result.stderr}")
                return DiskType.UNKNOWN

            # Parse output
            for line in result.stdout.strip().split('\n'):
                if line.startswith(device):
                    parts = line.split()
                    if len(parts) >= 2:
                        rota = parts[1]
                        if rota == "0":
                            return DiskType.NVME if device.startswith("nvme") else DiskType.SSD
                        elif rota == "1":
                            return DiskType.HDD

            return DiskType.UNKNOWN

        except FileNotFoundError:
            logger.debug("lsblk command not found")
            return DiskType.UNKNOWN
        except subprocess.TimeoutExpired:
            logger.warning("lsblk command timed out")
            return DiskType.UNKNOWN
        except Exception as e:
            logger.debug(f"lsblk error: {e}")
            return DiskType.UNKNOWN

    def _detect_by_smartctl(self, device: str) -> str:
        """
        Detect disk type using smartctl command.

        This method REQUIRES root privileges or privileged container.

        Checks if device is rotational.
        - non-rotational = SSD/NVMe
        - rotational = HDD

        Note: This requires /dev/sda, /dev/sdb, etc. as input.
        """
        # Map device name to /dev path
        dev_path = f"/dev/{device}"

        # For NVMe, need to strip partition
        if "n" in device:
            idx = device.index("n")
            dev_path = f"/dev/{device[:idx]}"

        try:
            # Run smartctl with -a (all) flag
            result = subprocess.run(
                ["smartctl", "-a", dev_path],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 1:
                # Access denied or permission error
                logger.warning(f"smartctl access denied for {dev_path}")
                return DiskType.UNKNOWN

            if result.returncode != 0:
                logger.debug(f"smartctl failed for {dev_path}: {result.stderr}")
                return DiskType.UNKNOWN

            # Check for "Rotation Rate" in output
            if "Rotation Rate:" in result.stdout:
                # Has rotation rate = HDD
                return DiskType.SSD  # Smartctl can't distinguish, treat as SSD
            elif "non-rotational" in result.stdout or "SSD" in result.stdout:
                return DiskType.NVME if device.startswith("nvme") else DiskType.SSD
            else:
                # No rotation rate mentioned, likely SSD/NVMe
                return DiskType.NVME if device.startswith("nvme") else DiskType.SSD

        except FileNotFoundError:
            logger.debug("smartctl command not found")
            return DiskType.UNKNOWN
        except subprocess.TimeoutExpired:
            logger.warning("smartctl command timed out")
            return DiskType.UNKNOWN
        except Exception as e:
            logger.debug(f"smartctl error for {dev_path}: {e}")
            return DiskType.UNKNOWN

    def _detect_by_naming(self, device: str) -> str:
        """
        Detect disk type based on naming convention (fallback method).

        This is a heuristic and not always reliable:
        - nvme* = NVMe SSD
        - sd* = Unknown (could be HDD or SSD)
        - vd* = Virtual disk (usually SSD)
        """
        if device.startswith("nvme"):
            return DiskType.NVME
        elif device.startswith("vd"):
            # Virtual disk (common in VMs), assume SSD for safety
            return DiskType.SSD
        elif device.startswith("sd"):
            # sda, sdb... could be either, conservative to assume SSD
            return DiskType.SSD
        else:
            return DiskType.UNKNOWN

    def get_disk_counts(self) -> Dict[str, int]:
        """
        Get counts of each disk type.

        Returns:
            Dict with keys: 'hdd', 'ssd', 'nvme'
        """
        disk_types = self.detect_disk_types()
        counts = {
            DiskType.HDD: 0,
            DiskType.SSD: 0,
            DiskType.NVME: 0
        }

        for disk_type in disk_types.values():
            if disk_type in counts:
                counts[disk_type] += 1

        return {
            'hdd': counts[DiskType.HDD],
            'ssd': counts[DiskType.SSD],
            'nvme': counts[DiskType.NVME]
        }

    def get_detection_summary(self) -> Dict[str, any]:
        """
        Get summary of disk detection results.

        Returns:
            Dict with detection method results and statistics.
        """
        disk_types = self.detect_disk_types()
        total = len(disk_types)
        known = sum(1 for t in disk_types.values() if t != DiskType.UNKNOWN)

        return {
            "total_disks": total,
            "known_types": known,
            "unknown_types": total - known,
            "by_type": {
                "hdd": sum(1 for t in disk_types.values() if t == DiskType.HDD),
                "ssd": sum(1 for t in disk_types.values() if t == DiskType.SSD),
                "nvme": sum(1 for t in disk_types.values() if t == DiskType.NVME),
                "unknown": sum(1 for t in disk_types.values() if t == DiskType.UNKNOWN),
            },
            "devices": disk_types
        }


# Global detector instance
_disk_detector = None


def get_disk_detector() -> DiskDetector:
    """Get or create the global disk detector instance."""
    global _disk_detector
    if _disk_detector is None:
        _disk_detector = DiskDetector()
        logger.info("Disk detector initialized")
    return _disk_detector
