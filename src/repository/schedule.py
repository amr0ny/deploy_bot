from typing import Literal

from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.sql.expression import select, delete

from src.models import Schedule


class ScheduleRepository:
    @staticmethod
    async def get_schedule(
        db: AsyncSession,
        today: Literal[
            "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
        ],
    ) -> Schedule:
        return await db.scalar(select(Schedule).where(Schedule.week_day == today))

    @staticmethod
    async def reset_schedule(
        db: AsyncSession,
        day: Literal[
            "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
        ],
        short_facts_count: int,
        medium_facts_count: int,
    ):
        await db.execute(delete(Schedule).where(Schedule.week_day == day))
        db.add(
            Schedule(
                week_day=day,
                short_facts=short_facts_count,
                medium_facts=medium_facts_count,
            )
        )
        await db.commit()

    @staticmethod
    async def get_all_schedules(db: AsyncSession) -> list[Schedule]:
        result = await db.execute(select(Schedule))
        return result.scalars().all()

    @staticmethod
    async def clear_schedule(db: AsyncSession):
        await db.execute(delete(Schedule))
        await db.commit()
