from fastapi import APIRouter, Depends, status
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from security.dependencies import require_roles
from database.models.accounts import (
    UserModel,
    UserGroupEnum
)
from services.payments import (
    create_payment_session
)
from schemas.payments import (
    PaymentSessionResponseSchema
)
from payments.interfaces import PaymentGatewayInterface
from config.dependencies import get_payment_gateway, get_settings
from config.settings import BaseAppSettings

router = APIRouter()


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
