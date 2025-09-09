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

    def __init__(self, max_attempts: int = 3, retry_delay_base: float = 10.0):
        self.max_attempts = max_attempts
        self.retry_delay_base = retry_delay_base

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

                if attempt == self.max_attempts - 1:
                    raise

        return None