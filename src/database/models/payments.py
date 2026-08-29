import enum
from typing import List

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, ForeignKey, Enum, DECIMAL, String

from database import Base


class PaymentStatus(str, enum.Enum):
    SUCCESSFUL = "successful"
    CANCELED = "canceled"
    REFUNDED = "refunded"


class PaymentModel(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False, unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(Enum(PaymentStatus), nullable=False)
    external_payment_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    order: Mapped["OrderModel"] = relationship(
        "OrderModel",
        back_populates="payment"
    )

    user: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="payments"
    )

    payment_items: Mapped[List["PaymentItemModel"]] = relationship(
        "PaymentItemModel",
        back_populates="payment"
    )


class PaymentItemModel(Base):
    __tablename__ = "payment_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)

    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id", ondelete="RESTRICT"), nullable=False)
    order_item_id: Mapped[int] = mapped_column(
        ForeignKey("order_items.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    price_at_payment: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)

    payment: Mapped["PaymentModel"] = relationship(
        "PaymentModel",
        back_populates="payment_items"
    )

    order_item: Mapped["OrderItemModel"] = relationship(
        "OrderItemModel",
        back_populates="payment_item"
    )
