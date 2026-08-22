from typing import Annotated, Any

from fastapi import Depends, status, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.movies import (
    CertificationRequestSchema,
    CertificationResponseSchema,
    GenreRequestSchema,
    GenreResponseSchema,
    GenreWithMovieCountResponseSchema,
    StarRequestSchema,
    StarResponseSchema,
    DirectorRequestSchema,
    DirectorResponseSchema,
    MovieCreateRequestSchema,
    MovieListItemResponseSchema,
    MovieDetailResponseSchema,
    MovieUpdateRequestSchema,
    PaginatedMovieResponseSchema
)
from database.models.movies import (
    CertificationModel,
    GenreModel,
    StarModel,
    DirectorModel,
    MovieModel
)
from database import get_db
from security.dependencies import require_roles
from database.models.accounts import (
    UserModel,
    UserGroupEnum
)

from schemas.accounts import MessageResponseSchema
from sqlalchemy.orm import joinedload


def update_instance(instance: Any, data: BaseModel) -> None:
    data = data.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(instance, key, value)


async def create_certification_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    certification_data: CertificationRequestSchema,
    current_user: Annotated[UserModel, Depends(require_roles(UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR))]
) -> CertificationResponseSchema:
    stmt = select(CertificationModel).where(
        CertificationModel.name == certification_data.name
    )

    result = await db.execute(stmt)
    certification = result.scalars().first()

    if certification:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A certification with this name {certification.name!r} already exists."
        )

    try:
        certification = CertificationModel(
            name=certification_data.name
        )

        db.add(certification)
        await db.commit()
        await db.refresh(certification)

        return CertificationResponseSchema.model_validate(certification)
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the certification."
        ) from e


async def get_certifications(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[CertificationResponseSchema]:
    stmt = select(CertificationModel)
    result = await db.execute(stmt)
    certifications = result.scalars().all()

    if not certifications:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No certifications found."
        )

    certification_list = [
        CertificationResponseSchema.model_validate(certification)
        for certification in certifications
    ]

    return certification_list


async def get_certification_by_id(
    db: Annotated[AsyncSession, Depends(get_db)],
    certification_id: int
) -> CertificationResponseSchema:
    stmt = select(CertificationModel).where(
        CertificationModel.id == certification_id
    )

    result = await db.execute(stmt)
    certification = result.scalars().first()

    if not certification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certification with id {certification_id} not found."
        )

    return CertificationResponseSchema.model_validate(certification)


async def update_certification_service(
        db: Annotated[AsyncSession, Depends(get_db)],
        certification_id: int,
        data: CertificationRequestSchema,
        current_user: Annotated[UserModel, Depends(require_roles(UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR))]
) -> CertificationResponseSchema:
    stmt = select(CertificationModel).where(
        CertificationModel.id == certification_id
    )
    result = await db.execute(stmt)
    certification = result.scalars().first()

    if not certification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certification with id {certification_id} not found."
        )

    stmt = select(CertificationModel).where(
        CertificationModel.name == data.name,
        CertificationModel.id != certification_id
    )
    result = await db.execute(stmt)
    is_the_same_name = result.scalars().first()

    if is_the_same_name:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A certification with this name {data.name!r} already exists."
        )

    try:
        update_instance(certification, data=data)
        db.add(certification)
        await db.commit()
        await db.refresh(certification)

        return CertificationResponseSchema.model_validate(certification)
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the certification."
        ) from e


async def delete_certification_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserModel, Depends(require_roles(UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR))],
    certification_id: int,
) -> MessageResponseSchema:
    stmt = select(CertificationModel).where(
        CertificationModel.id == certification_id
    )
    result = await db.execute(stmt)
    certification = result.scalars().first()

    if not certification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certification with id {certification_id} not found."
        )

    try:
        await db.delete(certification)
        await db.commit()
        return MessageResponseSchema(
            message=f"Certification {certification.name!r} was successfully deleted."
        )
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete certification {certification.name!r} - it is still assigned to one or more movies."
        ) from e
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the certification."
        ) from e


async def create_genre_service(
        db: Annotated[AsyncSession, Depends(get_db)],
        genre_data: GenreRequestSchema,
        current_user: Annotated[UserModel, Depends(require_roles(UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR))]
) -> GenreResponseSchema:
    stmt = select(GenreModel).where(
        GenreModel.name == genre_data.name
    )

    result = await db.execute(stmt)
    genre = result.scalars().first()

    if genre:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A genre with this name {genre.name!r} already exists."
        )

    try:
        genre = GenreModel(
            name=genre_data.name
        )

        db.add(genre)
        await db.commit()
        await db.refresh(genre)

        return GenreResponseSchema.model_validate(genre)
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the genre."
        ) from e


async def get_genres_with_movie_count(
        db: Annotated[AsyncSession, Depends(get_db)],
) -> list[GenreResponseSchema]:
    stmt = select(GenreModel)
    result = await db.execute(stmt)

    genres = result.scalars().all()

    if not genres:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No genres found"
        )

    genre_list = [
        GenreResponseSchema.model_validate(genre)
        for genre in genres
    ]

    return genre_list


async def get_genre_by_id(
    db: Annotated[AsyncSession, Depends(get_db)],
    genre_id: int
) -> GenreWithMovieCountResponseSchema:
    stmt = (
        select(GenreModel, func.count(MovieModel.id).label("movie_count"))
        .outerjoin(GenreModel.movies)
        .group_by(GenreModel.id)
        .where(GenreModel.id == genre_id)
    )

    result = await db.execute(stmt)
    row = result.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Genre with id {genre_id} not found."
        )

    genre, movie_count = row

    return GenreWithMovieCountResponseSchema(
        id=genre.id,
        name=genre.name,
        movie_count=movie_count
    )


async def get_movies_by_genre(
    db: Annotated[AsyncSession, Depends(get_db)],
    genre_id: int
) -> list[MovieListItemResponseSchema] | MessageResponseSchema:
    stmt = select(GenreModel).where(
        GenreModel.id == genre_id
    )

    result = await db.execute(stmt)
    genre = result.scalars().first()

    if not genre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Genre with id {genre_id} not found."
        )
    stmt = (
        select(MovieModel)
        .join(MovieModel.genres)
        .where(GenreModel.id.in_([genre_id]))
    )

    result = await db.execute(stmt)
    movies = result.scalars().all()

    if not movies:
        return MessageResponseSchema(
            message=f"No movies for {genre.name} genre"
        )

    return [
        MovieListItemResponseSchema.model_validate(movie)
        for movie in movies
    ]


async def update_genre_service(
        db: Annotated[AsyncSession, Depends(get_db)],
        genre_id: int,
        data: GenreRequestSchema,
        current_user: Annotated[UserModel, Depends(require_roles(UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR))]
) -> GenreResponseSchema:
    stmt = select(GenreModel).where(
        GenreModel.id == genre_id
    )
    result = await db.execute(stmt)
    genre = result.scalars().first()

    if not genre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Genre with id {genre_id} not found."
        )

    stmt = select(GenreModel).where(
        GenreModel.name == data.name,
        GenreModel.id != genre_id
    )
    result = await db.execute(stmt)
    is_the_same_name = result.scalars().first()

    if is_the_same_name:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A genre with this name {data.name!r} already exists."
        )

    try:
        update_instance(genre, data=data)
        db.add(genre)
        await db.commit()
        await db.refresh(genre)

        return GenreResponseSchema.model_validate(genre)
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the genre."
        ) from e


async def delete_genre_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserModel, Depends(require_roles(UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR))],
    genre_id: int,
) -> MessageResponseSchema:
    stmt = select(GenreModel).where(
        GenreModel.id == genre_id
    )
    result = await db.execute(stmt)
    genre = result.scalars().first()

    if not genre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Genre with id {genre_id} not found."
        )

    try:
        await db.delete(genre)
        await db.commit()
        return MessageResponseSchema(
            message=f"Genre {genre.name!r} was successfully deleted."
        )

    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the genre."
        ) from e


async def get_or_create_genre(
    db: Annotated[AsyncSession, Depends(get_db)],
    value: str
) -> GenreModel:
    stmt = select(GenreModel).where(GenreModel.name == value)
    result = await db.execute(stmt)
    genre = result.scalars().first()

    if not genre:
        genre = GenreModel(
            name=value
        )
        try:
            db.add(genre)
            await db.commit()
            await db.refresh(genre)
        except SQLAlchemyError as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred while creating the genre."
            ) from e
    return genre


async def resolve_genre(
    db: Annotated[AsyncSession, Depends(get_db)],
    value: str | int
) -> GenreModel:
    if isinstance(value, int):
        genre = await db.get(GenreModel, value)
        if not genre:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Genre with id {value} not found."
            )
        return genre
    return await get_or_create_genre(
        db=db,
        value=value
    )


async def create_star_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    star_data: StarRequestSchema,
    current_user: Annotated[UserModel, Depends(require_roles(UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR))]
) -> StarResponseSchema:
    stmt = select(StarModel).where(
        StarModel.name == star_data.name
    )

    result = await db.execute(stmt)
    star = result.scalars().first()

    if star:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A star with this name {star.name!r} already exists."
        )

    try:
        star = StarModel(
            name=star_data.name
        )

        db.add(star)
        await db.commit()
        await db.refresh(star)

        return StarResponseSchema.model_validate(star)
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the star."
        ) from e


async def get_stars(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[StarResponseSchema]:
    stmt = select(StarModel)
    result = await db.execute(stmt)
    stars = result.scalars().all()

    if not stars:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No stars found."
        )

    star_list = [
        StarResponseSchema.model_validate(star)
        for star in stars
    ]

    return star_list


async def get_star_by_id(
    db: Annotated[AsyncSession, Depends(get_db)],
    star_id: int
) -> StarResponseSchema:
    stmt = select(StarModel).where(
        StarModel.id == star_id
    )

    result = await db.execute(stmt)
    star = result.scalars().first()

    if not star:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Star with id {star_id} not found."
        )

    return StarResponseSchema.model_validate(star)


async def update_star_service(
        db: Annotated[AsyncSession, Depends(get_db)],
        star_id: int,
        data: StarRequestSchema,
        current_user: Annotated[UserModel, Depends(require_roles(UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR))]
) -> StarResponseSchema:
    stmt = select(StarModel).where(
        StarModel.id == star_id
    )
    result = await db.execute(stmt)
    star = result.scalars().first()

    if not star:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Star with id {star_id} not found."
        )

    stmt = select(StarModel).where(
        StarModel.name == data.name,
        StarModel.id != star_id
    )
    result = await db.execute(stmt)
    is_the_same_name = result.scalars().first()

    if is_the_same_name:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A star with this name {data.name!r} already exists."
        )

    try:
        update_instance(star, data=data)
        db.add(star)
        await db.commit()
        await db.refresh(star)

        return StarResponseSchema.model_validate(star)
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the star."
        ) from e


async def delete_star_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserModel, Depends(require_roles(UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR))],
    star_id: int,
) -> MessageResponseSchema:
    stmt = select(StarModel).where(
        StarModel.id == star_id
    )
    result = await db.execute(stmt)
    star = result.scalars().first()

    if not star:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Star with id {star_id} not found."
        )

    try:
        await db.delete(star)
        await db.commit()
        return MessageResponseSchema(
            message=f"Star {star.name!r} was successfully deleted."
        )
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the star."
        ) from e


async def get_or_create_star(
    db: Annotated[AsyncSession, Depends(get_db)],
    value: str
) -> StarModel:
    stmt = select(StarModel).where(StarModel.name == value)
    result = await db.execute(stmt)
    star = result.scalars().first()

    if not star:
        star = StarModel(
            name=value
        )
        try:
            db.add(star)
            await db.commit()
            await db.refresh(star)
        except SQLAlchemyError as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred while creating the star."
            ) from e
    return star


async def resolve_star(
    db: Annotated[AsyncSession, Depends(get_db)],
    value: str | int
) -> StarModel:
    if isinstance(value, int):
        star = await db.get(StarModel, value)
        if not star:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Star with id {value} not found."
            )
        return star
    return await get_or_create_star(
        db=db,
        value=value
    )


async def create_director_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    director_data: DirectorRequestSchema,
    current_user: Annotated[UserModel, Depends(require_roles(UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR))]
) -> DirectorResponseSchema:
    stmt = select(DirectorModel).where(
        DirectorModel.name == director_data.name
    )

    result = await db.execute(stmt)
    director = result.scalars().first()

    if director:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A director with this name {director.name!r} already exists."
        )

    try:
        director = DirectorModel(
            name=director_data.name
        )

        db.add(director)
        await db.commit()
        await db.refresh(director)

        return DirectorResponseSchema.model_validate(director)
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the director."
        ) from e


async def get_directors(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[DirectorResponseSchema]:
    stmt = select(DirectorModel)
    result = await db.execute(stmt)
    directors = result.scalars().all()

    if not directors:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No directors found."
        )

    director_list = [
        DirectorResponseSchema.model_validate(director)
        for director in directors
    ]

    return director_list


async def get_director_by_id(
    db: Annotated[AsyncSession, Depends(get_db)],
    director_id: int
) -> DirectorResponseSchema:
    stmt = select(DirectorModel).where(
        DirectorModel.id == director_id
    )

    result = await db.execute(stmt)
    director = result.scalars().first()

    if not director:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Director with id {director_id} not found."
        )

    return DirectorResponseSchema.model_validate(director)


async def update_director_service(
        db: Annotated[AsyncSession, Depends(get_db)],
        director_id: int,
        data: DirectorRequestSchema,
        current_user: Annotated[UserModel, Depends(require_roles(UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR))]
) -> DirectorResponseSchema:
    stmt = select(DirectorModel).where(
        DirectorModel.id == director_id,
    )
    result = await db.execute(stmt)
    director = result.scalars().first()

    if not director:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Director with id {director_id} not found."
        )

    stmt = select(DirectorModel).where(
        DirectorModel.name == data.name,
        DirectorModel.id != director_id
    )
    result = await db.execute(stmt)
    is_the_same_name = result.scalars().first()

    if is_the_same_name:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A director with this name {data.name!r} already exists."
        )

    try:
        update_instance(director, data=data)
        db.add(director)
        await db.commit()
        await db.refresh(director)

        return DirectorResponseSchema.model_validate(director)
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the director."
        ) from e


async def delete_director_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserModel, Depends(require_roles(UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR))],
    director_id: int,
) -> MessageResponseSchema:
    stmt = select(DirectorModel).where(
        DirectorModel.id == director_id
    )
    result = await db.execute(stmt)
    director = result.scalars().first()

    if not director:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Director with id {director_id} not found."
        )

    try:
        await db.delete(director)
        await db.commit()
        return MessageResponseSchema(
            message=f"Director {director.name!r} was successfully deleted."
        )
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the director."
        ) from e


async def get_or_create_director(
    db: Annotated[AsyncSession, Depends(get_db)],
    value: str
) -> DirectorModel:
    stmt = select(DirectorModel).where(DirectorModel.name == value)
    result = await db.execute(stmt)
    director = result.scalars().first()

    if not director:
        director = DirectorModel(
            name=value
        )
        try:
            db.add(director)
            await db.commit()
            await db.refresh(director)
        except SQLAlchemyError as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred while creating the director."
            ) from e
    return director


async def resolve_director(
    db: Annotated[AsyncSession, Depends(get_db)],
    value: str | int
) -> DirectorModel:
    if isinstance(value, int):
        director = await db.get(DirectorModel, value)
        if not director:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Director with id {value} not found."
            )
        return director
    return await get_or_create_director(
        db=db,
        value=value
    )


async def create_movie_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserModel, Depends(require_roles(UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR))],
    movie_data: MovieCreateRequestSchema
) -> MovieDetailResponseSchema:
    stmt = select(CertificationModel).where(CertificationModel.id == movie_data.certification_id)
    result = await db.execute(stmt)
    certification = result.scalars().first()

    if not certification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certification with id {movie_data.certification_id} not found."
        )

    stmt = select(MovieModel).where(
        MovieModel.name == movie_data.name,
        MovieModel.year == movie_data.year,
        MovieModel.time == movie_data.time
    )

    result = await db.execute(stmt)
    is_unique_constraint_violated = result.scalars().first()

    if is_unique_constraint_violated:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A movie with this name, year, and duration already exists."
        )

    genres = [
        await resolve_genre(
            db=db,
            value=genre_id_or_name
        )
        for genre_id_or_name in movie_data.genre_ids_or_names
    ]

    stars = [
        await resolve_star(
            db=db,
            value=star_id_or_name
        )
        for star_id_or_name in movie_data.star_ids_or_names
    ]

    directors = [
        await resolve_director(
            db=db,
            value=director_id_or_name
        )
        for director_id_or_name in movie_data.director_ids_or_names
    ]

    movie_data_cleaned = movie_data.model_dump(
        exclude=("genre_ids_or_names", "director_ids_or_names", "star_ids_or_names")
    )

    try:
        movie = MovieModel(
            **movie_data_cleaned
        )

        movie.genres = genres
        movie.stars = stars
        movie.directors = directors

        db.add(movie)
        await db.commit()
        await db.refresh(movie, ["genres", "stars", "directors"])

        return MovieDetailResponseSchema.model_validate(movie)
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the movie."
        ) from e


async def get_movies(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = 1,
    per_page: int = 20
) -> PaginatedMovieResponseSchema:
    stmt = select(MovieModel).options(
        joinedload(MovieModel.certification)
    ).offset(per_page * (page - 1)).limit(per_page)

    result = await db.execute(stmt)
    movies = result.scalars().all()

    stmt = select(func.count(MovieModel.id).label("total"))
    total = await db.scalar(stmt)

    if total % per_page == 0:
        total_pages = total // per_page
    else:
        total_pages = total // per_page + 1

    movies_list = [
        MovieListItemResponseSchema.model_validate(movie)
        for movie in movies
    ]

    return PaginatedMovieResponseSchema(
        items=movies_list,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )


async def get_movie_by_id(
    db: Annotated[AsyncSession, Depends(get_db)],
    movie_id: int,
) -> MovieDetailResponseSchema:
    stmt = (
        select(MovieModel)
        .where(MovieModel.id == movie_id)
        .options(
            joinedload(MovieModel.certification),
            joinedload(MovieModel.genres),
            joinedload(MovieModel.stars),
            joinedload(MovieModel.directors)
        )
    )
    result = await db.execute(stmt)

    movie = result.scalars().unique().first()

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Movie with id {movie_id} not found."
        )

    return MovieDetailResponseSchema.model_validate(movie)


async def update_movie_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserModel, Depends(require_roles(UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR))],
    movie_id: int,
    update_data: MovieUpdateRequestSchema
) -> MovieDetailResponseSchema:
    stmt = (
        select(MovieModel)
        .where(MovieModel.id == movie_id)
        .options(
            joinedload(MovieModel.certification),
            joinedload(MovieModel.genres),
            joinedload(MovieModel.stars),
            joinedload(MovieModel.directors)
        )
    )
    result = await db.execute(stmt)
    movie = result.scalars().unique().first()

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Movie with id {movie_id} not found."
        )

    movie_update_data = update_data.model_dump(exclude_unset=True)

    certification_id = movie_update_data.pop("certification_id", None)
    genre_ids_or_names = movie_update_data.pop("genre_ids_or_names", None)
    director_ids_or_names = movie_update_data.pop("director_ids_or_names", None)
    star_ids_or_names = movie_update_data.pop("star_ids_or_names", None)

    try:
        for key, value in movie_update_data.items():
            setattr(movie, key, value)

        if any(key in movie_update_data for key in ("name", "year", "time")):
            stmt = select(MovieModel).where(
                MovieModel.name == movie.name,
                MovieModel.year == movie.year,
                MovieModel.time == movie.time,
                MovieModel.id != movie_id
            )
            result = await db.execute(stmt)
            is_unique_constraint_violated = result.scalars().first()

            if is_unique_constraint_violated:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A movie with this name, year, and duration already exists."
                )

        if certification_id:
            certification = await db.get(CertificationModel, certification_id)
            if not certification:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Certification with id {certification_id} not found."
                )

        if genre_ids_or_names:
            genres = [
                await resolve_genre(
                    db=db,
                    value=genre_id_or_name
                ) for genre_id_or_name in genre_ids_or_names
            ]
            movie.genres = genres

        if star_ids_or_names:
            stars = [
                await resolve_star(
                    db=db,
                    value=star_id_or_name
                ) for star_id_or_name in star_ids_or_names
            ]
            movie.stars = stars

        if director_ids_or_names:
            directors = [
                await resolve_director(
                    db=db,
                    value=director_id_or_name
                ) for director_id_or_name in director_ids_or_names
            ]
            movie.directors = directors

        await db.commit()

        return MovieDetailResponseSchema.model_validate(movie)
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the movie."
        ) from e


async def delete_movie_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserModel, Depends(require_roles(UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR))],
    movie_id: int,
) -> MessageResponseSchema:
    movie = await db.get(MovieModel, movie_id)

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Movie with id {movie_id} not found."
        )

    try:
        # TODO: Add exception: f"Cannot delete movie '{name}' - it has already been purchased by one or more users."
        await db.delete(movie)
        await db.commit()

        return MessageResponseSchema(
            message=f"Movie {movie.name!r} was successfully deleted."
        )
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the movie."
        ) from e
