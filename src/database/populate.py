import asyncio

from sqlalchemy import select

from database import get_db_contextmanager
from database.models.movies import (
    CertificationModel,
    GenreModel,
    StarModel,
    DirectorModel,
    MovieModel
)
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


async def create_test_movies() -> None:
    async with get_db_contextmanager() as db:
        result = await db.execute(select(MovieModel))
        if result.scalars().first():
            return

        certifications = {
            name: CertificationModel(name=name)
            for name in ("G", "PG-13", "R")
        }
        db.add_all(certifications.values())

        genres = {
            name: GenreModel(name=name)
            for name in ("Action", "Drama", "Sci-Fi", "Comedy", "Thriller")
        }
        db.add_all(genres.values())

        stars = {
            name: StarModel(name=name)
            for name in ("Leonardo DiCaprio", "Tom Hardy", "Cillian Murphy", "Scarlett Johansson", "Robert Downey Jr.")
        }
        db.add_all(stars.values())

        directors = {
            name: DirectorModel(name=name)
            for name in ("Christopher Nolan", "Quentin Tarantino", "Denis Villeneuve")
        }
        db.add_all(directors.values())

        await db.flush()

        movies = [
            MovieModel(
                name="Inception",
                year=2010,
                time=148,
                imdb=8.8,
                votes=2200000,
                meta_score=74.0,
                gross=836800000.0,
                description="A thief who steals corporate secrets through dream-sharing technology.",
                price=14.99,
                certification=certifications["PG-13"],
                genres=[genres["Action"], genres["Sci-Fi"]],
                stars=[stars["Leonardo DiCaprio"], stars["Tom Hardy"]],
                directors=[directors["Christopher Nolan"]]
            ),
            MovieModel(
                name="Oppenheimer",
                year=2023,
                time=180,
                imdb=8.4,
                votes=650000,
                meta_score=88.0,
                gross=950000000.0,
                description="The story of J. Robert Oppenheimer and the creation of the atomic bomb.",
                price=19.99,
                certification=certifications["R"],
                genres=[genres["Drama"]],
                stars=[stars["Cillian Murphy"], stars["Robert Downey Jr."]],
                directors=[directors["Christopher Nolan"]]
            ),
            MovieModel(
                name="Dune",
                year=2021,
                time=155,
                imdb=8.0,
                votes=750000,
                meta_score=74.0,
                gross=402000000.0,
                description="A noble family becomes embroiled in a war for control over a desert planet.",
                price=17.99,
                certification=certifications["PG-13"],
                genres=[genres["Sci-Fi"], genres["Drama"]],
                stars=[stars["Scarlett Johansson"]],
                directors=[directors["Denis Villeneuve"]]
            ),
            MovieModel(
                name="Pulp Fiction",
                year=1994,
                time=154,
                imdb=8.9,
                votes=2100000,
                meta_score=94.0,
                gross=213900000.0,
                description="The lives of two mob hitmen, a boxer, and others intertwine in Los Angeles.",
                price=9.99,
                certification=certifications["R"],
                genres=[genres["Thriller"], genres["Comedy"]],
                stars=[stars["Tom Hardy"]],
                directors=[directors["Quentin Tarantino"]]
            ),
            MovieModel(
                name="The Avengers",
                year=2012,
                time=143,
                imdb=8.0,
                votes=1400000,
                meta_score=69.0,
                gross=1519000000.0,
                description="Earth's mightiest heroes assemble to stop an alien invasion.",
                price=12.99,
                certification=certifications["PG-13"],
                genres=[genres["Action"]],
                stars=[stars["Robert Downey Jr."], stars["Scarlett Johansson"]],
                directors=[]
            ),
        ]
        db.add_all(movies)

        await db.commit()


async def main() -> None:
    await create_user_groups()
    await create_admin_user()
    await create_test_movies()


if __name__ == "__main__":
    asyncio.run(main())
