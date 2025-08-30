from typing import List

from pydantic_settings import BaseSettings


class AppConfig(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///database.sqlite3"
    channel_id: str
    bot_token: str
    debug: bool = False
    queue_name: str = "default"
    queue_maxsize: int = 10000
    facts_dir_path = "../facts"
    short_facts_file = "short_facts.txt"
    medium_facts_file = "medium_facts.txt"

    admin_ids: List[int] = []

    class Config:
        env_file = ".env"
