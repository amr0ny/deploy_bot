import asyncio
import logging
import random
from typing import Tuple

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy.ext.asyncio.session import AsyncSession
from repository.publication_slot import PublicationSlotRepository

from src import facts as fct
from src.config import AppConfig
from src.models import FactType
from src.provider.factories import AsyncTaskFactory
from src.provider.manager import AsyncBrowserProviderManager, AsyncProviderManager
from src.provider.providers import AsyncYtDlpProvider
from src.queues.factories import TaskFactory, TaskType
from src.queues.interfaces import AsyncQueue
from src.repository.facts import FactRepository
from src.repository.proxy import ProxyRepository
from src.utils import extract_tiktok_links, parse_proxy

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


@router.message(Command("remaining_video_count"))
async def cmd_video_remaining(message: Message, queue: AsyncQueue):
    count = await queue.size()
    await message.answer(f"📦 В очереди сейчас {count} видео.")


@router.message(Command("remaining_facts_count"))
async def cmd_remaining_facts_count(message: Message, fact_repository: FactRepository):
    short_facts_count = await fact_repository.get_facts_count(FactType.SHORT)
    medium_facts_count = await fact_repository.get_facts_count(FactType.MEDIUM)
    await message.answer(
        f"📊 Осталось фактов:\n"
        f"— Коротких: {short_facts_count}\n"
        f"— Средних: {medium_facts_count}"
    )

@router.message(Command("remove_all_facts"))
async def cmd_remove_all_facts(message: Message, fact_repository: FactRepository):
    command_parts = message.caption.split()
    if len(command_parts) != 2:
        await message.answer("❌ Использование: /upload short или /upload medium")
        return

    fact_type = command_parts[1].lower()
    if fact_type not in ("short", "medium"):
        await message.answer("❌ Тип должен быть: short или medium")
        return


    await fact_repository.remove_all_facts(FactType(fact_type))
    await message.answer("Факты успешно удалены")

@router.message(Command("test_post"))
async def cmd_test_post(
    message: Message,
    queue: AsyncQueue,
    manager: AsyncProviderManager,
    task_browser_factory: AsyncTaskFactory,
    task_factory: TaskFactory,
    fact_repository: FactRepository,
    config: AppConfig,
):
    try:
        task_dict = await queue.get(timeout=10)
        task = task_factory.create(TaskType.LINK, url=task_dict.get("url"))
    except asyncio.TimeoutError:
        await message.answer("Видео в очереди не найдено")
        return

    short = await fact_repository.get_next_fact(FactType.SHORT)
    medium = await fact_repository.get_next_fact(FactType.MEDIUM)
    await message.answer("📤 Отправляю тестовую публикацию в канал...")
    if short:
        await message.bot.send_message(config.channel_id, f"[test] {short}")
    if medium:
        await message.bot.send_message(config.channel_id, f"[test] {medium}")

    await task.execute(message.bot, manager, task_browser_factory, config.channel_id)


@router.message(Command("upload"))
async def cmd_upload(message: Message, fact_repository: FactRepository):
    # Парсим команду: /upload short или /upload medium
    command_parts = message.caption.split()
    if len(command_parts) != 2:
        await message.answer("❌ Использование: /upload short или /upload medium")
        return

    fact_type = command_parts[1].lower()
    if fact_type not in ("short", "medium"):
        await message.answer("❌ Тип должен быть: short или medium")
        return
    fact_type = FactType(fact_type)
    if not message.document or not message.document.file_name.endswith(".txt"):
        await message.answer("❌ Пришлите .txt файл с фактами.")
        return

    await message.answer("⏳ Загружаю файл...")

    try:
        # Скачиваем файл
        file = await message.bot.get_file(message.document.file_id)
        file_content = await message.bot.download_file(file.file_path)

        # Декодируем и разбиваем на строки
        text = file_content.read().decode('utf-8')
        facts = [line.strip() for line in text.split('\n') if line.strip()]

        if not facts:
            await message.answer("❌ Файл пуст или не содержит фактов.")
            return

        await message.answer(f"⏳ Обрабатываю {len(facts)} фактов...")

        batch_size = 100
        for i in range(0, len(facts), batch_size):
            batch = facts[i:i + batch_size]
            await fact_repository.add_facts_batch(batch, fact_type)

            if i + batch_size < len(facts):
                await message.answer(f"⏳ Обработано {min(i + batch_size, len(facts))}/{len(facts)} фактов...")

        await message.answer(f"✅ Успешно добавлено {len(facts)} {fact_type} фактов в базу!")

    except Exception as e:
        logger.error(f"Ошибка при загрузке файла: {e}")
        await message.answer("❌ Произошла ошибка при обработке файла.")


@router.message(Command("video_clear"))
async def cmd_video_clear(message: Message, queue: AsyncQueue):
    await queue.clear()
    await message.answer("🗑 Очередь видео полностью очищена.")


@router.message(Command("add_proxy"))
async def add_proxy(message: Message, proxy_repository: ProxyRepository):
    try:
        proxy_str = message.caption or message.text or ""
        if proxy_str.startswith("/add_proxy"):
            proxy_str = proxy_str[len("/add_proxy"):].strip()  # убираем команду

        server, username, password = parse_proxy(proxy_str)

        if not server:
            await message.answer(
                "Некорректный формат прокси.\nПример: http://user:pass@host:port"
            )
            return

        await proxy_repository.add_proxy(server, username, password)
        await message.answer(f"Прокси {server} успешно добавлен!")

    except Exception as e:
        await message.answer(f"Ошибка при добавлении прокси: {e}")


@router.message(Command("remove_proxy"))
async def remove_proxy(message: Message, proxy_repository: ProxyRepository):
    try:
        msg = message.caption or message.text or ""

        if msg.startswith("/remove_proxy"):
            proxy_id_str = msg[len("/remove_proxy"):].strip()

        if proxy_id_str.isdigit():
            proxy_id = int(proxy_id_str)
        else:
            await message.answer("Нужно указать число (ID прокси)")
            return
        await proxy_repository.remove_proxy(proxy_id)

        await message.answer(f"Прокси c id {proxy_id} успешно удален!")

    except Exception as e:
        await message.answer(f"Ошибка при удалении прокси: {e}")


@router.message(Command("remove_all_proxies"))
async def remove_all_proxies(message: Message, proxy_repository: ProxyRepository):
    try:
        await proxy_repository.remove_all_proxies()
        await message.answer("Все прокси успешно удалены")
    except Exception as e:
        await message.answer(f"Ошибка при удалении прокси: {e}")

@router.message(Command("proxy_list"))
async def proxy_list(message: Message, proxy_repository: ProxyRepository):
    try:
        res = ""
        proxy_list = await proxy_repository.get_proxies()
        if len(proxy_list) <= 0:
            await message.answer("Список прокси пуст")
            return
        for proxy in proxy_list:
            res += str(proxy) + "\n"

        await message.answer(res)
    except Exception as e:
        await message.answer(f"Ошибка при получении списка прокси: {e}")


@router.message()
async def handle_video_submission(
    message: Message, queue: AsyncQueue
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

    links = list(tiktok_links)
    random.shuffle(links)

    for link in tiktok_links:
        try:
            await queue.put(
                {"url": link}
            )
            logger.info(f"TikTok link added to queue: {link}")

        except Exception as e:
            logger.error(f"Failed to add TikTok task: {e}")
            await message.answer("❌ Ошибка при добавлении TikTok ссылки.")

    await message.answer(f"✅ Добавлено {len(tiktok_links)} TikTok ссылок в очередь.")
