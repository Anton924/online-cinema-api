from typing import List, Optional
import uuid as uuid_pkg

from database import Base
from sqlalchemy import Integer, String, Table, Column, ForeignKey, Uuid, Float, Text, DECIMAL, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship


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
