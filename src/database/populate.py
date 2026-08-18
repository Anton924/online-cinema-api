import asyncio

from sqlalchemy import select

from database import get_db_contextmanager
from database.models.accounts import UserGroup, UserGroupEnum


async def create_user_groups() -> None:
    async with get_db_contextmanager() as db:
        result = await db.execute(select(UserGroup))
        existing_groups = {group.name for group in result.scalars().all()}

        for group_enum in UserGroupEnum:
            if group_enum not in existing_groups:
                db.add(UserGroup(name=group_enum))

        await db.commit()

if __name__ == "__main__":
    asyncio.run(create_user_groups())