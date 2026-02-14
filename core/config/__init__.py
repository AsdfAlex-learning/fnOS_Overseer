# Configuration management
from .config_manager import ConfigManager, get_config, get_value, _GLOBAL as _global_manager

# Create a config_manager namespace for accessing the global instance
class _ConfigManagerNamespace:
    @property
    def _GLOBAL(self):
        return _global_manager

config_manager = _ConfigManagerNamespace()

__all__ = ["ConfigManager", "get_config", "get_value", "config_manager"]

