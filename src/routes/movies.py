from typing import Annotated
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.movies import (
    CertificationRequestSchema,
    CertificationResponseSchema,
    GenreRequestSchema,
    GenreResponseSchema,
    GenreWithMovieCountResponseSchema,
    MovieListItemResponseSchema
)
from services.movies import (
    create_certification_service,
    get_certifications,
    get_certification_by_id,
    update_certification_service,
    delete_certification_service,
    create_genre_service,
    get_genres_with_movie_count,
    get_genre_by_id,
    get_movies_by_genre,
    update_genre_service,
    delete_genre_service
)
from database.models.accounts import (
    UserModel,
    UserGroupEnum
)
from database import get_db
from security.dependencies import require_roles
from schemas.accounts import MessageResponseSchema

router = APIRouter()


@router.post(
    "/certifications",
    status_code=status.HTTP_201_CREATED,
    response_model=CertificationResponseSchema
)
async def create_certification(
    db: Annotated[AsyncSession, Depends(get_db)],
    certification_data: CertificationRequestSchema,
    current_user: Annotated[UserModel, Depends(require_roles(UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR))]
) -> CertificationResponseSchema:
    return await create_certification_service(
        db=db,
        certification_data=certification_data,
        current_user=current_user
    )


@router.get(
    "/certifications",
    status_code=status.HTTP_200_OK,
    response_model=list[CertificationResponseSchema]
)
async def list_certifications(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> list[CertificationResponseSchema]:
    return await get_certifications(
        db=db
    )


@router.get(
    "/certifications/{certification_id}",
    status_code=status.HTTP_200_OK,
    response_model=CertificationResponseSchema
)
async def get_certification(
    db: Annotated[AsyncSession, Depends(get_db)],
    certification_id: int
) -> CertificationResponseSchema:
    return await get_certification_by_id(
        db=db,
        certification_id=certification_id
    )


@router.patch(
    "/certifications/{certification_id}",
    status_code=status.HTTP_200_OK,
    response_model=CertificationResponseSchema
)
async def update_certification(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserModel, Depends(require_roles(UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR))],
    certification_id: int,
    data: CertificationRequestSchema
) -> CertificationResponseSchema:
    return await update_certification_service(
        db=db,
        current_user=current_user,
        certification_id=certification_id,
        data=data
    )


@router.delete(
    "/certifications/{certification_id}",
    status_code=status.HTTP_200_OK,
    response_model=MessageResponseSchema
)
async def delete_certification(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserModel, Depends(require_roles(UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR))],
    certification_id: int,
) -> MessageResponseSchema:
    return await delete_certification_service(
        db=db,
        current_user=current_user,
        certification_id=certification_id,
    )


@router.post(
    "/genres",
    status_code=status.HTTP_201_CREATED,
    response_model=GenreResponseSchema
)
async def create_genre(
    db: Annotated[AsyncSession, Depends(get_db)],
    genre_data: GenreRequestSchema,
    current_user: Annotated[UserModel, Depends(require_roles(UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR))]
) -> GenreResponseSchema:
    return await create_genre_service(
        db=db,
        genre_data=genre_data,
        current_user=current_user
    )


@router.get(
    "/genres",
    status_code=status.HTTP_200_OK,
    response_model=list[GenreResponseSchema]
)
async def list_genres(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> list[GenreResponseSchema]:
    return await get_genres_with_movie_count(
        db=db
    )


@router.get(
    "/genres/{genre_id}",
    status_code=status.HTTP_200_OK,
    response_model=GenreWithMovieCountResponseSchema
)
async def get_genre(
    db: Annotated[AsyncSession, Depends(get_db)],
    genre_id: int
) -> GenreWithMovieCountResponseSchema:
    return await get_genre_by_id(
        db=db,
        genre_id=genre_id
    )


@router.get(
    "/genres/{genre_id}/movies",
    status_code=status.HTTP_200_OK,
    response_model=list[MovieListItemResponseSchema] | MessageResponseSchema
)
async def get_genre_movies(
    db: Annotated[AsyncSession, Depends(get_db)],
    genre_id: int
) -> list[MovieListItemResponseSchema] | MessageResponseSchema:
    return await get_movies_by_genre(
        db=db,
        genre_id=genre_id
    )


@router.patch(
    "/genres/{genre_id}",
    status_code=status.HTTP_200_OK,
    response_model=GenreResponseSchema
)
async def update_genre(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserModel, Depends(require_roles(UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR))],
    genre_id: int,
    data: GenreRequestSchema
) -> GenreResponseSchema:
    return await update_genre_service(
        db=db,
        current_user=current_user,
        genre_id=genre_id,
        data=data
    )


@router.delete(
    "/genres/{genre_id}",
    status_code=status.HTTP_200_OK,
    response_model=MessageResponseSchema
)
async def delete_genre(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserModel, Depends(require_roles(UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR))],
    genre_id: int,
) -> MessageResponseSchema:
    return await delete_genre_service(
        db=db,
        current_user=current_user,
        genre_id=genre_id,
    )
