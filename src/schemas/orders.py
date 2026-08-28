from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel


from schemas.movies import MovieListItemResponseSchema

from database.models.orders import StatusOrderEnum


class OrderItemResponseSchema(BaseModel):
    id: int
    movie: MovieListItemResponseSchema
    price_at_order: Decimal

    model_config = {
        "from_attributes": True
    }


class OrderResponseSchema(BaseModel):
    id: int
    status: StatusOrderEnum
    created_at: datetime
    order_sum: Decimal
    items: list[OrderItemResponseSchema]

    model_config = {
        "from_attributes": True
    }


class OrderListItemResponseSchema(BaseModel):
    id: int
    status: StatusOrderEnum
    created_at: datetime
    order_sum: Decimal
    items_count: int


class UserOrdersResponseSchema(BaseModel):
    user_email: str
    orders: list[OrderListItemResponseSchema]
