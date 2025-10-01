import asyncio
import logging
import os

from src.contexts import context_video
from src.interfaces import Command
from aiogram import Bot
from aiogram.types import FSInputFile
from src.provider.factories import AsyncTaskFactory
from src.provider.manager import AsyncProviderManager
from src.provider.tasks import AsyncTaskType

logger = logging.getLogger(__name__)

class TaskVideo(Command):
    def __init__(self, file_id: str, caption: str) -> Command:
        self.file_id = file_id
        self.caption = caption

    async def execute(self, bot: Bot, channel_id: str):
        await bot.send_video(channel_id, self.file_id, caption=self.caption)


class TaskLink(Command):
    def __init__(self, url: str) -> Command:
        self.url = url

    async def execute(
        self,
        bot: Bot,
        manager: AsyncProviderManager,
        factory: AsyncTaskFactory,
        channel_id: str,
    ):
        task_browser = factory.create(AsyncTaskType.VIDEO, url=self.url)
        filename = await manager.process_task(task_browser, timeout=10000)
        try:
            await bot.send_video(chat_id=channel_id, video=FSInputFile(filename), supports_streaming=True)
            await asyncio.sleep(5)

        except Exception as e:
            logger.error(f"Ошибка при отправке видео: {e}")

        finally:
            await self._safe_delete_file(filename)


    async def _safe_delete_file(self, filename: str):
        """Безопасное удаление файла с повторными попытками"""
        for attempt in range(3):
            try:
                if os.path.exists(filename):
                    os.remove(filename)
                    logger.info(f"Файл {filename} удален")
                    break
            except Exception as e:
                logger.warning(f"Не удалось удалить файл {filename} (попытка {attempt + 1}): {e}")
                await asyncio.sleep(1)


