from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas.accounts import (
    UserRegistrationRequestSchema,
    UserRegistrationResponseSchema,
    MessageResponseSchema,
    UserActivationRequestSchema,
    ResendActivationRequestSchema,
    TokenPairResponseSchema,
    LogoutRequestSchema,
    TokenRefreshRequestSchema,
    TokenRefreshResponseSchema,
    UserResponseSchema,
    PasswordChangeRequestSchema,
    PasswordResetRequestSchema,
    PasswordResetCompleteRequestSchema,
    UserLoginRequestSchema,
    ChangeUserGroupRequestSchema,
    UserActiveDeactivateStatusRequestSchema
)

from services.accounts import (
    register_user,
    activate_user,
    activate_through_activation_link,
    resend_activation_token,
    resend_activation_token,
    login_user,
    revoke_refresh_token,
    refresh_access_token,
    request_user_password_reset,
    reset_user_password,
    change_password,
    change_user_group_from_admin,
    activate_deactivate_user_manually
)
from config.dependencies import (
    get_email_sender,
    get_jwt_auth_manager,
    get_settings
)
from notifications.interfaces import EmailSenderInterface
from security.interfaces import JWTAuthManagerInterface
from config.settings import BaseAppSettings
from security import get_token
from security.dependencies import get_current_user
from database.models.accounts import (
    UserModel
)


router = APIRouter()


@router.post(
    "/accounts/register",
    status_code=status.HTTP_201_CREATED,
    response_model=UserRegistrationResponseSchema,
    responses={
        409: {
            "description": "Conflict - User with this email already exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "A user with this email test@example.com already exists."
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred during user creation.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred during user creation."
                    }
                }
            },
        }
    }
)
async def register(
        db: Annotated[AsyncSession, Depends(get_db)],
        user_data: UserRegistrationRequestSchema,
        email_sender: Annotated[EmailSenderInterface, Depends(get_email_sender)]
):
    return await register_user(db=db, user_data=user_data, email_sender=email_sender)


@router.post(
    "/accounts/activate",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": "Bad Request - The activation token is invalid or expired, "
                           "or the user account is already active.",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_token": {
                            "summary": "Invalid Token",
                            "value": {
                                "detail": "Invalid or expired activation token."
                            }
                        },
                        "already_active": {
                            "summary": "Account Already Active",
                            "value": {
                                "detail": "User account is already active."
                            }
                        },
                    }
                }
            },
        },
    }
)
async def activate(
        db: Annotated[AsyncSession, Depends(get_db)],
        activation_data: UserActivationRequestSchema,
        email_sender: Annotated[EmailSenderInterface, Depends(get_email_sender)]
):
    return await activate_user(
        db=db,
        activation_data=activation_data,
        email_sender=email_sender
    )


@router.get(
    "/accounts/activate_activation_link/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": "Bad Request - The activation token is invalid or expired, "
                           "or the user account is already active.",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_token": {
                            "summary": "Invalid Token",
                            "value": {
                                "detail": "Invalid or expired activation token."
                            }
                        },
                        "already_active": {
                            "summary": "Account Already Active",
                            "value": {
                                "detail": "User account is already active."
                            }
                        },
                    }
                }
            },
        },
    }
)
async def activate_activation_link(
        db: Annotated[AsyncSession, Depends(get_db)],
        email: str,
        token: str,
        email_sender: Annotated[EmailSenderInterface, Depends(get_email_sender)]
):
    return await activate_through_activation_link(
        db=db,
        email=email,
        token=token,
        email_sender=email_sender
    )


@router.post(
    "/accounts/resend-activation",
    status_code=status.HTTP_200_OK,
    response_model=MessageResponseSchema,
    responses={
        400: {
            "description": "Bad Request - The activation token is invalid or expired, "
                           "or the user account is already active.",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_token": {
                            "summary": "Invalid Token",
                            "value": {
                                "detail": "Invalid or expired activation token."
                            }
                        },
                        "already_active": {
                            "summary": "Account Already Active",
                            "value": {
                                "detail": "User account is already active."
                            }
                        },
                    }
                }
            },
        },
    }
)
async def resend_activation(
        db: Annotated[AsyncSession, Depends(get_db)],
        resend_activation_data: ResendActivationRequestSchema,
        email_sender: Annotated[EmailSenderInterface, Depends(get_email_sender)],
):
    return await resend_activation_token(
        db=db,
        resend_activation_data=resend_activation_data,
        email_sender=email_sender
    )

@router.post(
    "/accounts/login/",
    status_code=status.HTTP_200_OK,
    response_model=TokenPairResponseSchema
)
async def login(
    db: Annotated[AsyncSession, Depends(get_db)],
    login_data: UserLoginRequestSchema,
    jwt_auth_manager: Annotated[JWTAuthManagerInterface, Depends(get_jwt_auth_manager)],
    settings: Annotated[BaseAppSettings, Depends(get_settings)]
):
    return await login_user(
        db=db,
        login_data=login_data,
        jwt_auth_manager=jwt_auth_manager,
        settings=settings
    )


@router.post(
    "/accounts/logout",
    status_code=status.HTTP_200_OK,
    response_model=MessageResponseSchema
)
async def logout(
    db: Annotated[AsyncSession, Depends(get_db)],
    logout_data: LogoutRequestSchema,
):
    return await revoke_refresh_token(
        db=db,
        logout_data=logout_data
    )

@router.post(
    "/accounts/refresh",
    status_code=status.HTTP_200_OK,
    response_model=TokenRefreshResponseSchema,
    responses={
        400: {
            "description": "Bad Request - The provided refresh token is invalid or expired.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Token has expired."
                    }
                }
            },
        },
        401: {
            "description": "Unauthorized - Refresh token not found.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Refresh token not found."
                    }
                }
            },
        },
        404: {
            "description": "Not Found - The user associated with the token does not exist.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "User not found."
                    }
                }
            },
        },
    }
)
async def refresh(
    db: Annotated[AsyncSession, Depends(get_db)],
    jwt_auth_manager: Annotated[JWTAuthManagerInterface, Depends(get_jwt_auth_manager)],
    request_refresh_token_data: TokenRefreshRequestSchema,
):
    return await refresh_access_token(
        db=db,
        jwt_auth_manager=jwt_auth_manager,
        request_refresh_token_data=request_refresh_token_data
    )


@router.get(
    "/accounts/me",
    status_code=status.HTTP_200_OK,
    response_model=UserResponseSchema
)
async def read_me(
    current_user: Annotated[UserModel, Depends(get_current_user)]
):

    return UserResponseSchema(
        id=current_user.id,
        email=current_user.email,
        is_active=current_user.is_active,
        group=current_user.group.name,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        profile=current_user.profile
    )


@router.post(
    "/accounts/password-reset/request",
    status_code=status.HTTP_200_OK,
    response_model=MessageResponseSchema,
    responses={

    }
)
async def request_password_reset(
    db: Annotated[AsyncSession, Depends(get_db)],
    email_sender: Annotated[EmailSenderInterface, Depends(get_email_sender)],
    reset_password_data: PasswordResetRequestSchema
):
    return await request_user_password_reset(
        db=db,
        email_sender=email_sender,
        reset_password_data=reset_password_data
    )


@router.post(
    "/accounts/password-reset/complete",
    status_code=status.HTTP_200_OK,
    response_model=MessageResponseSchema,
    responses={
        400: {
            "description": (
                "Bad Request - The provided email or token is invalid, "
                "the token has expired, or the user account is not active."
            ),
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_email_or_token": {
                            "summary": "Invalid Email or Token",
                            "value": {
                                "detail": "Invalid email or token."
                            }
                        },
                        "expired_token": {
                            "summary": "Expired Token",
                            "value": {
                                "detail": "Invalid email or token."
                            }
                        }
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while resetting the password.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while resetting the password."
                    }
                }
            },
        },
    }
)
async def reset_password(
    db: Annotated[AsyncSession, Depends(get_db)],
    email_sender: Annotated[EmailSenderInterface, Depends(get_email_sender)],
    reset_password_data: PasswordResetCompleteRequestSchema
):
    return await reset_user_password(
        db=db,
        email_sender=email_sender,
        reset_password_data=reset_password_data
    )


@router.post(
    "/accounts/change-password",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK
)
async def change_user_password(
    db: Annotated[AsyncSession, Depends(get_db)],
    jwt_auth_manager: Annotated[JWTAuthManagerInterface, Depends(get_jwt_auth_manager)],
    change_password_data: PasswordChangeRequestSchema,
    token: Annotated[str, Depends(get_token)],
):
    return await change_password(
        db=db,
        jwt_auth_manager=jwt_auth_manager,
        change_password_data=change_password_data,
        token=token
    )

@router.patch(
    "/accounts/admin/users/{user_id}/group",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK
)
async def change_user_group(
    db: Annotated[AsyncSession, Depends(get_db)],
    change_group_data: ChangeUserGroupRequestSchema,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    user_id: int
):
    return await change_user_group_from_admin(
        db=db,
        change_group_data=change_group_data,
        current_user=current_user,
        user_id=user_id
    )

@router.patch(
    "/accounts/admin/users/{user_id}/activate",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK
)
async def activate_deactivate_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    activation_data: UserActiveDeactivateStatusRequestSchema,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    user_id: int
):
    return await activate_deactivate_user_manually(
        db=db,
        activation_data=activation_data,
        current_user=current_user,
        user_id=user_id
    )


