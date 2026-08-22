import enum
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from sqlalchemy import (
    ForeignKey,
    String,
    Boolean,
    DateTime,
    Enum,
    Integer,
    func,
    Text,
    Date,
    UniqueConstraint
)
from database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from security import (
    generate_secure_token,
    hash_password,
    verify_password
)

from database.validators.accounts import validate_password, validate_email as validate_email_format


class UserGroupEnum(str, enum.Enum):
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"


class GenderEnum(str, enum.Enum):
    MAN = "man"
    WOMAN = "woman"


class UserGroup(Base):
    __tablename__ = "user_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Enum(UserGroupEnum), unique=True, nullable=False)

    users: Mapped[List["UserModel"]] = relationship("UserModel", back_populates="group")

    def __repr__(self) -> str:
        return f"<UserGroupModel(id={self.id}, name={self.name})>"


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    _hashed_password: Mapped[str] = mapped_column("hashed_password", String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    group_id: Mapped[int] = mapped_column(ForeignKey("user_groups.id", ondelete="CASCADE"), nullable=False)

    group: Mapped["UserGroup"] = relationship("UserGroup", back_populates="users")

    profile: Mapped[Optional["UserProfileModel"]] = relationship("UserProfileModel", back_populates="user")

    activation_token: Mapped[Optional["ActivationTokenModel"]] = relationship(
        "ActivationTokenModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    password_reset_token: Mapped[Optional["PasswordResetTokenModel"]] = relationship(
        "PasswordResetTokenModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    refresh_token: Mapped[Optional["RefreshTokenModel"]] = relationship(
        "RefreshTokenModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    def has_group(self, group_name: UserGroupEnum) -> bool:
        return self.group.name == group_name

    @classmethod
    def create(cls, email: str, group_id: int, raw_password: str) -> "UserModel":
        user = cls(email=email, group_id=group_id)
        user.password = raw_password
        return user

    @property
    def password(self) -> None:
        raise AttributeError("Password is write-only. Use the setter to set the password.")

    @password.setter
    def password(self, raw_password: str) -> None:
        validate_password(raw_password, )
        self._hashed_password = hash_password(raw_password)

    @classmethod
    def verify_password(cls, plain_password: str, hashed_password: str) -> bool:
        return verify_password(plain_password, hashed_password)

    @validates("email")
    def validate_email(self, key: str, value: str) -> str:
        return validate_email_format(value)


class UserProfileModel(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    avatar: Mapped[Optional[str]] = mapped_column(String(255))
    gender: Mapped[Optional[str]] = mapped_column(Enum(GenderEnum))
    date_of_birth: Mapped[Optional[datetime.date]] = mapped_column(Date)
    info: Mapped[Optional[str]] = mapped_column(Text)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="profile")

    __table_args__ = (UniqueConstraint(user_id),)

    def __repr__(self) -> str:
        return (
            f"<UserProfileModel(id={self.id}, first_name={self.first_name}, last_name={self.last_name}, "
            f"gender={self.gender}, date_of_birth={self.date_of_birth})>"
        )


class TokenBaseModel(Base):
    __abstract__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token: Mapped[str] = mapped_column(
        String(512),
        unique=True,
        nullable=False,
        default=generate_secure_token
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc) + timedelta(days=1)
    )


class ActivationTokenModel(TokenBaseModel):
    __tablename__ = "activation_tokens"

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="activation_token")

    __table_args__ = (UniqueConstraint("user_id"),)

    def __repr__(self) -> str:
        return f"<ActivationTokenModel(id={self.id}, token={self.token}, expires_at={self.expires_at})>"


class PasswordResetTokenModel(TokenBaseModel):
    __tablename__ = "password_reset_tokens"

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="password_reset_token")

    __table_args__ = (UniqueConstraint("user_id"),)

    def __repr__(self) -> str:
        return f"<PasswordResetTokenModel(id={self.id}, token={self.token}, expires_at={self.expires_at})>"


class RefreshTokenModel(TokenBaseModel):
    __tablename__ = "refresh_tokens"

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="refresh_token")

    @classmethod
    def create(cls, user_id: int, token: str, days_valid: int) -> "RefreshTokenModel":
        expires_at = datetime.now(timezone.utc) + timedelta(days=days_valid)
        return cls(user_id=user_id, token=token, expires_at=expires_at)

    def __repr__(self) -> str:
        return f"<RefreshTokenModel(id={self.id}, token={self.token}, expires_at={self.expires_at})>"
