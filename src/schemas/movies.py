from uuid import UUID
from decimal import Decimal

from pydantic import BaseModel, Field


class CertificationRequestSchema(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class CertificationResponseSchema(BaseModel):
    id: int
    name: str

    model_config = {
        "from_attributes": True
    }


class GenreRequestSchema(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class GenreResponseSchema(BaseModel):
    id: int
    name: str

    model_config = {
        "from_attributes": True
    }


class GenreWithMovieCountResponseSchema(BaseModel):
    id: int
    name: str
    movie_count: int


class MovieListItemResponseSchema(BaseModel):
    id: int
    uuid: UUID
    name: str
    year: int
    time: int
    imdb: float
    price: Decimal
    certification: CertificationResponseSchema

    model_config = {
        "from_attributes": True
    }
