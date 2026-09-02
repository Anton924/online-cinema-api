from fastapi import APIRouter, Depends, status
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from security.dependencies import require_roles
from database.models.accounts import (
    UserModel,
    UserGroupEnum
)
from services.profiles import (
    create_user_profile,
    get_own_profile,
    update_user_profile,
    update_user_avatar,
    delete_user_avatar
)
from schemas.profiles import (
    UserProfileResponseSchema,
    UserProfileRequestSchema,
    UserProfileRequestUpdateSchema,
    UserProfileRequestUpdateAvatarSchema
)
from config.dependencies import get_s3_client
from storages.interfaces import S3StorageInterface


router = APIRouter()


@router.post(
    "/me",
    status_code=status.HTTP_201_CREATED,
    response_model=UserProfileResponseSchema,
    responses={
        401: {
            "description": "Unauthorized - The user account is not activated.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "User is not active"
                    }
                }
            },
        },
        409: {
            "description": "Conflict - A profile for this user already exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Profile for this user already exists."
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while uploading the avatar "
                           "or creating the profile.",
            "content": {
                "application/json": {
                    "examples": {
                        "avatar_upload_failed": {
                            "summary": "Avatar Upload Failed",
                            "value": {
                                "detail": "Failed to upload avatar. Please try again later."
                            }
                        },
                        "profile_creation_failed": {
                            "summary": "Profile Creation Failed",
                            "value": {
                                "detail": "An error occurred while creating the profile."
                            }
                        },
                    }
                }
            },
        },
    }
)
async def create_profile(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        UserModel,
        Depends(require_roles(UserGroupEnum.USER, UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ],
    s3_client: Annotated[S3StorageInterface, Depends(get_s3_client)],
    profile_data: Annotated[UserProfileRequestSchema, Depends(UserProfileRequestSchema.from_form)]
) -> UserProfileResponseSchema:
    return await create_user_profile(
        db=db,
        current_user=current_user,
        s3_client=s3_client,
        profile_data=profile_data
    )


@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    response_model=UserProfileResponseSchema,
    responses={
        404: {
            "description": "Not Found - No profile exists for this user yet.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Profile not found."
                    }
                }
            },
        },
    }
)
async def read_own_profile(
    current_user: Annotated[
        UserModel,
        Depends(require_roles(UserGroupEnum.USER, UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ],
    s3_client: Annotated[S3StorageInterface, Depends(get_s3_client)]
) -> UserProfileResponseSchema:
    return await get_own_profile(
        current_user=current_user,
        s3_client=s3_client
    )


@router.patch(
    "/me",
    status_code=status.HTTP_200_OK,
    response_model=UserProfileResponseSchema,
    responses={
        404: {
            "description": "Not Found - No profile exists for this user yet.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Profile not found."
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while updating the profile.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while updating the profile."
                    }
                }
            },
        },
    }
)
async def update_profile(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        UserModel,
        Depends(require_roles(UserGroupEnum.USER, UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ],
    s3_client: Annotated[S3StorageInterface, Depends(get_s3_client)],
    update_data: UserProfileRequestUpdateSchema
) -> UserProfileResponseSchema:
    return await update_user_profile(
        db=db,
        current_user=current_user,
        s3_client=s3_client,
        update_data=update_data
    )


@router.patch(
    "/me/avatar",
    status_code=status.HTTP_200_OK,
    response_model=UserProfileResponseSchema,
    responses={
        404: {
            "description": "Not Found - No profile exists for this user yet.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Profile not found."
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while uploading or saving the avatar.",
            "content": {
                "application/json": {
                    "examples": {
                        "avatar_upload_failed": {
                            "summary": "Avatar Upload Failed",
                            "value": {
                                "detail": "Failed to upload avatar. Please try again later."
                            }
                        },
                        "avatar_save_failed": {
                            "summary": "Avatar Save Failed",
                            "value": {
                                "detail": "An error occurred while saving the avatar. Please try again later."
                            }
                        },
                    }
                }
            },
        },
    }
)
async def update_avatar(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        UserModel,
        Depends(require_roles(UserGroupEnum.USER, UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ],
    s3_client: Annotated[S3StorageInterface, Depends(get_s3_client)],
    update_data: Annotated[
        UserProfileRequestUpdateAvatarSchema,
        Depends(UserProfileRequestUpdateAvatarSchema.from_form)
    ]
) -> UserProfileResponseSchema:
    return await update_user_avatar(
        db=db,
        current_user=current_user,
        s3_client=s3_client,
        update_data=update_data
    )


@router.delete(
    "/me/avatar",
    status_code=status.HTTP_200_OK,
    response_model=UserProfileResponseSchema,
    responses={
        404: {
            "description": "Not Found - No profile exists for this user, or the profile has no avatar.",
            "content": {
                "application/json": {
                    "examples": {
                        "profile_not_found": {
                            "summary": "Profile Not Found",
                            "value": {
                                "detail": "Profile not found."
                            }
                        },
                        "avatar_not_found": {
                            "summary": "Avatar Not Found",
                            "value": {
                                "detail": "Avatar not found."
                            }
                        },
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while deleting the avatar.",
            "content": {
                "application/json": {
                    "examples": {
                        "avatar_delete_failed": {
                            "summary": "Avatar Delete Failed",
                            "value": {
                                "detail": "Failed to delete avatar. Please try again later."
                            }
                        },
                        "db_delete_failed": {
                            "summary": "Database Update Failed",
                            "value": {
                                "detail": "An error occurred while deleting the avatar."
                            }
                        },
                    }
                }
            },
        },
    }
)
async def delete_avatar(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        UserModel,
        Depends(require_roles(UserGroupEnum.USER, UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ],
    s3_client: Annotated[S3StorageInterface, Depends(get_s3_client)]
) -> UserProfileResponseSchema:
    return await delete_user_avatar(
        db=db,
        current_user=current_user,
        s3_client=s3_client
    )
