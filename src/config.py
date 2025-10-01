from typing import List

from pydantic_settings import BaseSettings


class AppConfig(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///database.sqlite3"
    channel_id: str
    bot_token: str
    debug: bool = False
    queue_name: str = "default"
    redis_url: str = "redis://localhost:6379"
    queue_maxsize: int = 10000
    facts_dir_path: str = "./facts/"
    videos_dir_path: str = "./temp_videos/"
    short_facts_file: str = "short_facts.txt"
    medium_facts_file: str = "medium_facts.txt"

    admin_ids: List[int] = []

    class Config:
        env_file = ".env"
