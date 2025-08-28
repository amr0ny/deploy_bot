import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from dotenv import load_dotenv

load_dotenv()

from app.db.models import create_tables
from app.handlers import __all_routers__
from app.services.scheduler import setup_scheduler

bot = Bot(os.getenv('BOT_TOKEN'))


async def main():
    dp = Dispatcher()
    dp.include_routers(*__all_routers__)

    await bot.delete_webhook()
    await bot.set_my_commands([
        BotCommand(command='add_slot', description='Добавить слот публикации (день время тип)'),
        BotCommand(command='clear_slots', description='Удалить все слоты публикации'),
        BotCommand(command='slots', description='Показать текущее расписание'),
        BotCommand(command='video_mode_start', description='Включить режим сбора видео'),
        BotCommand(command='video_mode_stop', description='Выключить режим сбора видео'),
        BotCommand(command='video_remaining', description='Сколько видео в очереди'),
        BotCommand(command='upload', description='Загрузить файл с фактами (.txt)'),
        BotCommand(command='test_post', description='Отправить тестовый факт в канал'),
        BotCommand(command='remaining', description='Сколько фактов осталось'),
        BotCommand(command='video_clear', description='Очистить очередь видео'),
    ])

    await create_tables()
    setup_scheduler(bot)
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        logging.basicConfig(level=logging.INFO)
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
