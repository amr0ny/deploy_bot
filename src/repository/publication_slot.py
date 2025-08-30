from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.sql.expression import select, delete

from src.models import PublicationSlot


class PublicationSlotRepository:
    @staticmethod
    async def add_publication_slot(
        db: AsyncSession, week_day: str, time: str, content_type: str
    ):
        db.add(PublicationSlot(week_day=week_day, time=time, content_type=content_type))
        await db.commit()

    @staticmethod
    async def get_slots_for_day(
        db: AsyncSession, week_day: str
    ) -> list[PublicationSlot]:
        result = await db.execute(
            select(PublicationSlot).where(PublicationSlot.week_day == week_day)
        )
        return result.scalars().all()

    @staticmethod
    async def clear_slots(db: AsyncSession):
        await db.execute(delete(PublicationSlot))
        await db.commit()
