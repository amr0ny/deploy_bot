import asyncio
import logging

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy.ext.asyncio.session import AsyncSession
from repository.publication_slot import PublicationSlotRepository

from src import facts as fct
from src.config import AppConfig
from src.provider.factories import TaskBrowserFactory
from src.provider.manager import AsyncProviderManager
from src.queues.factories import TaskFactory, TaskType
from src.queues.interfaces import AsyncQueue
from src.utils import extract_tiktok_links

router = Router()
logger = logging.getLogger()


@router.message(Command("add_slot"))
async def cmd_add_slot(
    message: Message, db_session: AsyncSession, command: CommandObject
):
    try:
        day, time_str, type_str = command.args.split()
        valid_days = [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]
        valid_types = ["short_fact", "medium_fact", "video"]

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

        await PublicationSlotRepository.add_publication_slot(
            db_session, day.lower(), time_str, type_str.lower()
        )
        await message.answer(f"✅ Слот добавлен: {day} {time_str} {type_str}")
    except Exception:
        await message.answer(
            "❌ Неверный формат команды.\nПример: /add_slot monday 12:00 short_fact"
        )


@router.message(Command("clear_slots"))
async def cmd_clear_slots(message: Message, db_session: AsyncSession):
    await PublicationSlotRepository.clear_slots(db_session)
    await message.answer("✅ Все слоты публикаций удалены.")


@router.message(Command("slots"))
async def cmd_show_slots(message: Message, db_session: AsyncSession):
    weekdays = [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]
    response = ""
    for day in weekdays:
        slots = await PublicationSlotRepository.get_slots_for_day(db_session, day)
        if slots:
            response += f"📅 {day.capitalize()}\n"
            for s in sorted(slots, key=lambda x: x.time):
                response += f"🕒 {s.time} — {s.content_type}\n"
            response += "\n"
    if not response:
        response = "📭 Расписание пусто."
    await message.answer(response)


@router.message(Command("video_mode_start"))
async def cmd_video_mode_start(message: Message, queue: AsyncQueue):
    await queue.set_flag(True)
    await message.answer(
        "🎥 Режим сбора видео ВКЛЮЧЕН. Присылайте видео с подписью — они попадут в очередь."
    )


@router.message(Command("video_mode_stop"))
async def cmd_video_mode_stop(message: Message, queue: AsyncQueue):
    await queue.set_flag(False)
    await message.answer("🛑 Режим сбора видео ОТКЛЮЧЕН. Видео больше не сохраняются.")


@router.message(Command("video_remaining"))
async def cmd_video_remaining(message: Message, queue: AsyncQueue):
    count = await queue.size()
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
async def cmd_test_post(
    message: Message,
    queue: AsyncQueue,
    manager: AsyncProviderManager,
    task_browser_factory: TaskBrowserFactory,
    config: AppConfig
):
    try:
        task = await queue.get(timeout=10)
    except asyncio.TimeoutError:
        await message.answer("Видео в очереди не найдено")
        return

    short = fct.get_next_short_fact(False)
    medium = fct.get_next_medium_fact(False)
    await message.answer("📤 Отправляю тестовую публикацию в канал...")
    if short:
        await message.bot.send_message(config.channel_id, f"[test] {short}")
    if medium:
        await message.bot.send_message(config.channel_id, f"[test] {medium}")

    await task.execute(message.bot, manager, task_browser_factory, config.channel_id)


@router.message(Command("upload"))
async def cmd_upload(message: Message):
    if not message.document or not message.document.file_name.endswith(".txt"):
        await message.answer("❌ Пришлите .txt файл с фактами.")
        return

    if message.document.file_name not in ("medium_facts.txt", "short_facts.txt"):
        await message.answer(
            '❌ Файл должен называться "medium_facts.txt" или "short_facts.txt".'
        )
        return

    await message.answer("⏳ Загружаю файл...")
    await fct.upload_file(
        message.bot, message.document.file_id, message.document.file_name
    )
    await message.answer(f"✅ Файл {message.document.file_name} загружен и заменён.")


@router.message(Command("video_clear"))
async def cmd_video_clear(message: Message, queue: AsyncQueue):
    await queue.clear()
    await message.answer("🗑 Очередь видео полностью очищена.")


@router.message()
async def handle_video_submission(
    message: Message, queue: AsyncQueue, task_factory: TaskFactory
):
    if not await queue.get_flag():
        return

    tiktok_links = []
    caption = message.caption or ""

    if caption:
        tiktok_links = extract_tiktok_links(caption)

    if not tiktok_links and message.text:
        tiktok_links = extract_tiktok_links(message.text)

    if not tiktok_links:
        await message.answer(
            "📝 Отправьте видео с подписью или TikTok ссылку.\n\n"
            "Поддерживаемые форматы:\n"
            "• https://tiktok.com/@user/video/123456789\n"
            "• https://vm.tiktok.com/ABCD1234/\n"
            "• https://vt.tiktok.com/XYZ9876/"
        )
    for link in tiktok_links:
        try:
            await queue.put(
                task_factory.create(TaskType.LINK, url=link, caption=caption)
            )
            logger.info(f"TikTok link added to queue: {link}")

        except Exception as e:
            logger.error(f"Failed to add TikTok task: {e}")
            await message.answer("❌ Ошибка при добавлении TikTok ссылки.")

    await message.answer(f"✅ Добавлено {len(tiktok_links)} TikTok ссылок в очередь.")
