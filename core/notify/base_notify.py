from abc import ABC, abstractmethod
from typing import List, Optional

class BaseNotify(ABC):
    @abstractmethod
    def send(self, subject: str, content: str, to: Optional[List[str]] = None) -> bool:
        ...
