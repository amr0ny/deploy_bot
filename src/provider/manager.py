import time
from pathlib import Path

from src.provider.models import BrowserConfig
from datetime import datetime
from typing import Optional, List, Any, Dict, AsyncGenerator
import asyncio
from playwright.async_api import async_playwright, Browser
import logging

from src.browser.stealth import StealthBrowser
from src.provider.interfaces import AsyncTask, AsyncProvider

logger = logging.getLogger(__name__)


class TaskManager:
    """Менеджер для управления и выполнения задач с расширенной функциональностью."""

    def __init__(self, max_parallel: int = 3, screenshot_dir: str = "error_screenshots"):
        self.max_parallel = max_parallel
        self.semaphore = asyncio.Semaphore(max_parallel)
        self.active_tasks = {}  # task_id -> task_info
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.lock = asyncio.Lock()  # Для thread-safe операций
        self._stop_requested = False
        self.screenshot_dir = Path(screenshot_dir)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

    async def execute_task(self, task: AsyncTask, **dependencies) -> Any:
        """Выполнение задачи с ограничением параллелизма и мониторингом."""
        if self._stop_requested:
            raise RuntimeError("Task execution stopped")

        async with self.semaphore:
            task_id = id(task)
            task_info = {
                "task": task,
                "start_time": datetime.now(),
                "status": "running",
            }

            async with self.lock:
                self.active_tasks[task_id] = task_info

            try:
                result = await task.execute_with_retry(**dependencies)

                async with self.lock:
                    task_info["status"] = "completed"
                    task_info["end_time"] = datetime.now()
                    task_info["result"] = result
                    self.completed_tasks += 1

                logger.info(f"Task {task_id} completed successfully")
                return result

            except Exception as e:
                page = dependencies.get("page")
                if page:
                    try:
                        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                        screenshot_path = self.screenshot_dir / f"task_error_{id(self)}_{ts}.png"
                        await page.screenshot(path=str(screenshot_path))
                        logger.error(f"Screenshot saved: {screenshot_path}")
                    except Exception as se:
                        logger.error(f"Failed to capture screenshot: {se}")

                async with self.lock:
                    task_info["status"] = "failed"
                    task_info["end_time"] = datetime.now()
                    task_info["error"] = str(e)
                    self.failed_tasks += 1

                logger.error(f"Task {task_id} failed: {e}")
                raise

            finally:
                async with self.lock:
                    self.active_tasks.pop(task_id, None)

    async def execute_many(self, tasks: List[AsyncTask], **dependencies) -> List[Any]:
        """Параллельное выполнение множества задач с обработкой результатов."""
        task_coroutines = [self.execute_task(task, **dependencies) for task in tasks]

        results = []
        for future in asyncio.as_completed(task_coroutines):
            try:
                result = await future
                results.append(result)
            except Exception as e:
                results.append(e)  # или можно использовать None/специальный объект

        return results

    async def execute_with_timeout(
        self, task: AsyncTask, timeout: float, **dependencies
    ) -> Any:
        """Выполнение задачи с таймаутом."""
        try:
            return await asyncio.wait_for(
                self.execute_task(task, **dependencies), timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"Task {id(task)} timed out after {timeout} seconds")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики выполнения задач."""
        return {
            "max_parallel": self.max_parallel,
            "active_tasks": len(self.active_tasks),
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "total_tasks": self.completed_tasks + self.failed_tasks,
            "success_rate": (
                self.completed_tasks / (self.completed_tasks + self.failed_tasks)
            )
            if (self.completed_tasks + self.failed_tasks) > 0
            else 0,
        }

    def get_active_tasks_info(self) -> List[Dict]:
        """Информация о активных задачах."""
        return [
            {
                "task_id": task_id,
                "task_type": type(info["task"]).__name__,
                "start_time": info["start_time"],
                "duration": (datetime.now() - info["start_time"]).total_seconds(),
            }
            for task_id, info in self.active_tasks.items()
        ]

    async def stop(self):
        """Запрос остановки выполнения задач."""
        self._stop_requested = True

    async def wait_for_completion(self, timeout: Optional[float] = None):
        """Ожидание завершения всех активных задач."""
        start_time = time.time()
        while self.active_tasks:
            if timeout and (time.time() - start_time) > timeout:
                raise TimeoutError("Timeout waiting for task completion")
            await asyncio.sleep(0.1)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.wait_for_completion(timeout=30.0)  # Ждем завершения задач


class AsyncProviderManager:
    """Менеджер для асинхронной обработки задач с провайдерами."""

    def __init__(
        self,
        provider: AsyncProvider,
        task_manager: TaskManager,
        browser_config: BrowserConfig = BrowserConfig(),
        max_parallel_tasks: int = 3,
    ):
        self.provider = provider
        self.browser_config = browser_config
        self.max_parallel_tasks = max_parallel_tasks
        self.fingerprint = self._generate_fingerprint()
        self.task_manager = task_manager
        self.browser = None
        self.playwright = None
        self._is_running = False

    def _generate_fingerprint(self) -> dict:
        """Генерация fingerprint для браузера."""
        return StealthBrowser.get_random_fingerprint()

    def _get_browser_args(self) -> List[str]:
        """Генерирует аргументы для запуска браузера."""
        config = self.browser_config
        args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox" if config.no_sandbox else "",
            "--disable-web-security" if config.disable_web_security else "",
            "--disable-dev-shm-usage" if config.disable_dev_shm else "",
            "--disable-gpu" if config.disable_gpu else "",
            f"--window-size={config.window_width},{config.window_height}",
            "--enable-webgl" if config.enable_webgl else "",
            "--hide-scrollbars" if config.hide_scrollbars else "",
            "--mute-audio" if config.mute_audio else "",
            f"--user-agent={self.fingerprint['user_agent']}",
        ]
        return [arg for arg in args if arg]

    async def _launch_browser(self) -> Browser:
        """Запуск браузера с настройками."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.browser_config.headless, args=self._get_browser_args()
        )
        return self.browser

    async def _get_dependencies(self) -> Dict[str, Any]:
        """Возвращает зависимости для задач."""
        if not self.browser:
            await self._launch_browser()

        return {
            "browser": self.browser,
            "provider": self.provider,
            "fingerprint": self.fingerprint,
            "browser_config": self.browser_config,
        }

    async def process_task(self, task: AsyncTask, timeout: Optional[float]) -> Any:
        """Обработка одной задачи."""
        if not self._is_running:
            await self.start()

        dependencies = await self._get_dependencies()

        if timeout:
            return await self.task_manager.execute_with_timeout(
                task, timeout, **dependencies
            )
        else:
            return await self.task_manager.execute_task(task, **dependencies)

    async def process_batch(
        self, tasks: List[AsyncTask], timeout: Optional[float]
    ) -> List[Any]:
        """Пакетная обработка задач."""
        if not self._is_running:
            await self.start()

        dependencies = await self._get_dependencies()
        results = []

        for task in tasks:
            try:
                if timeout:
                    result = await self.task_manager.execute_with_timeout(
                        task, timeout, **dependencies
                    )
                else:
                    result = await self.task_manager.execute_task(task, **dependencies)
                results.append(result)
            except Exception as e:
                results.append(e)
                logger.error(f"Task failed: {e}")

        return results

    async def process_stream(
        self,
        task_stream: AsyncGenerator[AsyncTask, None],
        timeout: Optional[float],
        max_tasks: Optional[int] = None,
    ) -> AsyncGenerator[Any, None]:
        """Обработка потока задач."""
        if not self._is_running:
            await self.start()

        dependencies = await self._get_dependencies()
        processed_count = 0

        async for task in task_stream:
            if max_tasks and processed_count >= max_tasks:
                break

            try:
                if timeout:
                    result = await self.task_manager.execute_with_timeout(
                        task, timeout, **dependencies
                    )
                else:
                    result = await self.task_manager.execute_task(task, **dependencies)

                yield result
                processed_count += 1

            except Exception as e:
                logger.error(f"Stream task failed: {e}")
                yield e

    async def start(self):
        """Запуск менеджера."""
        if self._is_running:
            return

        await self._launch_browser()
        self._is_running = True
        logger.info("AsyncProviderManager started")

    async def stop(self):
        """Остановка менеджера."""
        if not self._is_running:
            return

        # Останавливаем TaskManager
        await self.task_manager.stop()
        await self.task_manager.wait_for_completion(timeout=30.0)

        # Закрываем браузер
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

        self._is_running = False
        logger.info("AsyncProviderManager stopped")

    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики."""
        task_stats = self.task_manager.get_stats()
        return {
            **task_stats,
            "is_running": self._is_running,
            "max_parallel_tasks": self.max_parallel_tasks,
            "browser_configured": self.browser is not None,
        }

    async def health_check(self) -> bool:
        """Проверка работоспособности."""
        if not self._is_running or not self.browser:
            return False

        try:
            # Простая проверка что браузер responsive
            context = await self.browser.new_context()
            await context.close()
            return True
        except Exception:
            return False

    async def restart(self):
        """Перезапуск менеджера."""
        await self.stop()
        await self.start()

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
