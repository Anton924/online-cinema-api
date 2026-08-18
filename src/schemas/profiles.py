from datetime import date
from typing import Any

from fastapi import UploadFile, Form, File
from pydantic import BaseModel, EmailStr, field_validator

from validation.profile import validate_image, validate_gender, validate_birth_date, validate_name


class UserProfileRequestSchema(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    avatar: UploadFile | None = None
    gender: str | None = None
    date_of_birth: date | None = None
    info: str | None = None

    @classmethod
    def from_form(
        cls,
        first_name=Form(),
        last_name=Form(),
        avatar=File(),
        gender=Form(),
        date_of_birth=Form(),
        info=Form(),
    ):
        return cls(
            first_name=first_name,
            last_name=last_name,
            avatar=avatar,
            gender=gender,
            date_of_birth=date_of_birth,
            info=info
        )

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, value: str) -> str | None:
        validate_name(value)
        return value

    @field_validator("avatar")
    @classmethod
    def validate_avatar(cls, value: UploadFile) -> UploadFile | None:
        validate_image(value)
        return value

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, value: str) -> str | None:
        validate_gender(value)
        return value

    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(cls, value: date) -> date | None:
        validate_birth_date(value)
        return value


class UserProfileResponseSchema(BaseModel):
    id: int | None
    first_name: str | None
    last_name: str | None
    avatar: str | None
    gender: str | None
    date_of_birth: date | None
    info: str | None
    user_id: int | None

    model_config = {
        "from_attributes": True
    }




