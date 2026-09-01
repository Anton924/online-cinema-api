from decimal import Decimal

from pydantic import BaseModel

from schemas.movies import MovieListItemResponseSchema

from database.models.payments import PaymentStatus


class PaymentItemResponseSchema(BaseModel):
    id: int
    movie: MovieListItemResponseSchema
    price_at_payment: Decimal

    model_config = {
        "from_attributes": True
    }


class PaymentResponseSchema(BaseModel):
    id: int
    status: PaymentStatus
    external_payment_id: str
    order_id: int
    items: list[PaymentItemResponseSchema]

    model_config = {
        "from_attributes": True
    }


class PaymentListItemResponseSchema(BaseModel):
    id: int
    status: PaymentStatus
    order_id: int
    items_count: int


class PaymentAdminListItemResponseSchema(BaseModel):
    id: int
    status: PaymentStatus
    order_id: int
    user_email: str
    items_count: int


class PaymentSessionResponseSchema(BaseModel):
    session_id: str
    checkout_url: str
