from src.provider.interfaces import AsyncProvider
from typing import Optional
from playwright.async_api import Page
import logging
from src.provider.models import TimeoutConfig
from playwright.async_api import TimeoutError

logger = logging.getLogger(__name__)


class AsyncSnaptikProvider(AsyncProvider):
    def __init__(
        self,
        timeouts: TimeoutConfig = TimeoutConfig(),
        stealth_settings: Optional[dict] = None,
    ):
        self.url = "https://snaptik.app/"
        self.timeouts = timeouts
        self.stealth_settings = stealth_settings or {}

    async def parse(self, page: Page, *args, **kwargs) -> Optional[str]:
        """Асинхронный метод парсинга видео."""
        url = kwargs.get("url")
        if not url:
            logger.warning("No URL provided for parsing")
            return None

        try:
            # Теперь работаем только с page, browser не нужен
            return await self._parse_page(page, url)

        except Exception:
            return None

    async def _continue_web(self, page: Page) -> bool:
        """Асинхронная обработка всплывающего окна."""
        try:
            button = await page.wait_for_selector(
                "button.button.continue-web",
                timeout=self.timeouts.wait_for_continue_button
            )
            if button:
                await button.click(timeout=self.timeouts.continue_button)
        except TimeoutError:
            # Кнопка не появилась — это не ошибка
            logger.debug("Continue button not found, skipping")
        except Exception as e:
            # Любая другая ошибка — логируем, но продолжаем
            logger.warning(f"Continue button error: {e}")
        return True

    async def _parse_page(self, page: Page, video_url: str) -> Optional[str]:
        """Асинхронная логика парсинга страницы."""
        try:
            # Навигация с ожиданием
            await page.goto(
                self.url, timeout=self.timeouts.page_load, wait_until="domcontentloaded"
            )

            # Обработка всплывающего окна
            if not await self._continue_web(page):
                return None

            # Ожидание и заполнение формы
            form = await page.wait_for_selector(
                'form.form[name="formurl"]', timeout=self.timeouts.form_selector
            )

            input_field = await form.wait_for_selector('input[name="url"]')
            await input_field.fill(video_url)

            # Отправка формы
            submit_button = await form.wait_for_selector('button[type="submit"]')
            await submit_button.click()

            # Ожидание результатов
            await page.wait_for_selector(
                "div.video-links, div.error-message", timeout=self.timeouts.result_load
            )

            # Поиск ссылок для скачивания
            links = await page.query_selector_all("div.video-links a")
            if links:
                first_link = links[0]
                return await first_link.get_attribute("href")

            raise Exception("No download links found")

        except Exception as e:
            logger.error(f"Parsing failed: {e}")
            raise
