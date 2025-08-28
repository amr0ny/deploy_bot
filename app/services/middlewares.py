import os
from aiogram import BaseMiddleware
from aiogram.types import Message
from typing import Callable, Awaitable

ADMIN_IDS = {int(x) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip().isdigit()}


class AdminOnlyMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, dict], Awaitable],
        event: Message,
        data: dict
    ):
        if event.from_user.id not in ADMIN_IDS:
            await event.answer('Недостаточно прав')
            return None
        return await handler(event, data)
