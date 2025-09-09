from playwright.sync_api import Browser

from abc import ABC, abstractmethod
from typing import Any, Optional
import asyncio
import random
import logging

from src.interfaces import Command


logger = logging.getLogger(__name__)


class Provider(ABC):
    @abstractmethod
    def parse(self, browser: Browser, *args, **kwargs) -> Any:
        pass


class AsyncProvider(ABC):
    @abstractmethod
    async def parse(self, *args, **kwargs) -> Any:
        pass

from pathlib import Path
from datetime import datetime

class AsyncTask(Command, ABC):
    """Абстрактный класс асинхронной задачи."""

    def __init__(self, max_attempts: int = 3, retry_delay_base: float = 10.0, screenshot_dir: str = "error_screenshots"):
        self.max_attempts = max_attempts
        self.retry_delay_base = retry_delay_base
        self.screenshot_dir = Path(screenshot_dir)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

    async def execute_with_retry(self, *args, **kwargs) -> Optional[Any]:
        """Выполнение задачи с повторными попытками."""
        for attempt in range(self.max_attempts):
            try:
                if attempt > 0:
                    delay = self.retry_delay_base * (2**attempt)
                    await asyncio.sleep(delay + random.uniform(0, 2))
                    logger.info(f"Retry attempt {attempt + 1}")

                return await self.execute(*args, **kwargs)

            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {e}")

                # --- снимаем скриншот, если есть доступ к странице ---
                page = kwargs.get("page")
                if page:
                    try:
                        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                        screenshot_path = self.screenshot_dir / f"task_error_{id(self)}_{ts}.png"
                        await page.screenshot(path=str(screenshot_path))
                        logger.error(f"Screenshot saved: {screenshot_path}")
                    except Exception as se:
                        logger.error(f"Failed to capture screenshot: {se}")

                if attempt == self.max_attempts - 1:
                    raise

        return None