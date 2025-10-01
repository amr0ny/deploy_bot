from enum import Enum
from typing import Any

from src.provider.interfaces import AsyncTask, AsyncProvider, AsyncBrowserProvider
from src.provider.models import BrowserConfig


class AsyncTaskType(Enum):
    BROWSER_VIDEO = "video_browser"
    VIDEO = "video"


class AsyncTaskBrowserVideo(AsyncTask):
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
        provider: AsyncBrowserProvider,
        fingerprint: dict,
        browser_config: BrowserConfig,
        **kwargs,
    ) -> Any:
        """Выполнение задачи скачивания видео."""
        context = await browser.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 ...")

        async with context:
            page = await context.new_page()
            result = await provider.parse(page, url=self.url)
            return result


class AsyncTaskVideo(AsyncTask):
    def __init__(self, url: str, download=True, **kwargs):
        super().__init__(**kwargs)
        self.url = url
        self.download = download

    async def execute(
        self,
        provider: AsyncProvider,
        **kwargs
    ) -> Any:
        return await provider.retrieve(self.url, self.download)

