from fastapi import APIRouter, Depends, status
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from security.dependencies import require_roles
from database.models.accounts import (
    UserModel,
    UserGroupEnum
)
from services.carts import (
    add_movie_to_cart,
    remove_movie_from_cart,
    get_cart,
    clear_cart_items,
    get_cart_by_user_id
)
from schemas.carts import (
    CartResponseSchema,
    UserCartResponseSchema
)
from schemas.accounts import (
    MessageResponseSchema
)


router = APIRouter()


@router.post(
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
        409: {
            "description": "Conflict - This movie is already in your cart.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "This movie is already in your cart."
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while adding the movie to cart.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while adding the movie to cart."
                    }
                }
            },
        },
    }
)
async def add_to_cart(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        UserModel,
        Depends(require_roles(UserGroupEnum.USER, UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ],
    movie_id: int
) -> MessageResponseSchema:
    return await add_movie_to_cart(
        db=db,
        current_user=current_user,
        movie_id=movie_id
    )


@router.delete(
    "/{movie_id}",
    status_code=status.HTTP_200_OK,
    response_model=MessageResponseSchema,
    responses={
        404: {
            "description": "Not Found - No movie with this id exists, or it is not in your cart.",
            "content": {
                "application/json": {
                    "examples": {
                        "movie_not_found": {
                            "summary": "Movie Not Found",
                            "value": {
                                "detail": "Movie with id 1 not found."
                            }
                        },
                        "not_in_cart": {
                            "summary": "Not In Cart",
                            "value": {
                                "detail": "The movie 'Inception' is not in your cart."
                            }
                        },
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while removing the movie from cart.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while removing the movie from cart."
                    }
                }
            },
        },
    }
)
async def remove_from_cart(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        UserModel,
        Depends(require_roles(UserGroupEnum.USER, UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ],
    movie_id: int
) -> MessageResponseSchema:
    return await remove_movie_from_cart(
        db=db,
        current_user=current_user,
        movie_id=movie_id
    )


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=CartResponseSchema | MessageResponseSchema
)
async def view_cart(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        UserModel,
        Depends(require_roles(UserGroupEnum.USER, UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ]
) -> CartResponseSchema | MessageResponseSchema:
    return await get_cart(
        db=db,
        current_user=current_user
    )


@router.delete(
    "",
    status_code=status.HTTP_200_OK,
    response_model=MessageResponseSchema,
    responses={
        500: {
            "description": "Internal Server Error - An error occurred while clearing the cart.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while clearing the cart."
                    }
                }
            },
        },
    }
)
async def clear_cart(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        UserModel,
        Depends(require_roles(UserGroupEnum.USER, UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ]
) -> MessageResponseSchema:
    return await clear_cart_items(
        db=db,
        current_user=current_user
    )


@router.get(
    "/users/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=MessageResponseSchema | UserCartResponseSchema,
    responses={
        404: {
            "description": "Not Found - No user with this id exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "User with id 1 not found."
                    }
                }
            },
        },
    }
)
async def view_user_cart(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserModel, Depends(require_roles(UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))],
    user_id: int
) -> MessageResponseSchema | UserCartResponseSchema:
    return await get_cart_by_user_id(
        db=db,
        current_user=current_user,
        user_id=user_id
    )
