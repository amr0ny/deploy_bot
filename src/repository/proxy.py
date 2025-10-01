from datetime import datetime
import re
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.future import select
from sqlalchemy import delete
from typing import List, Optional
import time


proxy_regex = re.compile(
    r"^(http|https|socks4|socks5)://"  # протокол
    r"(([a-zA-Z0-9.-]+)|(\d{1,3}(\.\d{1,3}){3}))"  # домен или IPv4
    r":([1-9]\d{0,4})$"  # порт
)

from src.models import Proxy, Base

class ProxyRepository:
    def __init__(self, session_maker: async_sessionmaker[AsyncSession]):
        self.session_maker = session_maker

    async def add_proxy(self, server: str, username: Optional[str], password: Optional[str]):
        if not proxy_regex.match(server):
            raise ValueError("Invalid Proxy")
        async with self.session_maker() as session:
            async with session.begin():
                session.add(Proxy(server=server, username=username, password=password))

    async def remove_proxy(self, id: int):
        async with self.session_maker() as session:
            async with session.begin():
                result = await session.execute(select(Proxy).where(Proxy.id == id))
                proxy = result.scalars().first()
                if not proxy:
                    raise ValueError(f"Proxy with id {id} not found")
                await session.delete(proxy)

    async def remove_all_proxies(self):
        async with self.session_maker() as session:
            async with session.begin():
                await session.execute(delete(Proxy))

    async def get_proxies(self) -> List[Proxy]:
        async with self.session_maker() as session:
            result = await session.execute(select(Proxy))
            return result.scalars().all()

    async def get_next_proxy(self) -> Optional[Proxy]:
        async with self.session_maker() as session:
            async with session.begin():
                result = await session.execute(
                    select(Proxy)
                    .order_by(Proxy.last_used_at.asc().nullsfirst())
                    .limit(1)
                )
                proxy = result.scalars().first()
                if not proxy:
                    return None

                proxy.last_used_at = datetime.utcnow()
                session.add(proxy)  # необязательно, но безопасно
                await session.flush()
                return proxy
