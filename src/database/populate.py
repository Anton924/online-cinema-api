import asyncio

from sqlalchemy import select

from database import get_db_contextmanager
from database.models.accounts import UserGroup, UserGroupEnum, UserModel
from config.dependencies import (
    get_settings
)


async def create_user_groups() -> None:
    async with get_db_contextmanager() as db:
        result = await db.execute(select(UserGroup))
        existing_groups = {group.name for group in result.scalars().all()}

        for group_enum in UserGroupEnum:
            if group_enum not in existing_groups:
                db.add(UserGroup(name=group_enum))

        await db.commit()


async def create_admin_user() -> None:
    settings = get_settings()

    async with get_db_contextmanager() as db:
        result = await db.execute(select(UserModel).where(UserModel.email == settings.ADMIN_EMAIL))
        existing_admin = result.scalars().first()
        if existing_admin:
            return

        admin_group = await db.scalar(select(UserGroup).where(UserGroup.name == UserGroupEnum.ADMIN))
        if not admin_group:
            raise RuntimeError("Admin group not found. Run create_user_groups() first.")

        admin_user = UserModel.create(
            email=settings.ADMIN_EMAIL,
            raw_password=settings.ADMIN_PASSWORD,
            group_id=admin_group.id
        )
        admin_user.is_active = True

        db.add(admin_user)
        await db.commit()


async def main() -> None:
    await create_user_groups()
    await create_admin_user()


if __name__ == "__main__":
    asyncio.run(main())
