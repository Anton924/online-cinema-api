from decimal import Decimal

from pydantic import BaseModel, Field

from schemas.movies import MovieListItemResponseSchema

from database.models.payments import PaymentStatus


class PaymentItemResponseSchema(BaseModel):
    id: int = Field(examples=[1])
    movie: MovieListItemResponseSchema
    price_at_payment: Decimal = Field(examples=[9.99])

    model_config = {
        "from_attributes": True
    }


class PaymentResponseSchema(BaseModel):
    id: int = Field(examples=[1])
    status: PaymentStatus = Field(examples=[PaymentStatus.SUCCESSFUL])
    external_payment_id: str = Field(examples=["pi_3Oa1b2c3D4e5F6g7H8i9J0k1"])
    order_id: int = Field(examples=[1])
    items: list[PaymentItemResponseSchema]

    model_config = {
        "from_attributes": True
    }


class PaymentListItemResponseSchema(BaseModel):
    id: int = Field(examples=[1])
    status: PaymentStatus = Field(examples=[PaymentStatus.SUCCESSFUL])
    order_id: int = Field(examples=[1])
    items_count: int = Field(examples=[2])


class PaymentAdminListItemResponseSchema(BaseModel):
    id: int = Field(examples=[1])
    status: PaymentStatus = Field(examples=[PaymentStatus.SUCCESSFUL])
    order_id: int = Field(examples=[1])
    user_email: str = Field(examples=["user@example.com"])
    items_count: int = Field(examples=[2])


class PaymentSessionResponseSchema(BaseModel):
    session_id: str = Field(examples=["cs_test_a1b2c3d4e5f6g7h8i9j0"])
    checkout_url: str = Field(examples=["https://checkout.stripe.com/c/pay/cs_test_a1b2c3d4e5f6g7h8i9j0"])
