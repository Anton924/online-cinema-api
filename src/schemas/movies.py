from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from database.models.movies import LikeDislikeEnum


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


class StarRequestSchema(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class StarResponseSchema(BaseModel):
    id: int
    name: str

    model_config = {
        "from_attributes": True
    }


class DirectorRequestSchema(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class DirectorResponseSchema(BaseModel):
    id: int
    name: str

    model_config = {
        "from_attributes": True
    }


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


class MovieCreateRequestSchema(BaseModel):
    name: str = Field(max_length=250)
    year: int
    time: int = Field(gt=0)
    imdb: float = Field(ge=0, le=10)
    votes: int = Field(ge=0)
    meta_score: float | None = Field(ge=0, le=100, default=None)
    gross: float | None = Field(ge=0, default=None)
    description: str = Field(min_length=1)
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    certification_id: int
    genre_ids_or_names: list[int | str]
    director_ids_or_names: list[int | str]
    star_ids_or_names: list[int | str]

    @field_validator("year")
    @classmethod
    def validate_year(cls, value: int) -> int:
        current_year = datetime.today().year
        if not (1888 <= value <= current_year + 5):
            raise ValueError(f"Year must be between 1888 and {current_year}.")
        return value


class MovieUpdateRequestSchema(BaseModel):
    name: str | None = Field(max_length=250, default=None)
    year: int | None = None
    time: int | None = Field(gt=0, default=None)
    imdb: float | None = Field(ge=0, le=10, default=None)
    votes: int | None = Field(ge=0, default=None)
    meta_score: float | None = Field(ge=0, le=100, default=None)
    gross: float | None = Field(ge=0, default=None)
    description: str | None = Field(min_length=1, default=None)
    price: Decimal | None = Field(gt=0, max_digits=10, decimal_places=2, default=None)
    certification_id: int | None = None
    genre_ids_or_names: list[int | str] | None = None
    director_ids_or_names: list[int | str] | None = None
    star_ids_or_names: list[int | str] | None = None

    @field_validator("year")
    @classmethod
    def validate_year(cls, value: int | None) -> int | None:
        if value is not None:
            current_year = datetime.today().year
            if not (1888 <= value <= current_year + 5):
                raise ValueError(f"Year must be between 1888 and {current_year}.")
        return value


class MovieDetailResponseSchema(BaseModel):
    id: int
    uuid: UUID
    name: str
    year: int
    time: int
    imdb: float
    price: Decimal
    votes: int
    meta_score: float | None
    gross: float | None
    description: str
    genres: list[GenreResponseSchema]
    stars: list[StarResponseSchema]
    directors: list[DirectorResponseSchema]
    certification: CertificationResponseSchema

    model_config = {
        "from_attributes": True
    }


class PaginatedMovieResponseSchema(BaseModel):
    items: list[MovieListItemResponseSchema]
    total: int
    page: int
    per_page: int
    total_pages: int


class LikeDislikeMovieSchema(BaseModel):
    like_dislike: LikeDislikeEnum = LikeDislikeEnum.LIKE


class MovieRateSchema(BaseModel):
    score: int = Field(ge=1, le=10)


class MovieCommentSchema(BaseModel):
    comment : str = Field(min_length=1)
    parent_id: int | None = Field(default=None, examples=[None])


class MovieCommentListItemResponseSchema(BaseModel):
    id: int
    user: str
    parent_id: int | None = Field(default=None, examples=[None])
    comment: str


class MovieCommentResponseSchema(BaseModel):
    movie_name: str
    comments: list[MovieCommentListItemResponseSchema] | None


class MovieCommentUpdateSchema(BaseModel):
    comment: str = Field(min_length=1)
