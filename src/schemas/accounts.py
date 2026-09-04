from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from database import accounts_validators
from schemas.profiles import UserProfileResponseSchema

from database.models.accounts import UserGroupEnum


class BaseEmailPasswordSchema(BaseModel):
    email: EmailStr = Field(examples=["user@example.com"])
    password: str = Field(examples=["StrongPassword123!"])

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return accounts_validators.validate_email(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return accounts_validators.validate_password(value)


class UserRegistrationRequestSchema(BaseEmailPasswordSchema):
    pass


class UserRegistrationResponseSchema(BaseModel):
    id: int = Field(examples=[1])
    email: EmailStr = Field(examples=["user@example.com"])
    is_active: bool = Field(examples=[False])
    created_at: datetime = Field(examples=["2024-01-01T12:00:00"])

    model_config = {
        "from_attributes": True
    }


class UserActivationRequestSchema(BaseModel):
    email: EmailStr = Field(examples=["user@example.com"])
    token: str = Field(examples=["a1b2c3d4-e5f6-7890-abcd-ef1234567890"])


class ResendActivationRequestSchema(BaseModel):
    email: EmailStr = Field(examples=["user@example.com"])


class UserLoginRequestSchema(BaseModel):
    email: EmailStr = Field(examples=["user@example.com"])
    password: str = Field(examples=["StrongPassword123!"])

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return accounts_validators.validate_email(value)


class TokenPairResponseSchema(BaseModel):
    access_token: str = Field(examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."])
    refresh_token: str = Field(examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."])
    token_type: str = "bearer"

    model_config = {
        "from_attributes": True
    }


class LogoutRequestSchema(BaseModel):
    refresh_token: str = Field(examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."])


class TokenRefreshRequestSchema(BaseModel):
    refresh_token: str = Field(examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."])


class TokenRefreshResponseSchema(BaseModel):
    access_token: str = Field(examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."])
    token_type: str = "bearer"

    model_config = {
        "from_attributes": True
    }


class PasswordChangeRequestSchema(BaseModel):
    old_password: str = Field(examples=["OldPassword123!"])
    new_password: str = Field(examples=["NewStrongPassword456!"])


class PasswordResetRequestSchema(BaseModel):
    email: EmailStr = Field(examples=["user@example.com"])


class PasswordResetCompleteRequestSchema(BaseModel):
    email: EmailStr = Field(examples=["user@example.com"])
    token: str = Field(examples=["a1b2c3d4-e5f6-7890-abcd-ef1234567890"])
    new_password: str = Field(examples=["NewStrongPassword456!"])


class UserResponseSchema(BaseModel):
    id: int = Field(examples=[1])
    email: EmailStr = Field(examples=["user@example.com"])
    is_active: bool = Field(examples=[True])
    group: str = Field(examples=["user"])
    created_at: datetime = Field(examples=["2024-01-01T12:00:00"])
    updated_at: datetime = Field(examples=["2024-01-01T12:00:00"])
    profile: UserProfileResponseSchema | None


class MessageResponseSchema(BaseModel):
    message: str = Field(examples=["Operation completed successfully."])


class ChangeUserGroupRequestSchema(BaseModel):
    group: UserGroupEnum = Field(examples=[UserGroupEnum.MODERATOR])


class UserActiveDeactivateStatusRequestSchema(BaseModel):
    is_active: bool = Field(examples=[True])
