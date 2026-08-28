from typing import Annotated
from fastapi import Depends, HTTPException, status
from sqlalchemy import select, delete, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from database import get_db
from security.dependencies import require_roles
from database.models.accounts import (
    UserModel,
    UserGroupEnum
)
from database.models.movies import (
    MovieModel
)
from database.models.carts import (
    CartModel,
    CartItem
)
from schemas.orders import (
    OrderItemResponseSchema,
    OrderResponseSchema,
    OrderListItemResponseSchema,
    UserOrdersResponseSchema
)
from schemas.accounts import (
    MessageResponseSchema
)
from database.models.orders import (
    OrderModel,
    OrderItemModel,
    StatusOrderEnum
)


async def create_order_from_cart(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        UserModel,
        Depends(require_roles(UserGroupEnum.USER, UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ]
) -> OrderResponseSchema:
    stmt = select(CartModel).options(
        joinedload(CartModel.cart_items)
        .joinedload(CartItem.movie)
        .joinedload(MovieModel.certification)
    ).where(
        CartModel.user_id == current_user.id
    )
    result = await db.execute(stmt)
    cart = result.scalars().unique().first()

    if not cart or not cart.cart_items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Your cart is empty."
        )
    try:
        order = OrderModel(
            user_id=current_user.id,
            status=StatusOrderEnum.PENDING,
            order_sum=0
        )
        db.add(order)
        await db.flush()
        order_items = []
        order_sum = 0
        for cart_item in cart.cart_items:
            stmt = select(OrderModel).join(
                OrderModel.order_items
            ).where(
                OrderModel.user_id == current_user.id,
                OrderItemModel.movie_id == cart_item.movie_id,
                or_(
                    OrderModel.status == StatusOrderEnum.PAID,
                    OrderModel.status == StatusOrderEnum.PENDING
                )
            )
            result = await db.execute(stmt)
            is_purchased = result.scalars().first()
            if is_purchased:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Movie {cart_item.movie.name!r} has already been purchased."
                )
            order_item = OrderItemModel(
                order_id=order.id,
                movie=cart_item.movie,
                price_at_order=cart_item.movie.price
            )
            db.add(order_item)
            await db.flush()
            order_items.append(OrderItemResponseSchema.model_validate(order_item))
            order_sum += order_item.price_at_order
        order.order_sum = order_sum
        stmt = delete(CartItem).where(
            CartItem.cart_id == cart.id
        )
        await db.execute(stmt)
        await db.commit()
        return OrderResponseSchema(
            id=order.id,
            status=order.status,
            created_at=order.created_at,
            order_sum=order.order_sum,
            items=order_items
        )
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the order."
        ) from e


async def get_user_orders(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        UserModel,
        Depends(require_roles(UserGroupEnum.USER, UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ]
) -> list[OrderListItemResponseSchema]:
    stmt = select(OrderModel).options(
        joinedload(OrderModel.order_items)
    ).where(
        OrderModel.user_id == current_user.id
    )
    result = await db.execute(stmt)
    orders = result.scalars().unique()
    orders_list = []
    for order in orders:
        items_count = len(order.order_items)
        orders_list.append(OrderListItemResponseSchema(
            id=order.id,
            status=order.status,
            created_at=order.created_at,
            order_sum=order.order_sum,
            items_count=items_count
        ))

    return orders_list


async def get_order_by_id(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        UserModel,
        Depends(require_roles(UserGroupEnum.USER, UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ],
    order_id: int
) -> OrderResponseSchema:
    stmt = select(OrderModel).options(
        joinedload(OrderModel.order_items)
        .joinedload(OrderItemModel.movie)
        .joinedload(MovieModel.certification)
    ).where(
        OrderModel.id == order_id
    )
    result = await db.execute(stmt)
    order = result.scalars().unique().first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with id {order_id} not found."
        )

    if order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can view only your own orders!"
        )

    order_items_list = [
        OrderItemResponseSchema.model_validate(order_item)
        for order_item in order.order_items
    ]

    return OrderResponseSchema(
        id=order.id,
        status=order.status,
        created_at=order.created_at,
        order_sum=order.order_sum,
        items=order_items_list
    )


async def cancel_order_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        UserModel,
        Depends(require_roles(UserGroupEnum.USER, UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ],
    order_id: int
) -> MessageResponseSchema:
    order = await db.get(OrderModel, order_id)

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with id {order_id} not found."
        )

    if order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can cancel only your own orders!"
        )
    if order.status != StatusOrderEnum.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending orders can be canceled."
        )
    try:
        order.status = StatusOrderEnum.CANCELED
        await db.commit()
        return MessageResponseSchema(
            message=f"Order #{order.id} was successfully canceled."
        )
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while canceling the order."
        ) from e


async def get_orders_by_user_id(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        UserModel,
        Depends(require_roles(UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ],
    user_id: int
) -> UserOrdersResponseSchema:
    user = await db.get(UserModel, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found."
        )

    stmt = select(OrderModel).options(
        joinedload(OrderModel.order_items)
    ).where(
        OrderModel.user_id == user_id
    )
    result = await db.execute(stmt)
    orders = result.scalars().unique().all()

    orders_list = []

    for order in orders:
        items_count = len(order.order_items)
        orders_list.append(OrderListItemResponseSchema(
            id=order.id,
            status=order.status,
            created_at=order.created_at,
            order_sum=order.order_sum,
            items_count=items_count
        ))

    return UserOrdersResponseSchema(
        user_email=user.email,
        orders=orders_list
    )
