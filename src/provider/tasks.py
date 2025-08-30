from enum import Enum
from typing import Any

from src.provider.interfaces import AsyncTask
from src.provider.models import BrowserConfig


class TaskBrowserType(Enum):
    VIDEO = "video"


class TaskBrowserVideo(AsyncTask):
    """Задача обработки одного видео."""

    def __init__(
        self,
        url: str,
        min_delay: float = 5.0,
        max_delay: float = 15.0,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.url = url
        self.min_delay = min_delay
        self.max_delay = max_delay

    async def execute(
        self,
        browser,
        provider,
        fingerprint: dict,
        browser_config: BrowserConfig,
        **kwargs,
    ) -> Any:
        """Выполнение задачи скачивания видео."""
        context = await browser.new_context(user_agent=fingerprint["user_agent"])

        async with context:
            page = await context.new_page()
            result = await provider.parse(page, url=self.url)
            return result
