import os
from aiogram import BaseMiddleware
from aiogram.types import Message
from typing import Callable, Dict, Any, Awaitable, TypeVar, List
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.provider.factories import TaskBrowserFactory
from src.provider.manager import AsyncProviderManager
from src.queues.factories import QueueFactory, TaskFactory
from src.queues.interfaces import Queue



T = TypeVar("T")

class DependencyMiddleware(BaseMiddleware):
    def __init__(self, key: str, dependency: T):
        self.key = key
        self.dependency = dependency

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        data[self.key] = self.dependency
        return await handler(event, data)

class DbMiddleware(BaseMiddleware):
    def __init__(self, session_maker: async_sessionmaker):
        self.session_maker = session_maker

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        async with self.session_maker() as session:
            data["db_session"] = session
            return await handler(event, data)

class AdminOnlyMiddleware(BaseMiddleware):
    def __init__(self, admin_ids: List[int]):
        self.admin_ids = admin_ids
    async def __call__(
        self,
        handler: Callable[[Message, dict], Awaitable],
        event: Message,
        data: Dict[str, Any],
    ):
        if event.from_user.id not in self.admin_ids:
            await event.answer("Недостаточно прав")
            return None
        return await handler(event, data)
