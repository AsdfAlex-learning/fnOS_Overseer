from abc import ABC, abstractmethod
from typing import Dict, Any, List
from datetime import date

class BaseAdapter(ABC):
    @abstractmethod
    def get_hardware_info(self) -> Dict[str, Any]:
        ...

    @abstractmethod
    def get_logs(self, for_date: date) -> Dict[str, List[Dict[str, Any]]]:
        ...
