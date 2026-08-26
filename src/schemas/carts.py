from decimal import Decimal

from pydantic import BaseModel

from schemas.movies import MovieListItemResponseSchema


class CartItemResponseSchema(BaseModel):
    id: int
    movie: MovieListItemResponseSchema

    model_config = {
        "from_attributes": True
    }


class CartResponseSchema(BaseModel):
    items: list[CartItemResponseSchema]
    total_items: int
    total_price: Decimal


class UserCartResponseSchema(BaseModel):
    user_email: str
    items: list[CartItemResponseSchema]
    total_items: int
    total_price: Decimal
