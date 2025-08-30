import os
from typing import Type, Dict, Any

from src.interfaces import Command
from aiogram import Bot
from aiogram.types import FSInputFile
from enum import Enum

from src.provider.factories import TaskBrowserFactory
from src.provider.manager import AsyncProviderManager
from src.provider.tasks import TaskBrowserType, TaskBrowserVideo
from src.utils import extract_mp4_url


class TaskVideo(Command):
    def __init__(self, file_id: str, caption: str) -> Command:
        self.file_id = file_id
        self.caption = caption

    async def execute(self, bot: Bot, channel_id: str):
        await bot.send_video(
            channel_id, self.file_id, caption=self.caption
        )


class TaskLink(Command):
    def __init__(self, url: str, caption) -> Command:
        self.url = url
        self.caption = caption

    async def execute(
        self, bot: Bot, manager: AsyncProviderManager, factory: TaskBrowserFactory, channel_id: str
    ):
        task_browser = factory.create(TaskBrowserType.VIDEO, url=self.url)
        encoded_url = await manager.process_task(task_browser, timeout=10000)
        url = extract_mp4_url(encoded_url)
        message = await bot.send_video(
            chat_id=channel_id,
            video=url,
            caption=self.caption,
            supports_streaming=True,
        )
