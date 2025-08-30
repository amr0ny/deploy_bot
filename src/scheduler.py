import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio.session import AsyncSession, async_sessionmaker

from src.facts import get_next_short_fact, get_next_medium_fact
from src.provider.factories import TaskBrowserFactory
from src.provider.manager import AsyncProviderManager
from src.queues.interfaces import AsyncQueue
from src.repository.publication_slot import PublicationSlotRepository

logger = logging.getLogger()
scheduler = AsyncIOScheduler(timezone="Europe/Moscow")


async def publish(
    bot: Bot,
    channel_id: str,
    queue: AsyncQueue,
    manager: AsyncProviderManager,
    task_browser_factory: TaskBrowserFactory,
    content_type: str,
):
    try:
        if content_type == "short_fact":
            fact = get_next_short_fact()
            if fact:
                await bot.send_message(channel_id, fact)
        elif content_type == "medium_fact":
            fact = get_next_medium_fact()
            if fact:
                await bot.send_message(channel_id, fact)
        elif content_type == "video":
            try:
                task = await queue.get(timeout=10)
                await task.execute(bot, manager, task_browser_factory, channel_id)
            except asyncio.TimeoutError:
                await bot.send_message(
                    channel_id,
                    "[!] Очередь видео пуста — публикация пропущена.",
                )
    except Exception as e:
        logger.warning(f"[!] Ошибка при публикации {content_type}: {e}")


async def schedule_today(
    bot: Bot,
    db_session: AsyncSession,
    queue: AsyncQueue,
    manager: AsyncProviderManager,
    task_browser_factory: TaskBrowserFactory,
    channel_id: str
):
    weekday = datetime.now().strftime("%A").lower()  # monday, tuesday, ...
    slots = await PublicationSlotRepository.get_slots_for_day(db_session, weekday)
    for slot in slots:
        hour, minute = map(int, slot.time.split(":"))
        dt = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
        if dt < datetime.now():
            dt += timedelta(days=1)
        scheduler.add_job(
            publish,
            "date",
            run_date=dt,
            args=[bot, channel_id, queue, manager, task_browser_factory, slot.content_type],
        )


async def setup_scheduler(
    bot: Bot,
    session_maker: async_sessionmaker,
    queue: AsyncQueue,
    manager: AsyncProviderManager,
    task_browser_factory: TaskBrowserFactory,
    channel_id: str
):
    async with session_maker() as db_session:
        scheduler.add_job(
            schedule_today,
            "cron",
            hour=14,
            minute=00,
            args=[bot, db_session, queue, manager, task_browser_factory, channel_id],
        )
        scheduler.start()
