from datetime import datetime, timezone, timedelta
from typing import Annotated, cast

from fastapi import Depends, status, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas.accounts import (
    UserRegistrationRequestSchema,
    MessageResponseSchema,
    ResendActivationRequestSchema,
    TokenPairResponseSchema,
    LogoutRequestSchema,
    TokenRefreshRequestSchema,
    TokenRefreshResponseSchema,
    PasswordResetRequestSchema,
    PasswordResetCompleteRequestSchema,
    PasswordChangeRequestSchema,
    UserLoginRequestSchema,
    ChangeUserGroupRequestSchema,
    UserActiveDeactivateStatusRequestSchema
)
from database.models.accounts import (
    UserModel,
    ActivationTokenModel,
    RefreshTokenModel,
    PasswordResetTokenModel,
    UserGroup,
    UserGroupEnum
)
from schemas.accounts import (
    UserRegistrationResponseSchema,
    UserActivationRequestSchema
)
from config.dependencies import (
    get_email_sender,
    get_jwt_auth_manager,
    get_settings
)
from notifications.interfaces import EmailSenderInterface
from sqlalchemy.orm import joinedload
from security.interfaces import JWTAuthManagerInterface
from config.settings import BaseAppSettings
from exceptions import BaseSecurityError
from security import get_token
from security.dependencies import get_current_user


async def register_user(
        db: Annotated[AsyncSession, Depends(get_db)],
        user_data: UserRegistrationRequestSchema,
        email_sender: Annotated[EmailSenderInterface, Depends(get_email_sender)]
) -> UserRegistrationResponseSchema:
    result = await db.execute(select(UserModel).where(UserModel.email == user_data.email))
    user = result.scalars().first()
    if user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A user with this email {user_data.email} already exists."
        )

    user_group = await db.scalars(select(UserGroup).where(UserGroup.name == UserGroupEnum.USER))
    user_group = user_group.first()
    if not user_group:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Default user group not found."
        )
    try:
        new_user = UserModel.create(
            email=user_data.email,
            raw_password=user_data.password,
            group_id=user_group.id
        )
        db.add(new_user)
        await db.flush()

        activation_token = ActivationTokenModel(user_id=new_user.id)
        db.add(activation_token)

        await db.commit()
        await db.refresh(new_user)
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during user creation."
        ) from e
    else:
        activation_link = (
            f"http://127.0.0.1:8000/api/v1/accounts/activate_activation_link/"
            f"?email={new_user.email}&token={activation_token.token}"
        )

        await email_sender.send_activation_email(
            new_user.email,
            activation_link
        )

    return UserRegistrationResponseSchema(
        id=new_user.id,
        email=new_user.email,
        is_active=new_user.is_active,
        created_at=new_user.created_at,
    )


async def activate_user(
        db: Annotated[AsyncSession, Depends(get_db)],
        activation_data: UserActivationRequestSchema,
        email_sender: Annotated[EmailSenderInterface, Depends(get_email_sender)],
) -> MessageResponseSchema:
    result = await db.execute(select(UserModel).where(UserModel.email == activation_data.email))
    user = result.scalars().first()
    stmt = select(ActivationTokenModel).options(
        joinedload(ActivationTokenModel.user)
    ).join(UserModel).where(
        UserModel.email == activation_data.email,
        ActivationTokenModel.token == activation_data.token,
    )

    result = await db.execute(stmt)
    token_record = result.scalars().first()

    now_utc = datetime.now(timezone.utc)
    if not token_record or cast(datetime, token_record.expires_at).replace(tzinfo=timezone.utc) < now_utc:
        if token_record:
            await db.delete(token_record)
            await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired activation token."
        )

    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is already active."
        )

    user.is_active = True
    await db.delete(token_record)
    await db.commit()

    login_link = "http://127.0.0.1:8000/api/v1/accounts/login/"

    await email_sender.send_activation_complete_email(
        email=user.email,
        login_link=login_link
    )

    return MessageResponseSchema(message="User account activated successfully.")


async def activate_through_activation_link(
        db: Annotated[AsyncSession, Depends(get_db)],
        email: str,
        token: str,
        email_sender: Annotated[EmailSenderInterface, Depends(get_email_sender)]
) -> MessageResponseSchema:
    result = await db.execute(select(UserModel).where(UserModel.email == email))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A user with this email {email} does not exist."
        )
    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is already active."
        )

    stmt = select(ActivationTokenModel).options(
        joinedload(ActivationTokenModel.user)
    ).join(UserModel).where(
        UserModel.email == email,
        ActivationTokenModel.token == token,
    )

    result = await db.execute(stmt)
    token_record = result.scalars().first()

    now_utc = datetime.now(timezone.utc)
    if not token_record or cast(datetime, token_record.expires_at).replace(tzinfo=timezone.utc) < now_utc:
        if token_record:
            await db.delete(token_record)
            await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired activation token."
        )

    user.is_active = True
    await db.delete(token_record)
    await db.commit()

    login_link = "http://127.0.0.1:8000/api/v1/accounts/login/"

    await email_sender.send_activation_complete_email(
        email=user.email,
        login_link=login_link
    )

    return MessageResponseSchema(message="User account activated successfully.")


async def resend_activation_token(
    db: Annotated[AsyncSession, Depends(get_db)],
    resend_activation_data: ResendActivationRequestSchema,
    email_sender: Annotated[EmailSenderInterface, Depends(get_email_sender)],
) -> MessageResponseSchema:
    stmt = select(UserModel).where(UserModel.email == resend_activation_data.email)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A user with this email {resend_activation_data.email} does not exist."
        )
    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is already active."
        )

    stmt = select(ActivationTokenModel).options(
        joinedload(ActivationTokenModel.user)
    ).join(UserModel).where(
        UserModel.email == user.email
    )

    result = await db.execute(stmt)
    invalid_token = result.scalars().one_or_none()
    if invalid_token:
        await db.delete(invalid_token)
        await db.commit()

    activation_token = ActivationTokenModel(user_id=user.id)
    db.add(activation_token)
    await db.commit()

    activation_link = (
        f"http://127.0.0.1:8000/api/v1/accounts/activate_activation_link/"
        f"?email={user.email}&token={activation_token.token}"
    )

    await email_sender.send_activation_email(
        email=user.email,
        activation_link=activation_link
    )

    return MessageResponseSchema(
        message="Activation link was send to your email"
    )


async def login_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    login_data: UserLoginRequestSchema,
    jwt_auth_manager: Annotated[JWTAuthManagerInterface, Depends(get_jwt_auth_manager)],
    settings: Annotated[BaseAppSettings, Depends(get_settings)]
) -> TokenPairResponseSchema:
    stmt = select(UserModel).filter_by(email=login_data.email)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user or not user.verify_password(login_data.password, user._hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not activated."
        )

    jwt_refresh_token = jwt_auth_manager.create_refresh_token({"user_id": user.id})

    try:
        refresh_token = RefreshTokenModel(
            user_id=user.id,
            token=jwt_refresh_token,
            expires_at=(datetime.now(timezone.utc) + timedelta(days=settings.LOGIN_TIME_DAYS))
        )
        db.add(refresh_token)
        await db.flush()
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the request.",
        ) from e
    jwt_access_token = jwt_auth_manager.create_access_token({"user_id": user.id})

    return TokenPairResponseSchema(
        access_token=jwt_access_token,
        refresh_token=jwt_refresh_token
    )


async def revoke_refresh_token(
    db: Annotated[AsyncSession, Depends(get_db)],
    logout_data: LogoutRequestSchema,
) -> MessageResponseSchema:
    stmt = select(RefreshTokenModel).where(RefreshTokenModel.token == logout_data.refresh_token)
    result = await db.execute(stmt)
    refresh_token = result.scalars().first()
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token not found."
        )

    await db.delete(refresh_token)
    await db.commit()

    return MessageResponseSchema(
        message="You have been successfully log out"
    )


async def refresh_access_token(
    db: Annotated[AsyncSession, Depends(get_db)],
    jwt_auth_manager: Annotated[JWTAuthManagerInterface, Depends(get_jwt_auth_manager)],
    request_refresh_token_data: TokenRefreshRequestSchema,
) -> TokenRefreshResponseSchema:
    try:
        data_from_token = jwt_auth_manager.decode_refresh_token(request_refresh_token_data.refresh_token)
        user_id = data_from_token.get("user_id")
    except BaseSecurityError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error)
        ) from error

    stmt = select(RefreshTokenModel).where(RefreshTokenModel.token == request_refresh_token_data.refresh_token)
    result = await db.execute(stmt)
    refresh_token = result.scalars().first()
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token not found."
        )

    user = await db.get(UserModel, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Token"
        )

    jwt_access_token = jwt_auth_manager.create_access_token({"user_id": user.id})

    return TokenRefreshResponseSchema(
        access_token=jwt_access_token
    )


async def request_user_password_reset(
    db: Annotated[AsyncSession, Depends(get_db)],
    email_sender: Annotated[EmailSenderInterface, Depends(get_email_sender)],
    reset_password_data: PasswordResetRequestSchema
) -> MessageResponseSchema:
    stmt = select(UserModel).where(UserModel.email == reset_password_data.email)
    result = await db.execute(stmt)
    user = result.scalars().first()
    if not user or not user.is_active:
        return MessageResponseSchema(
            message="If you are registered, you will receive an email with instructions."
        )
    try:
        await db.execute(delete(PasswordResetTokenModel).where(PasswordResetTokenModel.user_id == user.id))
        reset_token = PasswordResetTokenModel(
            user_id=user.id
        )
        db.add(reset_token)
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the request.",
        ) from e

    reset_link = (
        f"http://127.0.0.1:8000/api/v1/accounts/password-reset/complete"
        f"?email={user.email}&token={reset_token.token}"
    )

    await email_sender.send_password_reset_email(
        email=reset_password_data.email,
        reset_link=reset_link
    )

    return MessageResponseSchema(
        message="If you are registered, you will receive an email with instructions."
    )


async def reset_user_password(
    db: Annotated[AsyncSession, Depends(get_db)],
    email_sender: Annotated[EmailSenderInterface, Depends(get_email_sender)],
    reset_password_data: PasswordResetCompleteRequestSchema
) -> MessageResponseSchema:
    stmt = select(UserModel).where(UserModel.email == reset_password_data.email)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or token."
        )

    stmt = select(PasswordResetTokenModel).where(PasswordResetTokenModel.user_id == user.id)
    result = await db.execute(stmt)
    token_record = result.scalars().first()

    if not token_record or token_record.token != reset_password_data.token:
        if token_record:
            await db.delete(token_record)
            await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or token."
        )

    now = datetime.now(timezone.utc)
    expires_at = cast(datetime, token_record.expires_at).replace(tzinfo=timezone.utc)

    if expires_at < now:
        await db.delete(token_record)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or token."
        )

    try:
        user.password = reset_password_data.new_password
        await db.delete(token_record)
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while resetting the password."
        ) from e

    login_link = "http://127.0.0.1:8000/api/v1/accounts/login/"

    await email_sender.send_password_reset_complete_email(
        email=user.email,
        login_link=login_link
    )

    return MessageResponseSchema(
        message="Password was successfully reset!"
    )


async def change_password(
    db: Annotated[AsyncSession, Depends(get_db)],
    jwt_auth_manager: Annotated[JWTAuthManagerInterface, Depends(get_jwt_auth_manager)],
    change_password_data: PasswordChangeRequestSchema,
    token: Annotated[str, Depends(get_token)],
) -> MessageResponseSchema:
    try:
        data_from_token = jwt_auth_manager.decode_access_token(token)
        user_id = data_from_token.get("user_id")
    except BaseSecurityError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error)
        ) from error
    user = await db.get(UserModel, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token!"
        )

    if not user.verify_password(change_password_data.old_password, user._hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Old password is incorrect."
        )

    try:
        user.password = change_password_data.new_password
        db.add(user)
        await db.commit()
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while resetting the password."
        ) from e

    return MessageResponseSchema(
        message="Password was changed successfully!"
    )


async def change_user_group_from_admin(
    db: Annotated[AsyncSession, Depends(get_db)],
    change_group_data: ChangeUserGroupRequestSchema,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    user_id: int
) -> MessageResponseSchema:
    if current_user.group.name != UserGroupEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action."
        )

    result = await db.execute(select(UserModel).options(
        joinedload(UserModel.group)
    ).where(UserModel.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found."
        )

    if user.group.name == change_group_data.group:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User is already in the {change_group_data.group.value!r} group."
        )

    try:
        group = await db.scalar(select(UserGroup).where(UserGroup.name == change_group_data.group))
        user.group = group
        db.add(user)
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An error occurred while changing the group."
        ) from e

    return MessageResponseSchema(
        message=f"User group was successfully changed to {change_group_data.group.value!r}."
    )


async def activate_deactivate_user_manually(
    db: Annotated[AsyncSession, Depends(get_db)],
    activation_data: UserActiveDeactivateStatusRequestSchema,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    user_id: int
) -> MessageResponseSchema:
    if current_user.group.name != UserGroupEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action."
        )

    user = await db.get(UserModel, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found."
        )

    if user.is_active == activation_data.is_active:
        if activation_data.is_active is True:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is already active."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is already inactive."
            )

    try:
        user.is_active = activation_data.is_active
        db.add(user)
        if activation_data.is_active is False:
            await db.execute(delete(RefreshTokenModel).where(RefreshTokenModel.user_id == user.id))
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An error occurred while processing request."
        ) from e

    if activation_data.is_active is False:
        return MessageResponseSchema(
            message="User was successfully deactivated."
        )
    return MessageResponseSchema(
        message="User was successfully activated."
    )
