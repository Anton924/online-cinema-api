from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


from schemas.movies import MovieListItemResponseSchema

from database.models.orders import StatusOrderEnum


class OrderItemResponseSchema(BaseModel):
    id: int = Field(examples=[1])
    movie: MovieListItemResponseSchema
    price_at_order: Decimal = Field(examples=[9.99])

    model_config = {
        "from_attributes": True
    }


class OrderResponseSchema(BaseModel):
    id: int = Field(examples=[1])
    status: StatusOrderEnum = Field(examples=[StatusOrderEnum.PENDING])
    created_at: datetime = Field(examples=["2024-01-01T12:00:00"])
    order_sum: Decimal = Field(examples=[19.98])
    items: list[OrderItemResponseSchema]

    model_config = {
        "from_attributes": True
    }


class OrderListItemResponseSchema(BaseModel):
    id: int = Field(examples=[1])
    status: StatusOrderEnum = Field(examples=[StatusOrderEnum.PENDING])
    created_at: datetime = Field(examples=["2024-01-01T12:00:00"])
    order_sum: Decimal = Field(examples=[19.98])
    items_count: int = Field(examples=[2])


class UserOrdersResponseSchema(BaseModel):
    user_email: str = Field(examples=["user@example.com"])
    orders: list[OrderListItemResponseSchema]
