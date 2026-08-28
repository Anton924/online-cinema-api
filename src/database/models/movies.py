import enum
from typing import List, Optional
import uuid as uuid_pkg
from sqlalchemy import Integer, String, Table, Column, ForeignKey, Uuid, Float, Text, DECIMAL, UniqueConstraint, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from database import Base


class LikeDislikeEnum(str, enum.Enum):
    LIKE = "like"
    DISLIKE = "dislike"


MovieGenreModel = Table(
    "movie_genres",
    Base.metadata,
    Column("movie_id", ForeignKey("movies.id", ondelete="CASCADE"), nullable=False, primary_key=True),
    Column("genre_id", ForeignKey("genres.id", ondelete="CASCADE"), nullable=False, primary_key=True)
)

MovieDirectorModel = Table(
    "movie_directors",
    Base.metadata,
    Column("movie_id", ForeignKey("movies.id", ondelete="CASCADE"), nullable=False, primary_key=True),
    Column("director_id", ForeignKey("directors.id", ondelete="CASCADE"), nullable=False, primary_key=True)
)

MovieStarModel = Table(
    "movie_stars",
    Base.metadata,
    Column("movie_id", ForeignKey("movies.id", ondelete="CASCADE"), nullable=False, primary_key=True),
    Column("star_id", ForeignKey("stars.id", ondelete="CASCADE"), nullable=False, primary_key=True)
)


FavoriteMovieModel = Table(
    "movie_favorite",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), nullable=False, primary_key=True),
    Column("movie_id", ForeignKey("movies.id", ondelete="CASCADE"), nullable=False, primary_key=True)
)


class MovieLikeDislikeModel(Base):
    __tablename__ = "movie_likes_dislikes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), nullable=False)
    like_dislike: Mapped[str] = mapped_column(Enum(LikeDislikeEnum), nullable=False)

    __table_args__ = (UniqueConstraint("user_id", "movie_id"),)

    user: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="likes_dislikes"
    )

    movie: Mapped["MovieModel"] = relationship(
        "MovieModel",
        back_populates="likes_dislikes"
    )


class MovieRateModel(Base):
    __tablename__ = "movie_rates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (UniqueConstraint("user_id", "movie_id"),)

    user: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="scores"
    )

    movie: Mapped["MovieModel"] = relationship(
        "MovieModel",
        back_populates="scores"
    )

    @validates("score")
    def validate(self, key: str, value: int) -> int:
        if value not in range(1, 11):
            raise ValueError(
                "Rate score has to be in range form 1 to 10!"
            )
        return value


class MovieCommentModel(Base):
    __tablename__ = "movie_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("movie_comments.id", ondelete="CASCADE"), nullable=True, default=None
    )
    comment: Mapped[str] = mapped_column(Text, nullable=False)

    user: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="comments"
    )

    movie: Mapped["MovieModel"] = relationship(
        "MovieModel",
        back_populates="comments"
    )

    parent: Mapped["MovieCommentModel"] = relationship(
        "MovieCommentModel",
        back_populates="children_comments",
        remote_side=[id]
    )

    children_comments: Mapped[List["MovieCommentModel"]] = relationship(
        "MovieCommentModel",
        back_populates="parent"
    )

    @validates("comment")
    def validate_comment(self, key: str, value: str) -> str:
        if len(value) < 0:
            raise ValueError("Your comment has to consist at least one digit!")
        return value


class CertificationModel(Base):
    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    movies: Mapped[List["MovieModel"]] = relationship(
        "MovieModel",
        back_populates="certification"
    )


class GenreModel(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    movies: Mapped[List["MovieModel"]] = relationship(
        "MovieModel",
        secondary=MovieGenreModel,
        back_populates="genres"
    )


class StarModel(Base):
    __tablename__ = "stars"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    movies: Mapped[List["MovieModel"]] = relationship(
        "MovieModel",
        secondary=MovieStarModel,
        back_populates="stars"
    )


class DirectorModel(Base):
    __tablename__ = "directors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    movies: Mapped[List["MovieModel"]] = relationship(
        "MovieModel",
        secondary=MovieDirectorModel,
        back_populates="directors"
    )


class MovieModel(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uuid: Mapped[uuid_pkg.UUID] = mapped_column(Uuid, unique=True, default=uuid_pkg.uuid4)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    time: Mapped[int] = mapped_column(Integer, nullable=False)
    imdb: Mapped[float] = mapped_column(Float, nullable=False)
    votes: Mapped[int] = mapped_column(Integer, nullable=False)
    meta_score: Mapped[Optional[float]] = mapped_column(Float)
    gross: Mapped[Optional[float]] = mapped_column(Float)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)

    certification_id: Mapped[int] = mapped_column(ForeignKey("certifications.id"), nullable=False)

    __table_args__ = (UniqueConstraint("name", "year", "time"),)

    certification: Mapped["CertificationModel"] = relationship(
        "CertificationModel",
        back_populates="movies"
    )

    genres: Mapped[List["GenreModel"]] = relationship(
        "GenreModel",
        secondary=MovieGenreModel,
        back_populates="movies"
    )

    stars: Mapped[List["StarModel"]] = relationship(
        "StarModel",
        secondary=MovieStarModel,
        back_populates="movies"
    )

    directors: Mapped[List["DirectorModel"]] = relationship(
        "DirectorModel",
        secondary=MovieDirectorModel,
        back_populates="movies"
    )

    favorited_by: Mapped[List["UserModel"]] = relationship(
        "UserModel",
        secondary=FavoriteMovieModel,
        back_populates="favorite_movies"
    )

    likes_dislikes: Mapped[List["MovieLikeDislikeModel"]] = relationship(
        "MovieLikeDislikeModel",
        back_populates="movie"
    )

    scores: Mapped[List["MovieRateModel"]] = relationship(
        "MovieRateModel",
        back_populates="movie"
    )

    comments: Mapped[List["MovieCommentModel"]] = relationship(
        "MovieCommentModel",
        back_populates="movie"
    )

    cart_items: Mapped[List["CartItem"]] = relationship(
        "CartItem",
        back_populates="movie"
    )

    order_items: Mapped[List["OrderItemModel"]] = relationship(
        "OrderItemModel",
        back_populates="movie"
    )
