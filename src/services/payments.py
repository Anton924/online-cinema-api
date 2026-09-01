from typing import Annotated

import stripe
from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from database import get_db
from security.dependencies import require_roles
from database.models.accounts import (
    UserModel,
    UserGroupEnum
)
from schemas.payments import (
    PaymentSessionResponseSchema
)
from database.models.orders import (
    OrderModel,
    OrderItemModel,
    StatusOrderEnum
)
from payments.interfaces import PaymentGatewayInterface
from config.dependencies import get_payment_gateway, get_settings
from config.settings import BaseAppSettings


async def create_payment_session(
    db: Annotated[AsyncSession, Depends(get_db)],
    payment_gateway: Annotated[PaymentGatewayInterface, Depends(get_payment_gateway)],
    current_user: Annotated[
        UserModel,
        Depends(require_roles(UserGroupEnum.USER, UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ],
    settings: Annotated[BaseAppSettings, Depends(get_settings)],
    order_id: int
) -> PaymentSessionResponseSchema:
    stmt = select(OrderModel).options(
        joinedload(OrderModel.payment),
        joinedload(OrderModel.order_items)
        .joinedload(OrderItemModel.movie)
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
            detail="You can pay only for your own orders!"
        )
    if order.status != StatusOrderEnum.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending orders can be paid."
        )
    if order.payment:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A payment for this order already exists."
        )
    try:
        session = await payment_gateway.create_checkout_session(
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": order_item.movie.name},
                        "unit_amount": int(order_item.price_at_order * 100)
                    },
                    "quantity": 1
                }
                for order_item in order.order_items
            ],
            metadata={
                "user_id": str(current_user.id),
                "order_id": str(order.id)
            },
            mode="payment",
            success_url=settings.STRIPE_SUCCESS_URL,
            cancel_url=settings.STRIPE_CANCEL_URL,
            client_reference_id=str(order.id)
        )
        return PaymentSessionResponseSchema(
            session_id=session.id,
            checkout_url=session.url
        )
    except stripe.error.StripeError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the payment session."
        ) from e
