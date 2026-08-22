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
    MovieListItemResponseSchema
)
from database.models.movies import (
    CertificationModel,
    GenreModel,
    StarModel,
    MovieModel
)
from database import get_db
from security.dependencies import require_roles
from database.models.accounts import (
    UserModel,
    UserGroupEnum
)

from schemas.accounts import MessageResponseSchema


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
