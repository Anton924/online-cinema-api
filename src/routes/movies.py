from typing import Annotated
from fastapi import APIRouter, Depends, status
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
    delete_genre_service,
    create_star_service,
    get_stars,
    get_star_by_id,
    update_star_service,
    delete_star_service,
    create_director_service,
    get_directors,
    get_director_by_id,
    update_director_service,
    delete_director_service,
    create_movie_service,
    get_movies,
    get_movie_by_id,
    update_movie_service,
    delete_movie_service
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


@router.post(
    "/stars",
    status_code=status.HTTP_201_CREATED,
    response_model=StarResponseSchema
)
async def create_star(
    db: Annotated[AsyncSession, Depends(get_db)],
    star_data: StarRequestSchema,
    current_user: Annotated[UserModel, Depends(require_roles(UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR))]
) -> StarResponseSchema:
    return await create_star_service(
        db=db,
        star_data=star_data,
        current_user=current_user
    )


@router.get(
    "/stars",
    status_code=status.HTTP_200_OK,
    response_model=list[StarResponseSchema]
)
async def list_stars(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> list[StarResponseSchema]:
    return await get_stars(
        db=db
    )


@router.get(
    "/stars/{star_id}",
    status_code=status.HTTP_200_OK,
    response_model=StarResponseSchema
)
async def get_star(
    db: Annotated[AsyncSession, Depends(get_db)],
    star_id: int
) -> StarResponseSchema:
    return await get_star_by_id(
        db=db,
        star_id=star_id
    )


@router.patch(
    "/stars/{star_id}",
    status_code=status.HTTP_200_OK,
    response_model=StarResponseSchema
)
async def update_star(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserModel, Depends(require_roles(UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR))],
    star_id: int,
    data: StarRequestSchema
) -> StarResponseSchema:
    return await update_star_service(
        db=db,
        current_user=current_user,
        star_id=star_id,
        data=data
    )


@router.delete(
    "/stars/{star_id}",
    status_code=status.HTTP_200_OK,
    response_model=MessageResponseSchema
)
async def delete_star(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserModel, Depends(require_roles(UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR))],
    star_id: int,
) -> MessageResponseSchema:
    return await delete_star_service(
        db=db,
        current_user=current_user,
        star_id=star_id,
    )


@router.post(
    "/directors",
    status_code=status.HTTP_201_CREATED,
    response_model=DirectorResponseSchema
)
async def create_director(
    db: Annotated[AsyncSession, Depends(get_db)],
    director_data: DirectorRequestSchema,
    current_user: Annotated[UserModel, Depends(require_roles(UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR))]
) -> DirectorResponseSchema:
    return await create_director_service(
        db=db,
        director_data=director_data,
        current_user=current_user
    )


@router.get(
    "/directors",
    status_code=status.HTTP_200_OK,
    response_model=list[DirectorResponseSchema]
)
async def list_directors(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> list[DirectorResponseSchema]:
    return await get_directors(
        db=db
    )


@router.get(
    "/directors/{director_id}",
    status_code=status.HTTP_200_OK,
    response_model=DirectorResponseSchema
)
async def get_director(
    db: Annotated[AsyncSession, Depends(get_db)],
    director_id: int
) -> DirectorResponseSchema:
    return await get_director_by_id(
        db=db,
        director_id=director_id
    )


@router.patch(
    "/directors/{director_id}",
    status_code=status.HTTP_200_OK,
    response_model=DirectorResponseSchema
)
async def update_director(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserModel, Depends(require_roles(UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR))],
    director_id: int,
    data: DirectorRequestSchema
) -> DirectorResponseSchema:
    return await update_director_service(
        db=db,
        current_user=current_user,
        director_id=director_id,
        data=data
    )


@router.delete(
    "/directors/{director_id}",
    status_code=status.HTTP_200_OK,
    response_model=MessageResponseSchema
)
async def delete_director(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserModel, Depends(require_roles(UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR))],
    director_id: int,
) -> MessageResponseSchema:
    return await delete_director_service(
        db=db,
        current_user=current_user,
        director_id=director_id,
    )


@router.post(
    "/movies",
    status_code=status.HTTP_201_CREATED,
    response_model=MovieDetailResponseSchema,
)
async def create_movie(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserModel, Depends(require_roles(UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR))],
    movie_data: MovieCreateRequestSchema
) -> MovieDetailResponseSchema:
    return await create_movie_service(
        db=db,
        current_user=current_user,
        movie_data=movie_data
    )


@router.get(
    "/movies",
    status_code=status.HTTP_200_OK,
    response_model=PaginatedMovieResponseSchema,
)
async def list_movies(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = 1,
    per_page: int = 20
) -> PaginatedMovieResponseSchema:
    return await get_movies(
        db=db,
        page=page,
        per_page=per_page
    )


@router.get(
    "/movies/{movie_id}",
    status_code=status.HTTP_200_OK,
    response_model=MovieDetailResponseSchema,
)
async def get_movie(
    db: Annotated[AsyncSession, Depends(get_db)],
    movie_id: int,
) -> MovieDetailResponseSchema:
    return await get_movie_by_id(
        db=db,
        movie_id=movie_id,
    )


@router.patch(
    "/movies/{movie_id}",
    status_code=status.HTTP_200_OK,
    response_model=MovieDetailResponseSchema,
)
async def update_movie(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserModel, Depends(require_roles(UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR))],
    movie_id: int,
    update_data: MovieUpdateRequestSchema
) -> MovieDetailResponseSchema:
    return await update_movie_service(
        db=db,
        current_user=current_user,
        movie_id=movie_id,
        update_data=update_data
    )


@router.delete(
    "/movies/{movie_id}",
    status_code=status.HTTP_200_OK,
    response_model=MessageResponseSchema,
)
async def delete_movie(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserModel, Depends(require_roles(UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR))],
    movie_id: int,
) -> MessageResponseSchema:
    return await delete_movie_service(
        db=db,
        current_user=current_user,
        movie_id=movie_id,
    )
