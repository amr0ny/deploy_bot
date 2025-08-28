import os
from typing import Literal

from sqlalchemy import String
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

engine = create_async_engine(os.getenv('DATABASE_URL', 'sqlite+aiosqlite:///database.sqlite3'))
session = async_sessionmaker(engine)


class Base(AsyncAttrs, DeclarativeBase):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)


class Schedule(Base):
    __tablename__ = 'schedule'

    week_day: Mapped[Literal[
        'monday',
        'tuesday',
        'wednesday',
        'thursday',
        'friday',
        'saturday',
        'sunday'
    ]] = mapped_column(String(2), unique=True)
    short_facts: Mapped[int] = mapped_column()
    medium_facts: Mapped[int] = mapped_column()


class State(Base):
    __tablename__ = 'state'

    key: Mapped[Literal['short', 'medium']] = mapped_column(String(6), unique=True)
    index: Mapped[int] = mapped_column()


class PublicationSlot(Base):
    __tablename__ = 'publication_slots'

    week_day: Mapped[str] = mapped_column(String, nullable=False)        # monday, tuesday, etc.
    time: Mapped[str] = mapped_column(String, nullable=False)            # HH:MM
    content_type: Mapped[str] = mapped_column(String, nullable=False)    # short_fact, medium_fact, video


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
