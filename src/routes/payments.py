from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, status, Query, Request
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from security.dependencies import require_roles
from database.models.accounts import (
    UserModel,
    UserGroupEnum
)
from database.models.payments import (
    PaymentStatus
)
from services.payments import (
    create_payment_session,
    handle_stripe_webhook,
    get_user_payments,
    get_payment_by_id,
    get_all_payments,
    refund_payment_service
)
from schemas.payments import (
    PaymentSessionResponseSchema,
    PaymentListItemResponseSchema,
    PaymentResponseSchema,
    PaymentAdminListItemResponseSchema
)
from schemas.accounts import (
    MessageResponseSchema
)
from payments.interfaces import PaymentGatewayInterface
from config.dependencies import get_payment_gateway, get_settings
from config.settings import BaseAppSettings

router = APIRouter()


@router.get(
    "/admin",
    status_code=status.HTTP_200_OK,
    response_model=list[PaymentAdminListItemResponseSchema]
)
async def list_all_payments(
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
    return await get_all_payments(
        db=db,
        current_user=current_user,
        payment_status=payment_status,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to
    )


@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
    response_model=MessageResponseSchema,
    responses={
        400: {
            "description": "Bad Request - The Stripe webhook signature could not be verified.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid Stripe signature."
                    }
                }
            },
        },
    }
)
async def stripe_webhook(
    db: Annotated[AsyncSession, Depends(get_db)],
    payment_gateway: Annotated[PaymentGatewayInterface, Depends(get_payment_gateway)],
    request: Request
) -> MessageResponseSchema:
    return await handle_stripe_webhook(
        db=db,
        payment_gateway=payment_gateway,
        request=request
    )


@router.get("/success")
async def payment_success(
    session_id: str = Query(...)
) -> dict:
    return {
        "status": "success",
        "session_id": session_id
    }


@router.get("/cancel")
async def payment_cancel() -> dict:
    return {
        "status": "cancelled",
    }


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=list[PaymentListItemResponseSchema]
)
async def list_payments(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        UserModel,
        Depends(require_roles(UserGroupEnum.USER, UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ],
) -> list[PaymentListItemResponseSchema]:
    return await get_user_payments(
        db=db,
        current_user=current_user
    )


@router.post(
    "/{order_id}",
    status_code=status.HTTP_200_OK,
    response_model=PaymentSessionResponseSchema,
    responses={
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
        403: {
            "description": "Forbidden - You can pay only for your own orders.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "You can pay only for your own orders!"
                    }
                }
            },
        },
        409: {
            "description": "Conflict - The order is not pending, or already has a payment.",
            "content": {
                "application/json": {
                    "examples": {
                        "not_pending": {
                            "summary": "Order Not Pending",
                            "value": {
                                "detail": "Only pending orders can be paid."
                            }
                        },
                        "already_has_payment": {
                            "summary": "Payment Already Exists",
                            "value": {
                                "detail": "A payment for this order already exists."
                            }
                        },
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while creating the payment session.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while creating the payment session."
                    }
                }
            },
        },
    }
)
async def create_payment(
    db: Annotated[AsyncSession, Depends(get_db)],
    payment_gateway: Annotated[PaymentGatewayInterface, Depends(get_payment_gateway)],
    current_user: Annotated[
        UserModel,
        Depends(require_roles(UserGroupEnum.USER, UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ],
    settings: Annotated[BaseAppSettings, Depends(get_settings)],
    order_id: int
) -> PaymentSessionResponseSchema:
    return await create_payment_session(
        db=db,
        payment_gateway=payment_gateway,
        current_user=current_user,
        settings=settings,
        order_id=order_id
    )


@router.get(
    "/{payment_id}",
    status_code=status.HTTP_200_OK,
    response_model=PaymentResponseSchema,
    responses={
        404: {
            "description": "Not Found - No payment with this id exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Payment with id 1 not found."
                    }
                }
            },
        },
        403: {
            "description": "Forbidden - You can view only your own payments.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "You can view only your own payments!"
                    }
                }
            },
        },
    }
)
async def view_payment(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        UserModel,
        Depends(require_roles(UserGroupEnum.USER, UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ],
    payment_id: int
) -> PaymentResponseSchema:
    return await get_payment_by_id(
        db=db,
        current_user=current_user,
        payment_id=payment_id
    )


@router.post(
    "/{payment_id}/refund",
    status_code=status.HTTP_200_OK,
    response_model=MessageResponseSchema,
    responses={
        404: {
            "description": "Not Found - No payment with this id exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Payment with id 1 not found."
                    }
                }
            },
        },
        409: {
            "description": "Conflict - Only successful payments can be refunded.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Only successful payments can be refunded."
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while processing the refund.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while processing the refund."
                    }
                }
            },
        },
    }
)
async def refund_payment(
    db: Annotated[AsyncSession, Depends(get_db)],
    payment_gateway: Annotated[PaymentGatewayInterface, Depends(get_payment_gateway)],
    current_user: Annotated[
        UserModel,
        Depends(require_roles(UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ],
    payment_id: int,
    amount: Decimal | None = None
) -> MessageResponseSchema:
    return await refund_payment_service(
        db=db,
        payment_gateway=payment_gateway,
        current_user=current_user,
        payment_id=payment_id,
        amount=amount
    )
