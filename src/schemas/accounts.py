from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator

from database import accounts_validators
from schemas.profiles import UserProfileResponseSchema

from database.models.accounts import UserGroupEnum


class BaseEmailPasswordSchema(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value):
        return accounts_validators.validate_email(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value):
        return accounts_validators.validate_password(value)


class UserRegistrationRequestSchema(BaseEmailPasswordSchema):
    pass


class UserRegistrationResponseSchema(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    created_at: datetime

    model_config = {
        "from_attributes": True
    }


class UserActivationRequestSchema(BaseModel):
    email: EmailStr
    token: str


class ResendActivationRequestSchema(BaseModel):
    email: EmailStr


class UserLoginRequestSchema(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value):
        return accounts_validators.validate_email(value)


class TokenPairResponseSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

    model_config = {
        "from_attributes": True
    }


class LogoutRequestSchema(BaseModel):
    refresh_token: str


class TokenRefreshRequestSchema(BaseModel):
    refresh_token: str


class TokenRefreshResponseSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"

    model_config = {
        "from_attributes": True
    }


class PasswordChangeRequestSchema(BaseModel):
    old_password: str
    new_password: str


class PasswordResetRequestSchema(BaseModel):
    email: EmailStr


class PasswordResetCompleteRequestSchema(BaseModel):
    email: EmailStr
    token: str
    new_password: str


class UserResponseSchema(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    group: str
    created_at: datetime
    updated_at: datetime
    profile: UserProfileResponseSchema | None


class MessageResponseSchema(BaseModel):
    message: str


class ChangeUserGroupRequestSchema(BaseModel):
    group: UserGroupEnum


class UserActiveDeactivateStatusRequestSchema(BaseModel):
    is_active: bool
