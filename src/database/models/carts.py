from typing import List

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, ForeignKey, UniqueConstraint

from database import Base


class CartModel(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True)

    __table_args__ = (UniqueConstraint("user_id"),)

    user: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="cart"
    )

    cart_items: Mapped[List["CartItem"]] = relationship(
        "CartItem",
        back_populates="cart"
    )


class CartItem(Base):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id", ondelete="CASCADE"), nullable=False)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (UniqueConstraint("cart_id", "movie_id"),)

    cart: Mapped["CartModel"] = relationship(
        "CartModel",
        back_populates="cart_items"
    )

    movie: Mapped["MovieModel"] = relationship(
        "MovieModel",
        back_populates="cart_items"
    )
