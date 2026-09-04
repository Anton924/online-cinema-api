from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from database.models.movies import LikeDislikeEnum


class CertificationRequestSchema(BaseModel):
    name: str = Field(min_length=1, max_length=100, examples=["PG-13"])


class CertificationResponseSchema(BaseModel):
    id: int = Field(examples=[1])
    name: str = Field(examples=["PG-13"])

    model_config = {
        "from_attributes": True
    }


class GenreRequestSchema(BaseModel):
    name: str = Field(min_length=1, max_length=100, examples=["Action"])


class GenreResponseSchema(BaseModel):
    id: int = Field(examples=[1])
    name: str = Field(examples=["Action"])

    model_config = {
        "from_attributes": True
    }


class GenreWithMovieCountResponseSchema(BaseModel):
    id: int = Field(examples=[1])
    name: str = Field(examples=["Action"])
    movie_count: int = Field(examples=[42])


class StarRequestSchema(BaseModel):
    name: str = Field(min_length=1, max_length=100, examples=["Tom Hardy"])


class StarResponseSchema(BaseModel):
    id: int = Field(examples=[1])
    name: str = Field(examples=["Tom Hardy"])

    model_config = {
        "from_attributes": True
    }


class DirectorRequestSchema(BaseModel):
    name: str = Field(min_length=1, max_length=100, examples=["Christopher Nolan"])


class DirectorResponseSchema(BaseModel):
    id: int = Field(examples=[1])
    name: str = Field(examples=["Christopher Nolan"])

    model_config = {
        "from_attributes": True
    }


class MovieListItemResponseSchema(BaseModel):
    id: int = Field(examples=[1])
    uuid: UUID = Field(examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"])
    name: str = Field(examples=["Inception"])
    year: int = Field(examples=[2010])
    time: int = Field(examples=[148])
    imdb: float = Field(examples=[8.8])
    price: Decimal = Field(examples=[9.99])
    certification: CertificationResponseSchema

    model_config = {
        "from_attributes": True
    }


class MovieCreateRequestSchema(BaseModel):
    name: str = Field(max_length=250, examples=["Inception"])
    year: int = Field(examples=[2010])
    time: int = Field(gt=0, examples=[148])
    imdb: float = Field(ge=0, le=10, examples=[8.8])
    votes: int = Field(ge=0, examples=[2400000])
    meta_score: float | None = Field(ge=0, le=100, default=None, examples=[74.0])
    gross: float | None = Field(ge=0, default=None, examples=[292576195.0])
    description: str = Field(
        min_length=1,
        examples=["A thief who steals corporate secrets through dream-sharing technology."]
    )
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2, examples=[9.99])
    certification_id: int = Field(examples=[1])
    genre_ids_or_names: list[int | str] = Field(examples=[["Action", "Sci-Fi"]])
    director_ids_or_names: list[int | str] = Field(examples=[["Christopher Nolan"]])
    star_ids_or_names: list[int | str] = Field(examples=[["Leonardo DiCaprio", "Tom Hardy"]])

    @field_validator("year")
    @classmethod
    def validate_year(cls, value: int) -> int:
        current_year = datetime.today().year
        if not (1888 <= value <= current_year + 5):
            raise ValueError(f"Year must be between 1888 and {current_year}.")
        return value


class MovieUpdateRequestSchema(BaseModel):
    name: str | None = Field(max_length=250, default=None, examples=["Inception"])
    year: int | None = Field(default=None, examples=[2010])
    time: int | None = Field(gt=0, default=None, examples=[148])
    imdb: float | None = Field(ge=0, le=10, default=None, examples=[8.8])
    votes: int | None = Field(ge=0, default=None, examples=[2400000])
    meta_score: float | None = Field(ge=0, le=100, default=None, examples=[74.0])
    gross: float | None = Field(ge=0, default=None, examples=[292576195.0])
    description: str | None = Field(
        min_length=1,
        default=None,
        examples=["A thief who steals corporate secrets through dream-sharing technology."]
    )
    price: Decimal | None = Field(gt=0, max_digits=10, decimal_places=2, default=None, examples=[9.99])
    certification_id: int | None = Field(default=None, examples=[1])
    genre_ids_or_names: list[int | str] | None = Field(default=None, examples=[["Action", "Sci-Fi"]])
    director_ids_or_names: list[int | str] | None = Field(default=None, examples=[["Christopher Nolan"]])
    star_ids_or_names: list[int | str] | None = Field(
        default=None,
        examples=[["Leonardo DiCaprio", "Tom Hardy"]]
    )

    @field_validator("year")
    @classmethod
    def validate_year(cls, value: int | None) -> int | None:
        if value is not None:
            current_year = datetime.today().year
            if not (1888 <= value <= current_year + 5):
                raise ValueError(f"Year must be between 1888 and {current_year}.")
        return value


class MovieDetailResponseSchema(BaseModel):
    id: int = Field(examples=[1])
    uuid: UUID = Field(examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"])
    name: str = Field(examples=["Inception"])
    year: int = Field(examples=[2010])
    time: int = Field(examples=[148])
    imdb: float = Field(examples=[8.8])
    price: Decimal = Field(examples=[9.99])
    votes: int = Field(examples=[2400000])
    meta_score: float | None = Field(examples=[74.0])
    gross: float | None = Field(examples=[292576195.0])
    description: str = Field(
        examples=["A thief who steals corporate secrets through dream-sharing technology."]
    )
    genres: list[GenreResponseSchema]
    stars: list[StarResponseSchema]
    directors: list[DirectorResponseSchema]
    certification: CertificationResponseSchema

    model_config = {
        "from_attributes": True
    }


class PaginatedMovieResponseSchema(BaseModel):
    items: list[MovieListItemResponseSchema]
    total: int = Field(examples=[1])
    page: int = Field(examples=[1])
    per_page: int = Field(examples=[20])
    total_pages: int = Field(examples=[1])


class LikeDislikeMovieSchema(BaseModel):
    like_dislike: LikeDislikeEnum = LikeDislikeEnum.LIKE


class MovieRateSchema(BaseModel):
    score: int = Field(ge=1, le=10)


class MovieCommentSchema(BaseModel):
    comment : str = Field(min_length=1)
    parent_id: int | None = Field(default=None, examples=[None])


class MovieCommentListItemResponseSchema(BaseModel):
    id: int = Field(examples=[1])
    user: str = Field(examples=["user@example.com"])
    parent_id: int | None = Field(default=None, examples=[None])
    comment: str = Field(examples=["Great movie!"])


class MovieCommentResponseSchema(BaseModel):
    movie_name: str = Field(examples=["Inception"])
    comments: list[MovieCommentListItemResponseSchema] | None


class MovieCommentUpdateSchema(BaseModel):
    comment: str = Field(min_length=1)
