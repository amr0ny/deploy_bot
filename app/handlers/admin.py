import logging
import os

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from ..db import requests
from ..services import facts as fct
from ..services import video_queue

router = Router()
logger = logging.getLogger()


@router.message(Command("add_slot"))
async def cmd_add_slot(message: Message, command: CommandObject):
    try:
        day, time_str, type_str = command.args.split()
        valid_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        valid_types = ['short_fact', 'medium_fact', 'video']

        if day.lower() not in valid_days:
            await message.answer(
                "❌ Неверный день недели. Пример:\n"
                "/add_slot monday 12:00 short_fact\n"
                "Дни: monday, tuesday, ..., sunday"
            )
            return

        if type_str.lower() not in valid_types:
            await message.answer(
                "❌ Неверный тип. Пример:\n"
                "/add_slot monday 12:00 short_fact\n"
                "Типы: short_fact, medium_fact, video"
            )
            return

        await requests.add_publication_slot(day.lower(), time_str, type_str.lower())
        await message.answer(f"✅ Слот добавлен: {day} {time_str} {type_str}")
    except Exception:
        await message.answer(
            "❌ Неверный формат команды.\n"
            "Пример: /add_slot monday 12:00 short_fact"
        )


@router.message(Command("clear_slots"))
async def cmd_clear_slots(message: Message):
    await requests.clear_slots()
    await message.answer("✅ Все слоты публикаций удалены.")


@router.message(Command("slots"))
async def cmd_show_slots(message: Message):
    weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    response = ""
    for day in weekdays:
        slots = await requests.get_slots_for_day(day)
        if slots:
            response += f"📅 {day.capitalize()}\n"
            for s in sorted(slots, key=lambda x: x.time):
                response += f"🕒 {s.time} — {s.content_type}\n"
            response += "\n"
    if not response:
        response = "📭 Расписание пусто."
    await message.answer(response)


@router.message(Command('video_mode_start'))
async def cmd_video_mode_start(message: Message):
    video_queue.enable_video_mode()
    await message.answer("🎥 Режим сбора видео ВКЛЮЧЕН. Присылайте видео с подписью — они попадут в очередь.")


@router.message(Command('video_mode_stop'))
async def cmd_video_mode_stop(message: Message):
    video_queue.disable_video_mode()
    await message.answer("🛑 Режим сбора видео ОТКЛЮЧЕН. Видео больше не сохраняются.")


@router.message(Command('video_remaining'))
async def cmd_video_remaining(message: Message):
    count = video_queue.count_videos()
    await message.answer(f"📦 В очереди сейчас {count} видео.")


@router.message(Command("remaining"))
async def cmd_remaining(message: Message):
    facts = fct.count_remaining_facts()
    await message.answer(
        f"📊 Осталось фактов:\n"
        f"— Коротких: {facts['short']}\n"
        f"— Средних: {facts['medium']}"
    )


@router.message(Command("test_post"))
async def cmd_test_post(message: Message):
    short = fct.get_next_short_fact(False)
    medium = fct.get_next_medium_fact(False)
    video = video_queue.pop_next_video()

    if not short and not medium and not video:
        await message.answer("❌ Нет фактов и видео для тестовой публикации.")
        return

    await message.answer("📤 Отправляю тестовую публикацию в канал...")

    if short:
        await message.bot.send_message(os.getenv("CHANNEL_ID"), f"[test] {short}")
    if medium:
        await message.bot.send_message(os.getenv("CHANNEL_ID"), f"[test] {medium}")
    if video:
        await message.bot.send_video(os.getenv("CHANNEL_ID"), video["file_id"], caption=f"[test] {video['caption']}")


@router.message(Command("upload"))
async def cmd_upload(message: Message):
    if not message.document or not message.document.file_name.endswith('.txt'):
        await message.answer("❌ Пришлите .txt файл с фактами.")
        return



    if message.document.file_name not in ('medium_facts.txt', 'short_facts.txt'):
        await message.answer('❌ Файл должен называться "medium_facts.txt" или "short_facts.txt".')
        return

    await message.answer("⏳ Загружаю файл...")
    await fct.upload_file(message.bot, message.document.file_id, message.document.file_name)
    await message.answer(f"✅ Файл {message.document.file_name} загружен и заменён.")


@router.message(Command("video_clear"))
async def cmd_video_clear(message: Message):
    video_queue.clear_video_queue()
    await message.answer("🗑 Очередь видео полностью очищена.")


@router.message()
async def handle_video_submission(message: Message):
    if not video_queue.is_video_mode():
        return

    if message.video and message.caption:
        video_queue.add_video(message.video.file_id, message.caption)
        await message.answer("✅ Видео добавлено в очередь.")
