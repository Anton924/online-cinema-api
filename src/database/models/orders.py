from datetime import datetime, timezone
import enum
from typing import List

from database import Base
from sqlalchemy import ForeignKey, Enum, DECIMAL, Integer, DateTime
from sqlalchemy.orm import mapped_column, Mapped, relationship


class StatusOrderEnum(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELED = "canceled"


class OrderModel(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(Enum(StatusOrderEnum), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    order_sum: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)

    user: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="orders"
    )

    order_items: Mapped[List["OrderItemModel"]] = relationship(
        "OrderItemModel",
        back_populates="order"
    )

    payment: Mapped["PaymentModel"] = relationship(
        "PaymentModel",
        back_populates="order"
    )


class OrderItemModel(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="RESTRICT"), nullable=False)
    price_at_order: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)

    order: Mapped["OrderModel"] = relationship(
        "OrderModel",
        back_populates="order_items"
    )

    movie: Mapped["MovieModel"] = relationship(
        "MovieModel",
        back_populates="order_items"
    )

    payment_item: Mapped["PaymentItemModel"] = relationship(
        "PaymentItemModel",
        back_populates="order_item"
    )
