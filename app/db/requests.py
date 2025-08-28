from typing import Literal

from sqlalchemy import select, delete

from .models import (
    session,
    Schedule
)


async def get_schedule(
        today: Literal['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
) -> Schedule:
    async with session() as db:
        return await db.scalar(select(Schedule).where(Schedule.week_day == today))


async def reset_schedule(
        day: Literal['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'],
        short_facts_count: int,
        medium_facts_count: int
):
    async with session() as db:
        await db.execute(delete(Schedule).where(Schedule.week_day == day))
        db.add(Schedule(week_day=day, short_facts=short_facts_count, medium_facts=medium_facts_count))
        await db.commit()


async def get_all_schedules() -> list[Schedule]:
    async with session() as db:
        result = await db.execute(select(Schedule))
        return result.scalars().all()


async def clear_schedule():
    async with session() as db:
        await db.execute(delete(Schedule))
        await db.commit()



from .models import session, PublicationSlot
from sqlalchemy import select, delete


async def add_publication_slot(week_day: str, time: str, content_type: str):
    async with session() as db:
        db.add(PublicationSlot(week_day=week_day, time=time, content_type=content_type))
        await db.commit()


async def get_slots_for_day(week_day: str) -> list[PublicationSlot]:
    async with session() as db:
        result = await db.execute(
            select(PublicationSlot).where(PublicationSlot.week_day == week_day)
        )
        return result.scalars().all()


async def clear_slots():
    async with session() as db:
        await db.execute(delete(PublicationSlot))
        await db.commit()
