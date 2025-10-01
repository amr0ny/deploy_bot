import uuid
from pathlib import Path

import aiohttp
import os
from contextlib import asynccontextmanager
from aiogram.types import FSInputFile
from typing import AsyncGenerator

from src.config import AppConfig


@asynccontextmanager
async def context_video(url: str, filename: str = f"{uuid.uuid4()}.mp4") -> AsyncGenerator[FSInputFile, None]:
    """
    Асинхронный контекстный менеджер для скачивания видео и автоматического удаления файла.

    Использование:
        async with download_video(url) as video_file:
            await bot.send_video(chat_id, video_file)
    """
    # Скачиваем видео
    config = AppConfig()
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise ValueError(f"Не удалось скачать видео: {url}")
            content = await resp.read()
    path = Path(config, filename)
    # Сохраняем в файл
    with open(path, "wb") as f:
        f.write(content)

    # Передаём FSInputFile в блок
    try:
        yield FSInputFile(path)
    finally:
        # Удаляем файл после выхода из блока
        if os.path.exists(path):
            os.remove(path)
