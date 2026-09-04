from decimal import Decimal

from pydantic import BaseModel, Field

from schemas.movies import MovieListItemResponseSchema


class CartItemResponseSchema(BaseModel):
    id: int = Field(examples=[1])
    movie: MovieListItemResponseSchema

    model_config = {
        "from_attributes": True
    }


class CartResponseSchema(BaseModel):
    items: list[CartItemResponseSchema]
    total_items: int = Field(examples=[2])
    total_price: Decimal = Field(examples=[19.98])


class UserCartResponseSchema(BaseModel):
    user_email: str = Field(examples=["user@example.com"])
    items: list[CartItemResponseSchema]
    total_items: int = Field(examples=[2])
    total_price: Decimal = Field(examples=[19.98])
