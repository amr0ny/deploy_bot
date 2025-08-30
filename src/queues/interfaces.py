from abc import ABC, abstractmethod
from typing import AsyncIterable, Optional, Generic, TypeVar
import asyncio

from src.interfaces import Command

T = TypeVar("T", bound="Task")


class Queue(ABC, Generic[T]):
    """Основной интерфейс очереди"""

    @abstractmethod
    async def put(self, item: T) -> None:
        pass

    @abstractmethod
    async def get(self) -> T:
        pass

    @abstractmethod
    async def size(self) -> int:
        pass

    @abstractmethod
    async def is_empty(self) -> bool:
        pass


class AsyncQueue(Queue[T]):
    """Расширенный асинхронный интерфейс с дополнительными методами"""

    @abstractmethod
    async def get_nowait(self) -> T:
        pass

    @abstractmethod
    async def get(self, timeout: Optional[float] = None) -> T:
        """Перегруженный метод с таймаутом"""
        pass

    @abstractmethod
    async def put_nowait(self, item: T) -> None:
        pass

    @abstractmethod
    async def clear(self) -> None:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass

    @abstractmethod
    def __aiter__(self) -> AsyncIterable[T]:
        pass

    @abstractmethod
    async def set_flag(self, value: bool) -> None:
        pass

    @abstractmethod
    async def get_flag(self) -> bool:
        pass

    @abstractmethod
    async def flag_context(self, value: bool):
        pass
