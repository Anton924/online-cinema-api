from fastapi import APIRouter, Depends, status
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from security.dependencies import require_roles
from database.models.accounts import (
    UserModel,
    UserGroupEnum
)
from services.orders import (
    create_order_from_cart,
    get_user_orders,
    get_order_by_id,
    cancel_order_service,
    get_orders_by_user_id
)
from schemas.orders import (
    OrderResponseSchema,
    OrderListItemResponseSchema,
    UserOrdersResponseSchema
)
from schemas.accounts import (
    MessageResponseSchema
)


router = APIRouter()


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=OrderResponseSchema,
    responses={
        404: {
            "description": "Not Found - Your cart is empty.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Your cart is empty."
                    }
                }
            },
        },
        409: {
            "description": "Conflict - One of the movies in your cart has already been purchased.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Movie 'Inception' has already been purchased."
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while creating the order.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while creating the order."
                    }
                }
            },
        },
    }
)
async def create_order(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        UserModel,
        Depends(require_roles(UserGroupEnum.USER, UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ]
) -> OrderResponseSchema:
    return await create_order_from_cart(
        db=db,
        current_user=current_user
    )


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=list[OrderListItemResponseSchema]
)
async def list_orders(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        UserModel,
        Depends(require_roles(UserGroupEnum.USER, UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ]
) -> list[OrderListItemResponseSchema]:
    return await get_user_orders(
        db=db,
        current_user=current_user
    )


@router.get(
    "/{order_id}",
    status_code=status.HTTP_200_OK,
    response_model=OrderResponseSchema,
    responses={
        403: {
            "description": "Forbidden - You can only view your own orders.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "You can view only your own orders!"
                    }
                }
            },
        },
        404: {
            "description": "Not Found - No order with this id exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Order with id 1 not found."
                    }
                }
            },
        },
    }
)
async def view_order(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        UserModel,
        Depends(require_roles(UserGroupEnum.USER, UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ],
    order_id: int
) -> OrderResponseSchema:
    return await get_order_by_id(
        db=db,
        current_user=current_user,
        order_id=order_id
    )


@router.post(
    "/{order_id}/cancel",
    status_code=status.HTTP_200_OK,
    response_model=MessageResponseSchema,
    responses={
        403: {
            "description": "Forbidden - You can only cancel your own orders.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "You can cancel only your own orders!"
                    }
                }
            },
        },
        404: {
            "description": "Not Found - No order with this id exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Order with id 1 not found."
                    }
                }
            },
        },
        409: {
            "description": "Conflict - Only pending orders can be canceled.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Only pending orders can be canceled."
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while canceling the order.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while canceling the order."
                    }
                }
            },
        },
    }
)
async def cancel_order(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        UserModel,
        Depends(require_roles(UserGroupEnum.USER, UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ],
    order_id: int
) -> MessageResponseSchema:
    return await cancel_order_service(
        db=db,
        current_user=current_user,
        order_id=order_id
    )


@router.get(
    "/users/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=UserOrdersResponseSchema,
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
async def view_user_orders(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        UserModel,
        Depends(require_roles(UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ],
    user_id: int
) -> UserOrdersResponseSchema:
    return await get_orders_by_user_id(
        db=db,
        current_user=current_user,
        user_id=user_id
    )
