import asyncio
import csv
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.movies import (
    CertificationModel,
    GenreModel,
    StarModel,
    DirectorModel,
    MovieModel
)
from database.models.accounts import UserGroup, UserGroupEnum, UserModel
from database.models import carts, orders, payments  # noqa: F401
from config.dependencies import get_settings
from config.settings import BaseAppSettings
from database import get_db_contextmanager


class CSVDatabaseSeeder:

    def __init__(self, db_session: AsyncSession, settings: BaseAppSettings, csv_file_path: str) -> None:
        self.db_session = db_session
        self.settings = settings
        self.csv_file_path = csv_file_path

    async def create_user_groups(self) -> None:
        result = await self.db_session.execute(select(UserGroup))
        existing_groups = {group.name for group in result.scalars().all()}

        for group_enum in UserGroupEnum:
            if group_enum not in existing_groups:
                self.db_session.add(UserGroup(name=group_enum))

    async def create_admin_user(self) -> None:
        result = await self.db_session.execute(select(UserModel).where(UserModel.email == self.settings.ADMIN_EMAIL))
        existing_admin = result.scalars().first()
        if existing_admin:
            return

        admin_group = await self.db_session.scalar(select(UserGroup).where(UserGroup.name == UserGroupEnum.ADMIN))
        if not admin_group:
            raise RuntimeError("Admin group not found. Run create_user_groups() first.")

        admin_user = UserModel.create(
            email=self.settings.ADMIN_EMAIL,
            raw_password=self.settings.ADMIN_PASSWORD,
            group_id=admin_group.id
        )
        admin_user.is_active = True

        self.db_session.add(admin_user)

    async def _get_or_create(self, model: type, name: str, cache: dict) -> object:
        if name in cache:
            return cache[name]

        result = await self.db_session.execute(select(model).where(model.name == name))
        obj = result.scalars().first()

        if obj is None:
            obj = model(name=name)
            self.db_session.add(obj)
            await self.db_session.flush()

        cache[name] = obj
        return obj

    async def create_movies_from_csv(self) -> None:
        result = await self.db_session.execute(select(MovieModel))
        if result.scalars().first():
            return

        certifications_cache: dict = {}
        genres_cache: dict = {}
        stars_cache: dict = {}
        directors_cache: dict = {}

        with open(self.csv_file_path) as f:
            for row in csv.DictReader(f):
                certification = await self._get_or_create(
                    CertificationModel, row["certification"], certifications_cache
                )

                genres = [
                    await self._get_or_create(
                        GenreModel, name.strip(), genres_cache
                    )
                    for name in row["genres"].split(",")
                ]
                stars = [
                    await self._get_or_create(
                        StarModel, name.strip(), stars_cache
                    )
                    for name in row["stars"].split(",")
                ]
                directors = [
                    await self._get_or_create(
                        DirectorModel, name.strip(), directors_cache
                    )
                    for name in row["directors"].split(",")
                ]

                movie = MovieModel(
                    name=row["name"],
                    year=int(row["year"]),
                    time=int(row["time"]),
                    imdb=float(row["imdb"]),
                    votes=int(row["votes"]),
                    meta_score=float(row["meta_score"]),
                    gross=float(row["gross"]),
                    description=row["description"],
                    price=row["price"],
                    certification=certification,
                    genres=genres,
                    stars=stars,
                    directors=directors,
                )
                self.db_session.add(movie)

    async def seed(self) -> None:
        await self.create_user_groups()
        await self.create_admin_user()
        await self.create_movies_from_csv()
        await self.db_session.commit()


async def main() -> None:
    settings = get_settings()

    async with get_db_contextmanager() as session:
        seeder = CSVDatabaseSeeder(
            db_session=session,
            settings=settings,
            csv_file_path=settings.PATH_TO_MOVIES_CSV
        )
        await seeder.seed()


if __name__ == "__main__":
    asyncio.run(main())
