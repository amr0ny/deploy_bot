from abc import ABC, abstractmethod
from typing import Any


class Command(ABC):
    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        """Основная логика выполнения задачи."""
        pass
