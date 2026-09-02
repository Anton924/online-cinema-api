from fastapi import Depends, status, HTTPException
from typing import Annotated

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from security.dependencies import require_roles
from database.models.accounts import (
    UserModel,
    UserProfileModel,
    UserGroupEnum
)
from schemas.profiles import (
    UserProfileResponseSchema,
    UserProfileRequestSchema
)
from storages.interfaces import S3StorageInterface
from exceptions import S3FileUploadError, S3ConnectionError
from config.dependencies import get_s3_client


async def create_user_profile(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        UserModel,
        Depends(require_roles(UserGroupEnum.USER, UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ],
    profile_data: UserProfileRequestSchema,
    s3_client: Annotated[S3StorageInterface, Depends(get_s3_client)]
) -> UserProfileResponseSchema:
    if current_user.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is not active"
        )
    if current_user.profile:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Profile for this user already exists."
        )
    if profile_data.avatar:
        avatar_bytes = await profile_data.avatar.read()
        extension = profile_data.avatar.content_type.split("/")[-1]
        avatar_key = f"avatar/{current_user.id}.{extension}"
        try:
            await s3_client.upload_file(
                file_name=avatar_key,
                file_data=avatar_bytes,
                content_type=profile_data.avatar.content_type
            )
        except (S3FileUploadError, S3ConnectionError) as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload avatar. Please try again later."
            ) from e
    try:
        new_profile = UserProfileModel(
            first_name=profile_data.first_name,
            last_name=profile_data.last_name,
            gender=profile_data.gender,
            date_of_birth=profile_data.date_of_birth,
            info=profile_data.info,
            user_id=current_user.id,
        )
        if profile_data.avatar is not None:
            new_profile.avatar = avatar_key
            avatar_url = await s3_client.get_file_url(
                new_profile.avatar
            )
        else:
            avatar_url = None
        db.add(new_profile)
        await db.commit()
        await db.refresh(new_profile)
        return UserProfileResponseSchema(
            id=new_profile.id,
            first_name=new_profile.first_name,
            last_name=new_profile.last_name,
            avatar=avatar_url,
            gender=new_profile.gender,
            date_of_birth=new_profile.date_of_birth,
            info=new_profile.info,
            user_id=new_profile.user_id
        )
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the profile."
        ) from e
