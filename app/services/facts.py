import os

from aiogram import Bot
from aiohttp import ClientSession

FACTS_DIR = 'facts'
SHORT_FACTS_FILE = os.path.join(FACTS_DIR, 'short_facts.txt')
MEDIUM_FACTS_FILE = os.path.join(FACTS_DIR, 'medium_facts.txt')


def _read_lines(filepath: str) -> list[str]:
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]


def _write_lines(filepath: str, lines: list[str]):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n\n'.join(lines) + '\n' if lines else '')


def get_next_short_fact(delete: bool | None = True):
    facts = _read_lines(SHORT_FACTS_FILE)
    if not facts:
        return None
    fact = facts[0]
    if delete:
        _write_lines(SHORT_FACTS_FILE, facts[1:])
    return fact


def get_next_medium_fact(delete: bool | None = True):
    content = open(MEDIUM_FACTS_FILE, 'r', encoding='utf-8').read().strip()
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
    if not paragraphs:
        return None
    fact = paragraphs[0]
    if delete:
        _write_lines(MEDIUM_FACTS_FILE, paragraphs[1:])
    return fact


def count_remaining_facts():
    short = len(_read_lines(SHORT_FACTS_FILE))
    medium = len([p for p in open(MEDIUM_FACTS_FILE, 'r', encoding='utf-8').read().split('\n\n') if p.strip()])
    return {'short': short, 'medium': medium}



async def upload_file(bot: Bot, file_id: str, filename: str) -> str:
    os.makedirs(FACTS_DIR, exist_ok=True)
    path = os.path.join(FACTS_DIR, filename)

    file_info = await bot.get_file(file_id)
    file_path = file_info.file_path

    async with ClientSession() as session:
        async with session.get(f'https://api.telegram.org/file/bot{bot.token}/{file_path}') as resp:
            content = await resp.read()

    with open(path, 'wb') as f:
        f.write(content)

    return path