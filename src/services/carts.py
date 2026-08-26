from typing import Annotated
from fastapi import Depends, HTTPException, status
from sqlalchemy import select, delete
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
from schemas.carts import (
    CartItemResponseSchema,
    CartResponseSchema,
    UserCartResponseSchema
)
from schemas.accounts import (
    MessageResponseSchema
)


async def add_movie_to_cart(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        UserModel,
        Depends(require_roles(UserGroupEnum.USER, UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ],
    movie_id: int
) -> MessageResponseSchema:
    movie = await db.get(MovieModel, movie_id)

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Movie with id {movie_id} not found."
        )

    stmt = select(CartModel).where(
        CartModel.user_id == current_user.id
    )
    result = await db.execute(stmt)
    cart = result.scalars().first()
    try:
        if not cart:
            cart = CartModel(
                user_id=current_user.id
            )
            db.add(cart)
            await db.flush()
        stmt = select(CartItem).where(
            CartItem.cart_id == cart.id,
            CartItem.movie_id == movie.id
        )
        result = await db.execute(stmt)
        cart_item = result.scalars().first()
        if cart_item:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This movie is already in your cart."
            )
        cart_item = CartItem(
            cart_id=cart.id,
            movie_id=movie.id
        )
        db.add(cart_item)
        await db.commit()
        # TODO: Add checking if customer has already purchased this movie
        return MessageResponseSchema(
            message=f"Movie {movie.name!r} was successfully added to your cart."
        )
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while adding the movie to cart."
        ) from e


async def remove_movie_from_cart(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        UserModel,
        Depends(require_roles(UserGroupEnum.USER, UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ],
    movie_id: int
) -> MessageResponseSchema:
    movie = await db.get(MovieModel, movie_id)

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Movie with id {movie_id} not found."
        )

    stmt = select(CartModel).where(
        CartModel.user_id == current_user.id
    )
    result = await db.execute(stmt)
    cart = result.scalars().first()

    if not cart:
        return MessageResponseSchema(
            message="You have no movies in your cart!"
        )

    stmt = select(CartItem).where(
        CartItem.cart_id == cart.id,
        CartItem.movie_id == movie.id
    )
    result = await db.execute(stmt)
    cart_item = result.scalars().first()

    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"The movie {movie.name!r} is not in your cart."
        )

    try:
        await db.delete(cart_item)
        await db.commit()
        return MessageResponseSchema(
            message=f"Movie {movie.name!r} was removed from the cart."
        )
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while removing the movie from cart."
        ) from e


async def get_cart(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        UserModel,
        Depends(require_roles(UserGroupEnum.USER, UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ]
) -> CartResponseSchema | MessageResponseSchema:
    stmt = select(CartModel).where(
        CartModel.user_id == current_user.id
    ).options(
        joinedload(CartModel.cart_items)
        .joinedload(CartItem.movie)
        .joinedload(MovieModel.certification)
    )
    result = await db.execute(stmt)
    cart = result.scalars().unique().first()

    if not cart:
        return MessageResponseSchema(
            message="You have no movies in your cart!"
        )

    cart_items_list = [
        CartItemResponseSchema.model_validate(cart_item)
        for cart_item in cart.cart_items
    ]
    total_items = len(cart_items_list)
    total_price = sum(item.movie.price for item in cart.cart_items)
    if total_items <= 0:
        return MessageResponseSchema(
            message="You have no movies in your cart!"
        )
    return CartResponseSchema(
        items=cart_items_list,
        total_items=total_items,
        total_price=total_price
    )


async def clear_cart_items(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        UserModel,
        Depends(require_roles(UserGroupEnum.USER, UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ]
) -> MessageResponseSchema:
    stmt = select(CartModel).where(
        CartModel.user_id == current_user.id
    )
    result = await db.execute(stmt)
    cart = result.scalars().first()

    if not cart:
        return MessageResponseSchema(
            message="Your cart was successfully cleared."
        )
    try:
        stmt = delete(CartItem).where(
            CartItem.cart_id == cart.id
        )
        await db.execute(stmt)
        await db.commit()
        return MessageResponseSchema(
            message="Your cart was successfully cleared."
        )
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while clearing the cart."
        ) from e


async def get_cart_by_user_id(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserModel, Depends(require_roles(UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))],
    user_id: int
) -> UserCartResponseSchema | MessageResponseSchema:
    user = await db.get(UserModel, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found."
        )
    stmt = select(CartModel).options(
        joinedload(CartModel.cart_items)
        .joinedload(CartItem.movie)
        .joinedload(MovieModel.certification)
    ).where(
        CartModel.user_id == user_id
    )
    result = await db.execute(stmt)
    cart = result.scalars().unique().first()
    if not cart:
        return MessageResponseSchema(
            message=f"User {user.email!r} has no movies in the cart."
        )

    cart_items_list = [
        CartItemResponseSchema.model_validate(cart_item)
        for cart_item in cart.cart_items
    ]
    total_items = len(cart_items_list)
    total_price = sum(item.movie.price for item in cart.cart_items)

    if total_items <= 0:
        return MessageResponseSchema(
            message=f"User {user.email!r} has no movies in the cart."
        )

    return UserCartResponseSchema(
        user_email=user.email,
        items=cart_items_list,
        total_items=total_items,
        total_price=total_price
    )
