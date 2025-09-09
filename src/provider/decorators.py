import functools
import logging
from datetime import datetime
from playwright.sync_api import Page  # если у тебя async_api, то Page оттуда

logger = logging.getLogger(__name__)


def screenshot_on_exception(func):
    @functools.wraps(func)
    async def wrapper(self, page: Page, *args, **kwargs):
        try:
            return await func(self, page, *args, **kwargs)
        except Exception as e:
            try:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = self.screenshot_dir / f"task_error_{id(self)}_{ts}.png"
                await page.screenshot(path=str(screenshot_path))
                logger.error(f"Screenshot saved: {screenshot_path}")
            except Exception as se:
                logger.error(f"Failed to capture screenshot: {se}")
            # пробрасываем исключение дальше (чтобы логика не терялась)
            raise e

    return wrapper
