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
    "/register",
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
) -> UserRegistrationResponseSchema:
    return await register_user(db=db, user_data=user_data, email_sender=email_sender)


@router.post(
    "/activate",
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
) -> MessageResponseSchema:
    return await activate_user(
        db=db,
        activation_data=activation_data,
        email_sender=email_sender
    )


@router.get(
    "/activate_activation_link/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": "Bad Request - No user with this email exists, the activation token "
                           "is invalid or expired, or the user account is already active.",
            "content": {
                "application/json": {
                    "examples": {
                        "user_not_found": {
                            "summary": "User Not Found",
                            "value": {
                                "detail": "A user with this email test@example.com does not exist."
                            }
                        },
                        "already_active": {
                            "summary": "Account Already Active",
                            "value": {
                                "detail": "User account is already active."
                            }
                        },
                        "invalid_token": {
                            "summary": "Invalid Token",
                            "value": {
                                "detail": "Invalid or expired activation token."
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
) -> MessageResponseSchema:
    return await activate_through_activation_link(
        db=db,
        email=email,
        token=token,
        email_sender=email_sender
    )


@router.post(
    "/resend-activation",
    status_code=status.HTTP_200_OK,
    response_model=MessageResponseSchema,
    responses={
        400: {
            "description": "Bad Request - No user with this email exists, "
                           "or the user account is already active.",
            "content": {
                "application/json": {
                    "examples": {
                        "user_not_found": {
                            "summary": "User Not Found",
                            "value": {
                                "detail": "A user with this email test@example.com does not exist."
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
) -> MessageResponseSchema:
    return await resend_activation_token(
        db=db,
        resend_activation_data=resend_activation_data,
        email_sender=email_sender
    )


@router.post(
    "/login/",
    status_code=status.HTTP_200_OK,
    response_model=TokenPairResponseSchema,
    responses={
        401: {
            "description": "Unauthorized - Invalid email or password, or the account is not activated.",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_credentials": {
                            "summary": "Invalid Credentials",
                            "value": {
                                "detail": "Invalid email or password."
                            }
                        }
                    }
                }
            },
        },
        403: {
            "description": "Forbidden - The user account is not activated.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "User account is not activated."
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error - An error occurred while processing the request.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while processing the request."
                    }
                }
            },
        },
    }
)
async def login(
    db: Annotated[AsyncSession, Depends(get_db)],
    login_data: UserLoginRequestSchema,
    jwt_auth_manager: Annotated[JWTAuthManagerInterface, Depends(get_jwt_auth_manager)],
    settings: Annotated[BaseAppSettings, Depends(get_settings)]
) -> TokenPairResponseSchema:
    return await login_user(
        db=db,
        login_data=login_data,
        jwt_auth_manager=jwt_auth_manager,
        settings=settings
    )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    response_model=MessageResponseSchema,
    responses={
        400: {
            "description": "Bad Request - Refresh token not found.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Refresh token not found."
                    }
                }
            },
        },
    }
)
async def logout(
    db: Annotated[AsyncSession, Depends(get_db)],
    logout_data: LogoutRequestSchema,
) -> MessageResponseSchema:
    return await revoke_refresh_token(
        db=db,
        logout_data=logout_data
    )


@router.post(
    "/refresh",
    status_code=status.HTTP_200_OK,
    response_model=TokenRefreshResponseSchema,
    responses={
        400: {
            "description": (
                "Bad Request - The refresh token is invalid or expired, not found, "
                "or the associated user no longer exists."
            ),
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_or_expired": {
                            "summary": "Invalid Or Expired Token",
                            "value": {
                                "detail": "Token has expired."
                            }
                        },
                        "token_not_found": {
                            "summary": "Refresh Token Not Found",
                            "value": {
                                "detail": "Refresh token not found."
                            }
                        },
                        "user_not_found": {
                            "summary": "Invalid Token",
                            "value": {
                                "detail": "Invalid Token"
                            }
                        },
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
) -> TokenRefreshResponseSchema:
    return await refresh_access_token(
        db=db,
        jwt_auth_manager=jwt_auth_manager,
        request_refresh_token_data=request_refresh_token_data
    )


@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    response_model=UserResponseSchema,
    responses={
        401: {
            "description": "Unauthorized - Missing, invalid, or expired token.",
            "content": {
                "application/json": {
                    "examples": {
                        "missing_header": {
                            "summary": "Missing Authorization Header",
                            "value": {
                                "detail": "Authorization header is missing"
                            }
                        },
                        "invalid_format": {
                            "summary": "Invalid Authorization Format",
                            "value": {
                                "detail": "Invalid Authorization header format. Expected 'Bearer <token>'"
                            }
                        },
                    }
                }
            },
        },
        404: {
            "description": "Not Found - The user associated with the token does not exist.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "User not found"
                    }
                }
            },
        },
    }
)
async def read_me(
    current_user: Annotated[UserModel, Depends(get_current_user)]
) -> UserResponseSchema:
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
    "/password-reset/request",
    status_code=status.HTTP_200_OK,
    response_model=MessageResponseSchema,
    responses={
        500: {
            "description": "Internal Server Error - An error occurred while processing the request.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while processing the request."
                    }
                }
            },
        },
    }
)
async def request_password_reset(
    db: Annotated[AsyncSession, Depends(get_db)],
    email_sender: Annotated[EmailSenderInterface, Depends(get_email_sender)],
    reset_password_data: PasswordResetRequestSchema
) -> MessageResponseSchema:
    return await request_user_password_reset(
        db=db,
        email_sender=email_sender,
        reset_password_data=reset_password_data
    )


@router.post(
    "/password-reset/complete",
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
) -> MessageResponseSchema:
    return await reset_user_password(
        db=db,
        email_sender=email_sender,
        reset_password_data=reset_password_data
    )


@router.post(
    "/change-password",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": "Bad Request - Invalid/expired token, or the old password is incorrect.",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_token": {
                            "summary": "Invalid Token",
                            "value": {
                                "detail": "Invalid token."
                            }
                        },
                        "wrong_old_password": {
                            "summary": "Wrong Old Password",
                            "value": {
                                "detail": "Old password is incorrect."
                            }
                        },
                    }
                }
            },
        },
        401: {
            "description": "Unauthorized - Missing/invalid Authorization header, or the user no longer exists.",
            "content": {
                "application/json": {
                    "examples": {
                        "missing_header": {
                            "summary": "Missing Authorization Header",
                            "value": {
                                "detail": "Authorization header is missing"
                            }
                        },
                        "invalid_format": {
                            "summary": "Invalid Authorization Format",
                            "value": {
                                "detail": "Invalid Authorization header format. Expected 'Bearer <token>'"
                            }
                        },
                        "user_not_found": {
                            "summary": "User Not Found",
                            "value": {
                                "detail": "Invalid token!"
                            }
                        },
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
async def change_user_password(
    db: Annotated[AsyncSession, Depends(get_db)],
    jwt_auth_manager: Annotated[JWTAuthManagerInterface, Depends(get_jwt_auth_manager)],
    change_password_data: PasswordChangeRequestSchema,
    token: Annotated[str, Depends(get_token)],
) -> MessageResponseSchema:
    return await change_password(
        db=db,
        jwt_auth_manager=jwt_auth_manager,
        change_password_data=change_password_data,
        token=token
    )


@router.patch(
    "/admin/users/{user_id}/group",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": "Bad Request - Invalid/expired token, or the user is already in the requested group.",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_token": {
                            "summary": "Invalid Token",
                            "value": {
                                "detail": "Invalid token."
                            }
                        },
                        "already_in_group": {
                            "summary": "Already In Group",
                            "value": {
                                "detail": "User is already in the 'admin' group."
                            }
                        },
                    }
                }
            },
        },
        401: {
            "description": "Unauthorized - Missing or invalid Authorization header.",
            "content": {
                "application/json": {
                    "examples": {
                        "missing_header": {
                            "summary": "Missing Authorization Header",
                            "value": {
                                "detail": "Authorization header is missing"
                            }
                        },
                        "invalid_format": {
                            "summary": "Invalid Authorization Format",
                            "value": {
                                "detail": "Invalid Authorization header format. Expected 'Bearer <token>'"
                            }
                        },
                    }
                }
            },
        },
        403: {
            "description": "Forbidden - The requester is not an administrator.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "You do not have permission to perform this action."
                    }
                }
            },
        },
        404: {
            "description": "Not Found - The requester's own account, or the target user id, does not exist.",
            "content": {
                "application/json": {
                    "examples": {
                        "requester_not_found": {
                            "summary": "Requester Not Found",
                            "value": {
                                "detail": "User not found"
                            }
                        },
                        "target_not_found": {
                            "summary": "Target User Not Found",
                            "value": {
                                "detail": "User with id 42 not found."
                            }
                        },
                    }
                }
            },
        },
    }
)
async def change_user_group(
    db: Annotated[AsyncSession, Depends(get_db)],
    change_group_data: ChangeUserGroupRequestSchema,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    user_id: int
) -> MessageResponseSchema:
    return await change_user_group_from_admin(
        db=db,
        change_group_data=change_group_data,
        current_user=current_user,
        user_id=user_id
    )


@router.patch(
    "/admin/users/{user_id}/activate",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": (
                "Bad Request - Invalid/expired token, or the account is already "
                "in the requested activation state."
            ),
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_token": {
                            "summary": "Invalid Token",
                            "value": {
                                "detail": "Invalid token."
                            }
                        },
                        "already_active": {
                            "summary": "Already Active",
                            "value": {
                                "detail": "User account is already active."
                            }
                        },
                        "already_inactive": {
                            "summary": "Already Inactive",
                            "value": {
                                "detail": "User account is already inactive."
                            }
                        },
                    }
                }
            },
        },
        401: {
            "description": "Unauthorized - Missing or invalid Authorization header.",
            "content": {
                "application/json": {
                    "examples": {
                        "missing_header": {
                            "summary": "Missing Authorization Header",
                            "value": {
                                "detail": "Authorization header is missing"
                            }
                        },
                        "invalid_format": {
                            "summary": "Invalid Authorization Format",
                            "value": {
                                "detail": "Invalid Authorization header format. Expected 'Bearer <token>'"
                            }
                        },
                    }
                }
            },
        },
        403: {
            "description": "Forbidden - The requester is not an administrator.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "You do not have permission to perform this action."
                    }
                }
            },
        },
        404: {
            "description": "Not Found - The requester's own account, or the target user id, does not exist.",
            "content": {
                "application/json": {
                    "examples": {
                        "requester_not_found": {
                            "summary": "Requester Not Found",
                            "value": {
                                "detail": "User not found"
                            }
                        },
                        "target_not_found": {
                            "summary": "Target User Not Found",
                            "value": {
                                "detail": "User with id 42 not found."
                            }
                        },
                    }
                }
            },
        },
    }
)
async def activate_deactivate_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    activation_data: UserActiveDeactivateStatusRequestSchema,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    user_id: int
) -> MessageResponseSchema:
    return await activate_deactivate_user_manually(
        db=db,
        activation_data=activation_data,
        current_user=current_user,
        user_id=user_id
    )
