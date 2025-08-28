
import logging
import os
from datetime import datetime, timedelta
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from ..db import requests
from .facts import get_next_short_fact, get_next_medium_fact
from .video_queue import pop_next_video

logger = logging.getLogger()
scheduler = AsyncIOScheduler(timezone='Europe/Moscow')


async def publish(bot: Bot, content_type: str):
    try:
        if content_type == 'short_fact':
            fact = get_next_short_fact()
            if fact:
                await bot.send_message(os.getenv("CHANNEL_ID"), fact)
        elif content_type == 'medium_fact':
            fact = get_next_medium_fact()
            if fact:
                await bot.send_message(os.getenv("CHANNEL_ID"), fact)
        elif content_type == 'video':
            video = pop_next_video()
            if video:
                await bot.send_video(os.getenv("CHANNEL_ID"), video["file_id"], caption=video["caption"])
            else:
                await bot.send_message(os.getenv("CHANNEL_ID"), "[!] Очередь видео пуста — публикация пропущена.")
    except Exception as e:
        logger.warning(f"[!] Ошибка при публикации {content_type}: {e}")


async def schedule_today(bot: Bot):
    weekday = datetime.now().strftime('%A').lower()  # monday, tuesday, ...
    slots = await requests.get_slots_for_day(weekday)
    for slot in slots:
        hour, minute = map(int, slot.time.split(":"))
        dt = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
        if dt < datetime.now():
            dt += timedelta(days=1)  # на завтра, если время уже прошло
        scheduler.add_job(publish, 'date', run_date=dt, args=[bot, slot.content_type])


def setup_scheduler(bot: Bot):
    scheduler.add_job(schedule_today, 'cron', hour=0, minute=0, args=[bot])
    scheduler.start()
