from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select, delete, func
from datetime import datetime

from src.models import Fact, FactType


class FactRepository:
    def __init__(self, session_maker: async_sessionmaker[AsyncSession]):
        self.session_maker = session_maker

    async def get_next_fact(self, fact_type: FactType) -> Optional[str]:
        """Получить следующий факт (возвращает и удаляет строку)"""
        async with self.session_maker() as session:
            async with session.begin():
                result = await session.execute(
                    select(Fact)
                    .where(Fact.type == fact_type)
                    .order_by(Fact.id.asc())
                    .limit(1)
                )
                fact = result.scalars().first()
                if not fact:
                    return None

                fact_text = fact.text
                await session.delete(fact)
                return fact_text

    async def get_facts_count(self, fact_type: FactType) -> int:
        """Получить количество фактов по типу"""
        async with self.session_maker() as session:
            result = await session.execute(
                select(func.count(Fact.id))
                .where(Fact.type == fact_type)
            )
            return result.scalar() or 0

    async def add_facts_batch(self, texts: List[str], fact_type: FactType):
        """Добавить batch фактов"""
        async with self.session_maker() as session:
            async with session.begin():
                facts = [Fact(text=text, type=fact_type) for text in texts]
                session.add_all(facts)

    async def remove_all_facts(self, fact_type: FactType):
        """Удалить все факты (опционально по типу)"""
        async with self.session_maker() as session:
            async with session.begin():
                await session.execute(
                    delete(Fact).where(Fact.type == fact_type)
                )