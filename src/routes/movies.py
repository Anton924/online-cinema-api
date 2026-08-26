from decimal import Decimal
from typing import Annotated, Literal
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
    PaginatedMovieResponseSchema,
    LikeDislikeMovieSchema,
    MovieRateSchema
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
    delete_movie_service,
    add_movie_to_favorites,
    remove_movie_from_favorites,
    get_favorite_movies,
    set_movie_reaction_service,
    remove_movie_reaction_service,
    set_movie_rating_service,
    remove_movie_rating_service
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
    response_model=CertificationResponseSchema,
    responses={
        409: {
            "description": "Conflict - A certification with this name already exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "A certification with this name 'PG-13' already exists."
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while creating the certification.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while creating the certification."
                    }
                }
            },
        },
    }
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
    response_model=list[CertificationResponseSchema],
    responses={
        404: {
            "description": "Not Found - No certifications found.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "No certifications found."
                    }
                }
            },
        },
    }
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
    response_model=CertificationResponseSchema,
    responses={
        404: {
            "description": "Not Found - No certification with this id exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Certification with id 1 not found."
                    }
                }
            },
        },
    }
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
    response_model=CertificationResponseSchema,
    responses={
        404: {
            "description": "Not Found - No certification with this id exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Certification with id 1 not found."
                    }
                }
            },
        },
        409: {
            "description": "Conflict - A certification with this name already exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "A certification with this name 'PG-13' already exists."
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while updating the certification.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while updating the certification."
                    }
                }
            },
        },
    }
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
    response_model=MessageResponseSchema,
    responses={
        404: {
            "description": "Not Found - No certification with this id exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Certification with id 1 not found."
                    }
                }
            },
        },
        409: {
            "description": "Conflict - The certification is still assigned to one or more movies.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Cannot delete certification 'PG-13' - it is still assigned to one or more movies."
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while deleting the certification.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while deleting the certification."
                    }
                }
            },
        },
    }
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
    response_model=GenreResponseSchema,
    responses={
        409: {
            "description": "Conflict - A genre with this name already exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "A genre with this name 'Action' already exists."
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while creating the genre.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while creating the genre."
                    }
                }
            },
        },
    }
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
    response_model=list[GenreResponseSchema],
    responses={
        404: {
            "description": "Not Found - No genres found.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "No genres found"
                    }
                }
            },
        },
    }
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
    response_model=GenreWithMovieCountResponseSchema,
    responses={
        404: {
            "description": "Not Found - No genre with this id exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Genre with id 1 not found."
                    }
                }
            },
        },
    }
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
    response_model=list[MovieListItemResponseSchema] | MessageResponseSchema,
    responses={
        404: {
            "description": "Not Found - No genre with this id exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Genre with id 1 not found."
                    }
                }
            },
        },
    }
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
    response_model=GenreResponseSchema,
    responses={
        404: {
            "description": "Not Found - No genre with this id exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Genre with id 1 not found."
                    }
                }
            },
        },
        409: {
            "description": "Conflict - A genre with this name already exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "A genre with this name 'Action' already exists."
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while updating the genre.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while updating the genre."
                    }
                }
            },
        },
    }
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
    response_model=MessageResponseSchema,
    responses={
        404: {
            "description": "Not Found - No genre with this id exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Genre with id 1 not found."
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while deleting the genre.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while deleting the genre."
                    }
                }
            },
        },
    }
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
    response_model=StarResponseSchema,
    responses={
        409: {
            "description": "Conflict - A star with this name already exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "A star with this name 'Tom Hardy' already exists."
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while creating the star.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while creating the star."
                    }
                }
            },
        },
    }
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
    response_model=list[StarResponseSchema],
    responses={
        404: {
            "description": "Not Found - No stars found.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "No stars found."
                    }
                }
            },
        },
    }
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
    response_model=StarResponseSchema,
    responses={
        404: {
            "description": "Not Found - No star with this id exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Star with id 1 not found."
                    }
                }
            },
        },
    }
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
    response_model=StarResponseSchema,
    responses={
        404: {
            "description": "Not Found - No star with this id exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Star with id 1 not found."
                    }
                }
            },
        },
        409: {
            "description": "Conflict - A star with this name already exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "A star with this name 'Tom Hardy' already exists."
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while updating the star.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while updating the star."
                    }
                }
            },
        },
    }
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
    response_model=MessageResponseSchema,
    responses={
        404: {
            "description": "Not Found - No star with this id exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Star with id 1 not found."
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while deleting the star.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while deleting the star."
                    }
                }
            },
        },
    }
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
    response_model=DirectorResponseSchema,
    responses={
        409: {
            "description": "Conflict - A director with this name already exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "A director with this name 'Christopher Nolan' already exists."
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while creating the director.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while creating the director."
                    }
                }
            },
        },
    }
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
    response_model=list[DirectorResponseSchema],
    responses={
        404: {
            "description": "Not Found - No directors found.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "No directors found."
                    }
                }
            },
        },
    }
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
    response_model=DirectorResponseSchema,
    responses={
        404: {
            "description": "Not Found - No director with this id exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Director with id 1 not found."
                    }
                }
            },
        },
    }
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
    response_model=DirectorResponseSchema,
    responses={
        404: {
            "description": "Not Found - No director with this id exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Director with id 1 not found."
                    }
                }
            },
        },
        409: {
            "description": "Conflict - A director with this name already exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "A director with this name 'Christopher Nolan' already exists."
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while updating the director.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while updating the director."
                    }
                }
            },
        },
    }
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
    response_model=MessageResponseSchema,
    responses={
        404: {
            "description": "Not Found - No director with this id exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Director with id 1 not found."
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while deleting the director.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while deleting the director."
                    }
                }
            },
        },
    }
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
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=MovieDetailResponseSchema,
    responses={
        404: {
            "description": "Not Found - The certification, genre, star, or director id given does not exist.",
            "content": {
                "application/json": {
                    "examples": {
                        "certification_not_found": {
                            "summary": "Certification Not Found",
                            "value": {
                                "detail": "Certification with id 1 not found."
                            }
                        },
                        "genre_not_found": {
                            "summary": "Genre Not Found",
                            "value": {
                                "detail": "Genre with id 1 not found."
                            }
                        },
                        "star_not_found": {
                            "summary": "Star Not Found",
                            "value": {
                                "detail": "Star with id 1 not found."
                            }
                        },
                        "director_not_found": {
                            "summary": "Director Not Found",
                            "value": {
                                "detail": "Director with id 1 not found."
                            }
                        },
                    }
                }
            },
        },
        409: {
            "description": "Conflict - A movie with this name, year, and duration already exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "A movie with this name, year, and duration already exists."
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while creating the movie.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while creating the movie."
                    }
                }
            },
        },
    }
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
    "",
    status_code=status.HTTP_200_OK,
    response_model=PaginatedMovieResponseSchema,
)
async def list_movies(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = 1,
    per_page: int = 20,
    search: str | None = None,
    year: int | None = None,
    imdb_min: int | None = None,
    genre_id: int | None = None,
    certification_id: int | None = None,
    price_min: Decimal | None = None,
    price_max: Decimal | None = None,
    sort_by: Literal["id", "price", "year", "imdb", "votes"] = "id",
    order: Literal["asc", "desc"] = "asc"
) -> PaginatedMovieResponseSchema:
    return await get_movies(
        db=db,
        page=page,
        per_page=per_page,
        search=search,
        year=year,
        imdb_min=imdb_min,
        genre_id=genre_id,
        certification_id=certification_id,
        price_min=price_min,
        price_max=price_max,
        sort_by=sort_by,
        order=order,
    )


@router.get(
    "/favorites",
    status_code=status.HTTP_200_OK,
    response_model=PaginatedMovieResponseSchema
)
async def list_favorite_movies(
    current_user: Annotated[
        UserModel,
        Depends(require_roles(UserGroupEnum.USER, UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ],
    page: int = 1,
    per_page: int = 20,
) -> PaginatedMovieResponseSchema:
    return await get_favorite_movies(
        current_user=current_user,
        page=page,
        per_page=per_page,
    )


@router.get(
    "/{movie_id}",
    status_code=status.HTTP_200_OK,
    response_model=MovieDetailResponseSchema,
    responses={
        404: {
            "description": "Not Found - No movie with this id exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Movie with id 1 not found."
                    }
                }
            },
        },
    }
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
    "/{movie_id}",
    status_code=status.HTTP_200_OK,
    response_model=MovieDetailResponseSchema,
    responses={
        404: {
            "description": "Not Found - The movie, certification, genre, star, or director id given does not exist.",
            "content": {
                "application/json": {
                    "examples": {
                        "movie_not_found": {
                            "summary": "Movie Not Found",
                            "value": {
                                "detail": "Movie with id 1 not found."
                            }
                        },
                        "certification_not_found": {
                            "summary": "Certification Not Found",
                            "value": {
                                "detail": "Certification with id 1 not found."
                            }
                        },
                        "genre_not_found": {
                            "summary": "Genre Not Found",
                            "value": {
                                "detail": "Genre with id 1 not found."
                            }
                        },
                        "star_not_found": {
                            "summary": "Star Not Found",
                            "value": {
                                "detail": "Star with id 1 not found."
                            }
                        },
                        "director_not_found": {
                            "summary": "Director Not Found",
                            "value": {
                                "detail": "Director with id 1 not found."
                            }
                        },
                    }
                }
            },
        },
        409: {
            "description": "Conflict - A movie with this name, year, and duration already exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "A movie with this name, year, and duration already exists."
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while updating the movie.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while updating the movie."
                    }
                }
            },
        },
    }
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
    "/{movie_id}",
    status_code=status.HTTP_200_OK,
    response_model=MessageResponseSchema,
    responses={
        404: {
            "description": "Not Found - No movie with this id exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Movie with id 1 not found."
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while deleting the movie.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while deleting the movie."
                    }
                }
            },
        },
    }
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


@router.post(
    "/{movie_id}/favorites",
    status_code=status.HTTP_200_OK,
    response_model=MessageResponseSchema,
    responses={
        404: {
            "description": "Not Found - No movie with this id exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Movie with id 1 not found."
                    }
                }
            },
        },
        409: {
            "description": "Conflict - This movie is already in your favorites.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "This movie is already in your favorites."
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while adding the movie to favorites.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while adding the movie to favorites."
                    }
                }
            },
        },
    }
)
async def add_to_favorites(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        UserModel,
        Depends(require_roles(UserGroupEnum.USER, UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ],
    movie_id: int
) -> MessageResponseSchema:
    return await add_movie_to_favorites(
        db=db,
        current_user=current_user,
        movie_id=movie_id
    )


@router.delete(
    "/{movie_id}/favorites",
    status_code=status.HTTP_200_OK,
    response_model=MessageResponseSchema,
    responses={
        404: {
            "description": "Not Found - No movie with this id exists, or it is not in your favorites.",
            "content": {
                "application/json": {
                    "examples": {
                        "movie_not_found": {
                            "summary": "Movie Not Found",
                            "value": {
                                "detail": "Movie with id 1 not found."
                            }
                        },
                        "not_in_favorites": {
                            "summary": "Not In Favorites",
                            "value": {
                                "detail": "This movie is not in your favorites."
                            }
                        },
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while deleting the movie to favorites.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while deleting the movie to favorites."
                    }
                }
            },
        },
    }
)
async def remove_from_favorites(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        UserModel,
        Depends(require_roles(UserGroupEnum.USER, UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ],
    movie_id: int
) -> MessageResponseSchema:
    return await remove_movie_from_favorites(
        db=db,
        current_user=current_user,
        movie_id=movie_id
    )


@router.post(
    "/{movie_id}/like",
    status_code=status.HTTP_200_OK,
    response_model=MessageResponseSchema,
    responses={
        404: {
            "description": "Not Found - No movie with this id exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Movie with id 1 not found."
                    }
                }
            },
        },
        409: {
            "description": "Conflict - You have already reacted to this movie with the same reaction.",
            "content": {
                "application/json": {
                    "examples": {
                        "already_liked": {
                            "summary": "Already Liked",
                            "value": {
                                "detail": "The movie 'Inception' is already liked by you"
                            }
                        },
                        "already_disliked": {
                            "summary": "Already Disliked",
                            "value": {
                                "detail": "The movie 'Inception' is already disliked by you"
                            }
                        },
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while estimating the movie.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while estimating the movie."
                    }
                }
            },
        },
    }
)
async def set_movie_reaction(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        UserModel,
        Depends(require_roles(UserGroupEnum.USER, UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ],
    movie_id: int,
    like_dislike: LikeDislikeMovieSchema
) -> MessageResponseSchema:
    return await set_movie_reaction_service(
        db=db,
        current_user=current_user,
        movie_id=movie_id,
        like_dislike=like_dislike
    )


@router.delete(
    "/{movie_id}/like",
    status_code=status.HTTP_200_OK,
    response_model=MessageResponseSchema,
    responses={
        404: {
            "description": "Not Found - No movie with this id exists, or you have not reacted to it.",
            "content": {
                "application/json": {
                    "examples": {
                        "movie_not_found": {
                            "summary": "Movie Not Found",
                            "value": {
                                "detail": "Movie with id 1 not found."
                            }
                        },
                        "no_reaction": {
                            "summary": "No Reaction Found",
                            "value": {
                                "detail": "You have not reacted to the 'Inception' movie"
                            }
                        },
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while deleting your reaction to the movie.",
            "content": {
                "application/json": {
                    "examples": {
                        "delete_like_failed": {
                            "summary": "Failed To Delete Like",
                            "value": {
                                "detail": "An error occurred while deleting like to the movie."
                            }
                        },
                        "delete_dislike_failed": {
                            "summary": "Failed To Delete Dislike",
                            "value": {
                                "detail": "An error occurred while deleting dislike to the movie."
                            }
                        },
                    }
                }
            },
        },
    }
)
async def remove_movie_reaction(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        UserModel,
        Depends(require_roles(UserGroupEnum.USER, UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ],
    movie_id: int
) -> MessageResponseSchema:
    return await remove_movie_reaction_service(
        db=db,
        current_user=current_user,
        movie_id=movie_id
    )


@router.post(
    "/{movie_id}/rating",
    status_code=status.HTTP_200_OK,
    response_model=MessageResponseSchema,
    responses={
        404: {
            "description": "Not Found - No movie with this id exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Movie with id 1 not found."
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while adding score to the movie.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while adding score to the movie."
                    }
                }
            },
        },
    }
)
async def set_movie_rating(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        UserModel,
        Depends(require_roles(UserGroupEnum.USER, UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ],
    movie_id: int,
    rating: MovieRateSchema
) -> MessageResponseSchema:
    return await set_movie_rating_service(
        db=db,
        current_user=current_user,
        movie_id=movie_id,
        rating=rating
    )


@router.delete(
    "/{movie_id}/rating",
    status_code=status.HTTP_200_OK,
    response_model=MessageResponseSchema,
    responses={
        404: {
            "description": "Not Found - No movie with this id exists, or you have not rated it.",
            "content": {
                "application/json": {
                    "examples": {
                        "movie_not_found": {
                            "summary": "Movie Not Found",
                            "value": {
                                "detail": "Movie with id 1 not found."
                            }
                        },
                        "no_rating": {
                            "summary": "No Rating Found",
                            "value": {
                                "detail": "You have not rated the movie 'Inception'"
                            }
                        },
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while deleting score to the movie.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while deleting score to the movie."
                    }
                }
            },
        },
    }
)
async def remove_movie_rating(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        UserModel,
        Depends(require_roles(UserGroupEnum.USER, UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ],
    movie_id: int
) -> MessageResponseSchema:
    return await remove_movie_rating_service(
        db=db,
        current_user=current_user,
        movie_id=movie_id
    )
