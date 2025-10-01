import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.fsm.storage.memory import MemoryStorage

from sqlalchemy.ext.asyncio.engine import create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio.session import AsyncSession

from src.config import AppConfig
from src.middlewares import AdminOnlyMiddleware, DependencyMiddleware, DbMiddleware
from src.models import create_tables
from src.handlers import router
from src.provider.factories import AsyncTaskFactory
from src.provider.manager import AsyncBrowserProviderManager, TaskManager, AsyncProviderManager
from src.provider.models import TimeoutConfig, BrowserConfig
from src.provider.providers import AsyncYtDlpProvider
from src.queues.factories import QueueFactory, QueueType, TaskFactory
from src.repository.facts import FactRepository
from src.repository.proxy import ProxyRepository

from src.scheduler import setup_scheduler


async def get_db_session(session_maker: async_sessionmaker) -> AsyncSession:
    async with session_maker() as session:
        yield session


async def main():
    config = AppConfig()

    dp = Dispatcher(storage=MemoryStorage())
    bot = Bot(config.bot_token)

    engine = create_async_engine(config.database_url)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    timeout_config = TimeoutConfig()
    browser_config = BrowserConfig()
    task_browser_manager = TaskManager()
    proxy_repository = ProxyRepository(session_maker)
    fact_repository = FactRepository(session_maker)
    yt_dlp_provider = AsyncYtDlpProvider()
    manager = AsyncProviderManager(
        provider=yt_dlp_provider,
        task_manager=task_browser_manager,
    )

    task_queue = QueueFactory.create(
        QueueType.REDIS, queue_name=config.queue_name, redis_url=config.redis_url
    )

    task_factory = TaskFactory()
    async_task_factory = AsyncTaskFactory()

    admin_middleware = AdminOnlyMiddleware(config.admin_ids)
    db_middleware = DbMiddleware("db_session", session_maker)
    proxy_repository_middleware = DependencyMiddleware("proxy_repository", proxy_repository)
    fact_repository_middleware = DependencyMiddleware("fact_repository", fact_repository)
    queue_middleware = DependencyMiddleware("queue", task_queue)
    task_factory_middleware = DependencyMiddleware("task_factory", task_factory)
    manager_middleware = DependencyMiddleware("manager", manager)
    task_browser_factory_middleware = DependencyMiddleware(
        "task_browser_factory", async_task_factory
    )
    config_middleware = DependencyMiddleware("config", config)

    router.message.middleware(admin_middleware)
    dp.update.outer_middleware(db_middleware)
    dp.update.outer_middleware(proxy_repository_middleware)
    dp.update.outer_middleware(fact_repository_middleware)
    dp.update.outer_middleware(queue_middleware)
    dp.update.outer_middleware(task_factory_middleware)
    dp.update.outer_middleware(manager_middleware)
    dp.update.outer_middleware(task_browser_factory_middleware)
    dp.update.outer_middleware(config_middleware)

    dp.include_routers(router)

    await bot.delete_webhook()
    await bot.set_my_commands(
        [
            BotCommand(
                command="add_slot",
                description="Добавить слот публикации (день время тип)",
            ),
            BotCommand(
                command="clear_slots", description="Удалить все слоты публикации"
            ),
            BotCommand(command="slots", description="Показать текущее расписание"),
            BotCommand(
                command="video_mode_start", description="Включить режим сбора видео"
            ),
            BotCommand(
                command="video_mode_stop", description="Выключить режим сбора видео"
            ),
            BotCommand(
                command="video_remaining", description="Сколько видео в очереди"
            ),
            BotCommand(command="upload", description="Загрузить файл с фактами (.txt)"),
            BotCommand(
                command="test_post", description="Отправить тестовый факт в канал"
            ),
            BotCommand(command="remaining", description="Сколько фактов осталось"),
            BotCommand(command="video_clear", description="Очистить очередь видео"),
        ]
    )

    await create_tables(engine)
    await setup_scheduler(
        bot, session_maker, fact_repository, task_queue, manager, async_task_factory, task_factory, config.channel_id
    )
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        logging.basicConfig(level=logging.INFO)
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
