import re
from typing import List
from urllib.parse import urlparse
import base64
import json
import urllib.parse


def extract_mp4_url(rapid_url: str) -> str:
    """
    Принимает rapidcdn.app/v2 ссылку и возвращает настоящий mp4-URL.
    """
    # Достаём token из query string
    query = urllib.parse.urlparse(rapid_url).query
    params = urllib.parse.parse_qs(query)
    token = params.get("token", [None])[0]
    if not token:
        raise ValueError("В ссылке нет параметра token")

    # JWT = header.payload.signature -> берём payload
    parts = token.split(".")
    if len(parts) < 2:
        raise ValueError("Некорректный формат JWT токена")
    payload_b64 = parts[1]

    # Добавляем padding, если не кратно 4
    payload_b64 += "=" * (-len(payload_b64) % 4)

    # Декодируем JSON
    payload = json.loads(base64.urlsafe_b64decode(payload_b64))

    # Внутри "url" лежит ссылка на mp4
    return payload.get("url")


def extract_tiktok_links(text: str) -> List[str]:
    """Извлекает TikTok ссылки из текста."""
    # Регулярное выражение для TikTok ссылок
    tiktok_pattern = r"https?://(?:www\.)?tiktok\.com/[^?\s]+|https?://vm\.tiktok\.com/[^?\s]+|https?://vt\.tiktok\.com/[^?\s]+"
    matches = re.findall(tiktok_pattern, text, re.IGNORECASE)

    # Валидация и нормализация ссылок
    valid_links = []
    for link in matches:
        try:
            parsed = urlparse(link)
            if parsed.netloc in [
                "tiktok.com",
                "www.tiktok.com",
                "vm.tiktok.com",
                "vt.tiktok.com",
            ]:
                valid_links.append(link)
        except:
            continue

    return valid_links
