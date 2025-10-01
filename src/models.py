from enum import Enum
from typing import Literal

from sqlalchemy import String
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.ext.asyncio.engine import AsyncEngine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql.functions import func
from sqlalchemy.sql.sqltypes import DateTime, Integer, Enum as SQLEnum


class Base(AsyncAttrs, DeclarativeBase):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)


class Schedule(Base):
    __tablename__ = "schedule"

    week_day: Mapped[
        Literal[
            "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
        ]
    ] = mapped_column(String(2), unique=True)
    short_facts: Mapped[int] = mapped_column()
    medium_facts: Mapped[int] = mapped_column()


class State(Base):
    __tablename__ = "state"

    key: Mapped[Literal["short", "medium"]] = mapped_column(String(6), unique=True)
    index: Mapped[int] = mapped_column()


class PublicationSlot(Base):
    __tablename__ = "publication_slots"

    week_day: Mapped[str] = mapped_column(
        String, nullable=False
    )  # monday, tuesday, etc.
    time: Mapped[str] = mapped_column(String, nullable=False)  # HH:MM
    content_type: Mapped[str] = mapped_column(
        String, nullable=False
    )  # short_fact, medium_fact, video


class FactType(Enum):
    SHORT = "short"
    MEDIUM = "medium"


class Fact(Base):
    __tablename__ = "facts"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    text: Mapped[str] = mapped_column(
        String, nullable=False
    )
    type: Mapped[FactType] = mapped_column(
        SQLEnum(FactType), nullable=False
    )

    def __str__(self):
        return self.text
class Proxy(Base):
    __tablename__ = "proxies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    server: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(String(255), nullable=True)
    password: Mapped[str] = mapped_column(String(255), nullable=True)
    last_used_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment="Время последнего использования прокси",
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self):
        return f"{self.id}. {self.server}, {self.last_used_at}"


async def create_tables(engine: AsyncEngine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
