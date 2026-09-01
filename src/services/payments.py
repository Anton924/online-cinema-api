from datetime import datetime, date, time
from typing import Annotated

import stripe
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from database import get_db
from security.dependencies import require_roles
from database.models.accounts import (
    UserModel,
    UserGroupEnum
)
from database.models.movies import (
    MovieModel
)
from database.models.payments import (
    PaymentModel,
    PaymentItemModel,
    PaymentStatus
)
from schemas.accounts import (
    MessageResponseSchema
)
from schemas.payments import (
    PaymentSessionResponseSchema,
    PaymentListItemResponseSchema,
    PaymentItemResponseSchema,
    PaymentResponseSchema,
    PaymentAdminListItemResponseSchema
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


async def handle_stripe_webhook(
        db: Annotated[AsyncSession, Depends(get_db)],
        payment_gateway: Annotated[PaymentGatewayInterface, Depends(get_payment_gateway)],
        request: Request
) -> MessageResponseSchema:
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    try:
        event = await payment_gateway.verify_webhook_event(payload, sig_header)
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Stripe signature."
        ) from e
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        metadata = session["metadata"].to_dict()
        if session["payment_status"] == "paid":
            try:
                existing_payment = await db.scalar(
                    select(PaymentModel).where(PaymentModel.external_payment_id == session["id"])
                )
                if existing_payment:
                    return MessageResponseSchema(
                        message="Event already processed."
                    )
                new_payment = PaymentModel(
                    order_id=int(metadata.get("order_id")),
                    user_id=int(metadata.get("user_id")),
                    status=PaymentStatus.SUCCESSFUL,
                    external_payment_id=session["id"],
                    payment_intent_id=session["payment_intent"]
                )
                db.add(new_payment)
                await db.flush()
                stmt = select(OrderModel).options(
                    joinedload(OrderModel.order_items)
                ).where(
                    OrderModel.id == int(metadata.get("order_id"))
                )
                result = await db.execute(stmt)
                order = result.scalars().unique().first()
                order.status = StatusOrderEnum.PAID

                for order_item in order.order_items:
                    new_payment_item = PaymentItemModel(
                        payment_id=new_payment.id,
                        order_item_id=order_item.id,
                        price_at_payment=order_item.price_at_order
                    )
                    db.add(new_payment_item)
                    await db.flush()
                await db.commit()
                return MessageResponseSchema(
                    message=f"Payment for order #{order.id} was successfully processed"
                )
            except SQLAlchemyError as e:
                await db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="An error occurred while processing the payment"
                ) from e
        else:
            return MessageResponseSchema(
                message="Payment is still processing."
            )
    return MessageResponseSchema(
        message="Event ignored."
    )


async def get_user_payments(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        UserModel,
        Depends(require_roles(UserGroupEnum.USER, UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ]
) -> list[PaymentListItemResponseSchema]:
    stmt = select(PaymentModel).options(
        selectinload(PaymentModel.payment_items)
    ).where(
        PaymentModel.user_id == current_user.id
    )
    result = await db.execute(stmt)
    payments = result.scalars().all()

    payments_list = []

    for payment in payments:
        payments_list.append(
            PaymentListItemResponseSchema(
                id=payment.id,
                status=payment.status,
                order_id=payment.order_id,
                items_count=len(payment.payment_items)
            )
        )

    return payments_list


async def get_payment_by_id(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        UserModel,
        Depends(require_roles(UserGroupEnum.USER, UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ],
    payment_id: int
) -> PaymentResponseSchema:
    stmt = select(PaymentModel).options(
        selectinload(PaymentModel.payment_items)
        .joinedload(PaymentItemModel.order_item)
        .joinedload(OrderItemModel.movie)
        .joinedload(MovieModel.certification)
    ).where(
        PaymentModel.id == payment_id
    )
    result = await db.execute(stmt)
    payment = result.scalars().first()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment with id {payment_id} not found."
        )

    if payment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can view only your own payments!"
        )

    payments_items_list = [
        PaymentItemResponseSchema(
            id=payment_item.id,
            movie=payment_item.order_item.movie,
            price_at_payment=payment_item.price_at_payment
        )
        for payment_item in payment.payment_items
    ]

    return PaymentResponseSchema(
        id=payment.id,
        status=payment.status,
        external_payment_id=payment.external_payment_id,
        order_id=payment.order_id,
        items=payments_items_list
    )


async def get_all_payments(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        UserModel,
        Depends(require_roles(UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ],
    payment_status: PaymentStatus | None = None,
    user_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[PaymentAdminListItemResponseSchema]:
    stmt = select(PaymentModel).options(
        joinedload(PaymentModel.user),
        selectinload(PaymentModel.payment_items)
    )
    if payment_status is not None:
        stmt = stmt.where(
            PaymentModel.status == payment_status
        )
    if user_id is not None:
        stmt = stmt.where(
            PaymentModel.user_id == user_id
        )
    if date_from is not None:
        stmt = stmt.where(
            PaymentModel.created_at >= date_from
        )
    if date_to is not None:
        stmt = stmt.where(
            PaymentModel.created_at <= datetime.combine(date_to, time.max)
        )

    result = await db.execute(stmt)
    payments = result.scalars().unique().all()
    payments_list = [
        PaymentAdminListItemResponseSchema(
            id=payment.id,
            status=payment.status,
            order_id=payment.order_id,
            user_email=payment.user.email,
            items_count=len(payment.payment_items)
        )
        for payment in payments
    ]

    return payments_list
