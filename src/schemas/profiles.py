from datetime import date

from fastapi import UploadFile, Form, File, HTTPException, status
from pydantic import BaseModel, field_validator, ValidationError

from validation.profile import validate_image, validate_gender, validate_birth_date, validate_name

from database.models.accounts import GenderEnum


class UserProfileRequestSchema(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    avatar: UploadFile | None = None
    gender: GenderEnum | None = None
    date_of_birth: date | None = None
    info: str | None = None

    @classmethod
    def from_form(
        cls,
        first_name: str | None = Form(None),
        last_name: str | None = Form(None),
        avatar: UploadFile | None | str = File(None),
        gender: GenderEnum | None = Form(None),
        date_of_birth: date | None | str = Form(None),
        info: str | None = Form(None),
    ) -> "UserProfileRequestSchema":

        try:
            if isinstance(avatar, str):
                avatar = None
            return cls(
                first_name=first_name,
                last_name=last_name,
                avatar=avatar,
                gender=gender,
                date_of_birth=date_of_birth,
                info=info
            )
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=[
                    {"field": error["loc"][-1], "message": error["msg"]}
                    for error in e.errors()
                ]
            ) from e

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def validate_name(cls, value: str) -> str | None:
        if not value or value is None:
            return None
        return validate_name(value)

    @field_validator("avatar")
    @classmethod
    def validate_avatar(cls, value: UploadFile) -> UploadFile | None:
        if not value or value is None:
            return None
        return validate_image(value)

    @field_validator("gender", mode="before")
    @classmethod
    def validate_gender(cls, value: str) -> GenderEnum | None:
        if not value or value is None:
            return None
        return validate_gender(value)

    @field_validator("date_of_birth", mode="before")
    @classmethod
    def validate_date_of_birth(cls, value: date) -> date | None:
        if not value or value is None:
            return None
        return validate_birth_date(value)


class UserProfileResponseSchema(BaseModel):
    id: int | None
    first_name: str | None
    last_name: str | None
    avatar: str | None
    gender: GenderEnum | None
    date_of_birth: date | None
    info: str | None
    user_id: int | None

    model_config = {
        "from_attributes": True
    }


class UserProfileRequestUpdateSchema(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    gender: GenderEnum | None = None
    date_of_birth: date | None = None
    info: str | None = None


class UserProfileRequestUpdateAvatarSchema(BaseModel):
    avatar: UploadFile

    @classmethod
    def from_form(
            cls,
            avatar: UploadFile
    ) -> "UserProfileRequestUpdateAvatarSchema":
        return cls(
            avatar=avatar
        )

    @field_validator("avatar")
    @classmethod
    def validate_avatar(cls, value: UploadFile) -> UploadFile:
        return validate_image(value)
