import asyncio
import json
from typing import TypeVar, Optional, AsyncIterator
import redis.asyncio as redis
from contextlib import asynccontextmanager

from src.queues.interfaces import AsyncQueue

T = TypeVar('T')


class RedisAsyncQueue(AsyncQueue[T]):
    """
    Асинхронная очередь на основе Redis
    """

    async def put(self, item: T) -> None:
        pass

    def __init__(
            self,
            queue_name: str,
            redis_url: str = "redis://localhost:6379",
            serializer: callable = json.dumps,
            deserializer: callable = json.loads,
            flag_key_suffix: str = "_flag"
    ):
        self.queue_name = queue_name
        self.redis_url = redis_url
        self.serializer = serializer
        self.deserializer = deserializer
        self.flag_key = f"{queue_name}{flag_key_suffix}"

        self._redis: Optional[redis.Redis] = None
        self._closed = False

    async def _ensure_connection(self) -> redis.Redis:
        """Обеспечивает подключение к Redis"""
        if self._closed:
            raise RuntimeError("Queue is closed")

        if self._redis is None:
            self._redis = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )

        return self._redis

    async def put(self, item: T, timeout: Optional[float] = None) -> None:
        """
        Добавление элемента в очередь с возможностью таймаута

        Args:
            item: Элемент для добавления
            timeout: Таймаут в секундах (для Redis обычно не нужен,
                     но реализован для совместимости с интерфейсом)

        Raises:
            asyncio.TimeoutError: Если таймаут истек
        """
        if timeout is not None:
            # Реализация с таймаутом
            try:
                await asyncio.wait_for(self.put_nowait(item), timeout=timeout)
            except asyncio.TimeoutError:
                raise asyncio.TimeoutError(f"Timeout while putting item to queue {self.queue_name}")
        else:
            # Без таймаута - обычное добавление
            await self.put_nowait(item)

    async def put_nowait(self, item: T) -> None:
        """
        Добавление элемента в очередь без ожидания

        Args:
            item: Элемент для добавления
        """
        redis_client = await self._ensure_connection()
        serialized_item = self.serializer(item)
        await redis_client.lpush(self.queue_name, serialized_item)

    async def get_nowait(self) -> T:
        """
        Получение элемента из очереди без ожидания

        Returns:
            Элемент из очереди

        Raises:
            asyncio.QueueEmpty: Если очередь пуста
        """
        redis_client = await self._ensure_connection()
        serialized_item = await redis_client.rpop(self.queue_name)

        if serialized_item is None:
            raise asyncio.QueueEmpty(f"Queue {self.queue_name} is empty")

        return self.deserializer(serialized_item)

    async def get(self, timeout: Optional[float] = None) -> T:
        """
        Получение элемента из очереди с возможностью таймаута

        Args:
            timeout: Таймаут в секундах

        Returns:
            Элемент из очереди

        Raises:
            asyncio.QueueEmpty: Если очередь пуста и таймаут истек
        """
        if timeout is None:
            # Без таймаута - используем обычное получение
            return await self.get_nowait()

        try:
            # Используем brpop с таймаутом
            redis_client = await self._ensure_connection()
            result = await redis_client.brpop(
                self.queue_name,
                timeout=timeout
            )

            if result is None:
                raise asyncio.QueueEmpty(f"Queue {self.queue_name} is empty")

            # result содержит (key, value)
            _, serialized_item = result
            return self.deserializer(serialized_item)

        except asyncio.TimeoutError:
            raise asyncio.QueueEmpty(f"Timeout while waiting for item in {self.queue_name}")

    async def clear(self) -> None:
        """Очистка очереди"""
        redis_client = await self._ensure_connection()
        await redis_client.delete(self.queue_name)
        await redis_client.delete(self.flag_key)

    async def close(self) -> None:
        """Закрытие соединения с Redis"""
        self._closed = True
        if self._redis is not None:
            await self._redis.close()
            self._redis = None

    def __aiter__(self) -> AsyncIterator[T]:
        """
        Возвращает асинхронный итератор

        Returns:
            Асинхронный итератор
        """
        return self._QueueIterator(self)

    class _QueueIterator:
        """Внутренний класс итератора для очереди"""

        def __init__(self, queue: 'RedisAsyncQueue'):
            self.queue = queue

        def __aiter__(self) -> AsyncIterator[T]:
            return self

        async def __anext__(self) -> T:
            """
            Получение следующего элемента

            Returns:
                Следующий элемент из очереди

            Raises:
                StopAsyncIteration: Когда очередь закрыта или достигнут конец
            """
            try:
                # Получаем элемент с небольшим таймаутом для возможности прерывания
                return await self.queue.get(timeout=1.0)
            except asyncio.QueueEmpty:
                # Проверяем, не закрыта ли очередь
                if self.queue._closed:
                    raise StopAsyncIteration
                # Продолжаем ждать новые элементы
                return await self.__anext__()
            except RuntimeError:
                # Очередь закрыта
                raise StopAsyncIteration

    async def set_flag(self, value: bool) -> None:
        """
        Установка флага в Redis

        Args:
            value: Значение флага
        """
        redis_client = await self._ensure_connection()
        await redis_client.set(self.flag_key, "1" if value else "0")

    async def get_flag(self) -> bool:
        """
        Получение значения флага из Redis

        Returns:
            Значение флага
        """
        redis_client = await self._ensure_connection()
        value = await redis_client.get(self.flag_key)
        return value == "1" if value is not None else False

    @asynccontextmanager
    async def flag_context(self, value: bool):
        """
        Контекстный менеджер для временного изменения флага

        Args:
            value: Временное значение флага
        """
        original_value = await self.get_flag()
        await self.set_flag(value)

        try:
            yield
        finally:
            await self.set_flag(original_value)

    async def size(self) -> int:
        """
        Получение размера очереди

        Returns:
            Количество элементов в очереди
        """
        redis_client = await self._ensure_connection()
        return await redis_client.llen(self.queue_name)

    async def is_empty(self) -> bool:
        """
        Проверка, пуста ли очередь

        Returns:
            True если очередь пуста
        """
        return await self.size() == 0

    async def peek(self) -> Optional[T]:
        """
        Просмотр последнего элемента без его удаления

        Returns:
            Последний элемент или None если очередь пуста
        """
        redis_client = await self._ensure_connection()
        serialized_item = await redis_client.lindex(self.queue_name, -1)

        if serialized_item is None:
            return None

        return self.deserializer(serialized_item)