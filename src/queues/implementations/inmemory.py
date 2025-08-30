import asyncio
from contextlib import asynccontextmanager
from typing import Optional, AsyncIterable

from src.queues.interfaces import AsyncQueue, T


class InMemoryQueue(AsyncQueue[T]):
    """
    Асинхронная очередь в оперативной памяти на основе asyncio.Queue.
    Потокобезопасна и предназначена для использования в async/await коде.
    """

    def __init__(self, maxsize: int = 0, name: str = "default"):
        """
        Инициализирует очередь.

        :param maxsize: Максимальный размер очереди (0 - без ограничений)
        :param name: Имя очереди для идентификации
        """
        self._queue = asyncio.Queue(maxsize=maxsize)
        self._name = name
        self._closed = False
        self._total_processed = 0
        self._total_added = 0
        self._flag = False
        self._flag_lock = asyncio.Lock()

    async def put(self, item: T) -> None:
        """
        Добавляет элемент в очередь.
        Блокируется, если очередь полная.

        :param item: Элемент для добавления
        :raises RuntimeError: Если очередь закрыта
        """
        if self._closed:
            raise RuntimeError(f"Queue '{self._name}' is closed")

        await self._queue.put(item)
        self._total_added += 1

    async def put_nowait(self, item: T) -> None:
        """
        Добавляет элемент в очередь без блокировки.

        :param item: Элемент для добавления
        :raises RuntimeError: Если очередь закрыта
        :raises asyncio.QueueFull: Если очередь полная
        """
        if self._closed:
            raise RuntimeError(f"Queue '{self._name}' is closed")

        self._queue.put_nowait(item)
        self._total_added += 1

    async def get(self, timeout: Optional[float] = None) -> T:
        """
        Извлекает элемент из очереди.
        Блокируется, если очередь пустая.

        :param timeout: Таймаут в секундах
        :return: Извлеченный элемент
        :raises asyncio.TimeoutError: Если таймаут истек
        :raises RuntimeError: Если очередь закрыта и пуста
        """
        if self._closed and self._queue.empty():
            raise RuntimeError(f"Queue '{self._name}' is closed and empty")

        if timeout is None:
            item = await self._queue.get()
        else:
            item = await asyncio.wait_for(self._queue.get(), timeout)

        self._total_processed += 1
        return item

    async def get_nowait(self) -> T:
        """
        Извлекает элемент из очереди без блокировки.

        :return: Извлеченный элемент
        :raises asyncio.QueueEmpty: Если очередь пустая
        :raises RuntimeError: Если очередь закрыта и пуста
        """
        if self._closed and self._queue.empty():
            raise RuntimeError(f"Queue '{self._name}' is closed and empty")

        item = self._queue.get_nowait()
        self._total_processed += 1
        return item

    async def size(self) -> int:
        """Возвращает текущее количество элементов в очереди."""
        return self._queue.qsize()

    async def is_empty(self) -> bool:
        """Проверяет, пуста ли очередь."""
        return self._queue.empty()

    async def clear(self) -> None:
        """Очищает очередь от всех элементов."""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    async def close(self) -> None:
        """
        Закрывает очередь. Новые элементы добавить нельзя.
        Существующие элементы можно обработать.
        """
        self._closed = True

    def is_closed(self) -> bool:
        """Проверяет, закрыта ли очередь."""
        return self._closed

    async def get_stats(self) -> dict:
        """Возвращает статистику по очереди."""
        return {
            "name": self._name,
            "current_size": await self.size(),
            "is_empty": await self.is_empty(),
            "is_closed": self.is_closed(),
            "total_added": self._total_added,
            "total_processed": self._total_processed,
            "pending": self._total_added - self._total_processed,
        }

    def __aiter__(self) -> AsyncIterable[T]:
        """Возвращает асинхронный итератор по элементам очереди."""
        return self

    async def __anext__(self) -> T:
        """
        Возвращает следующий элемент из очереди.
        Итерация завершается, когда очередь закрыта и пуста.
        """
        if self._closed and self._queue.empty():
            raise StopAsyncIteration

        try:
            return await self.get()
        except RuntimeError:
            raise StopAsyncIteration

    @asynccontextmanager
    async def processing_context(self, timeout: Optional[float] = None):
        """
        Контекстный менеджер для обработки задач с автоматическим подтверждением.

        Usage:
        async with queue.processing_context() as task:
            await task.execute()
        """
        task = await self.get(timeout)
        try:
            yield task
        finally:
            self._queue.task_done()

    async def set_flag(self, value: bool) -> None:
        """Установить флаг с блокировкой."""
        async with self._flag_lock:
            self._flag = value

    async def get_flag(self) -> bool:
        """Получить значение флага."""
        async with self._flag_lock:
            return self._flag

    @asynccontextmanager
    async def flag_context(self, value: bool):
        """Контекстный менеджер для временного изменения флага."""
        original_value = await self.get_flag()
        try:
            await self.set_flag(value)
            yield
        finally:
            await self.set_flag(original_value)
