from typing import List

from pydantic_settings import BaseSettings


class AppConfig(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///database.sqlite3"
    channel_id: str
    bot_token: str
    debug: bool = False
    queue_name: str = "default"
    queue_maxsize: int = 10000
    admin_ids: List[int] = []

    class Config:
        env_file = ".env"
