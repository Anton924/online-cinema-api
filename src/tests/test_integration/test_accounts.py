from datetime import datetime, timezone, timedelta

import pytest
from unittest.mock import patch
from sqlalchemy import select, delete, func

from database.models.accounts import UserModel, UserGroup, UserGroupEnum, RefreshTokenModel, ActivationTokenModel, PasswordResetTokenModel
from sqlalchemy.exc import SQLAlchemyError


@pytest.mark.asyncio
async def test_register_success(client, db_session, seed_user_groups):
    payload = {
        "email": "user@example.com",
        "password": "StrongPassword123!"
    }

    response = await client.post("/api/v1/accounts/register", json=payload)
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"
    response_data = response.json()
    assert response_data["email"] == payload["email"], "Returned email does not match the one sent."
    assert "id" in response_data, "Response body should contain the new user's id."

    stmt = select(UserModel).where(UserModel.email == payload["email"])
    result = await db_session.execute(stmt)
    created_user = result.scalars().first()
    assert created_user is not None, "User was not created in the database."
    assert created_user.email == payload["email"]
    assert created_user.is_active is False, "Newly registered user should not be active yet."

    stmt = select(ActivationTokenModel).where(ActivationTokenModel.user_id == created_user.id)
    result = await db_session.execute(stmt)
    token_record = result.scalars().first()
    assert token_record is not None, "Activation token was not created."
    assert token_record.token is not None, "Activation token has no token value."

    expires_at = token_record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    assert expires_at > now, "Activation token should not already be expired."


@pytest.mark.asyncio
async def test_register_conflict(client, db_session, seed_user_groups):
    payload = {
        "email": "user@example.com",
        "password": "StrongPassword123!"
    }

    await client.post("/api/v1/accounts/register", json=payload)
    response = await client.post("/api/v1/accounts/register", json=payload)
    assert response.status_code == 409, f"Expected 409, got {response.status_code}"
    assert response.json()["detail"] == f"A user with this email {payload['email']} already exists.", "Unexpected conflict error message."


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_password, expected_error", [
    ("short", "Value error, Password must contain at least 8 characters."),
    ("NoDigitHere!", "Value error, Password must contain at least one digit."),
    ("nodigitnorupper@", "Value error, Password must contain at least one uppercase letter."),
    ("NOLOWERCASE1@", "Value error, Password must contain at least one lower letter."),
    ("NoSpecial123", "Value error, Password must contain at least one special character: @, $, !, %, *, ?, #, &."),
])
async def test_register_invalid_password(client, seed_user_groups, invalid_password, expected_error):
    payload = {
        "email": "user@example.com",
        "password": invalid_password
    }

    response = await client.post("/api/v1/accounts/register", json=payload)
    assert response.status_code == 422, f"Expected 422, got {response.status_code}"
    assert response.json()["detail"][0]["msg"] == expected_error, f"Expected error message: {expected_error}"


@pytest.mark.asyncio
async def test_register_commit_error(client, seed_user_groups):
    payload = {
        "email": "testuser@example.com",
        "password": "StrongPassword123!"
    }

    with patch("routes.accounts.AsyncSession.commit", side_effect=SQLAlchemyError):
        response = await client.post("/api/v1/accounts/register", json=payload)

        assert response.status_code == 500, f"Expected 500, got {response.status_code}"
        assert response.json()["detail"] == "An error occurred during user creation.", "Unexpected error message for a commit failure."


@pytest.mark.asyncio
async def test_activate_success(client, db_session, seed_user_groups):
    payload = {
        "email": "user@example.com",
        "password": "StrongPassword123!"
    }

    response = await client.post("/api/v1/accounts/register", json=payload)
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"
    stmt = select(UserModel).where(UserModel.email == payload["email"])
    result = await db_session.execute(stmt)
    user = result.scalars().first()
    assert user is not None, "User should exist in the database."
    assert not user.is_active, "User should not be active before activation."

    stmt = select(ActivationTokenModel).where(ActivationTokenModel.user_id == user.id)
    result = await db_session.execute(stmt)
    token_record = result.scalars().first()
    assert token_record is not None, "Activation token was not found for the user."

    payload_activation = {
        "email": user.email,
        "token": token_record.token
    }
    response = await client.post("/api/v1/accounts/activate", json=payload_activation)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["message"] == "User account activated successfully.", "Unexpected success message."

    await db_session.refresh(user, ["is_active", "activation_token"])
    assert user.is_active is True, "User should be active after successful activation."
    assert user.activation_token is None, "Activation token should be deleted after successful activation."


@pytest.mark.asyncio
async def test_activate_expired_token(client, db_session, seed_user_groups):
    payload = {
        "email": "user@example.com",
        "password": "StrongPassword123!"
    }

    response = await client.post("/api/v1/accounts/register", json=payload)
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"

    stmt = select(UserModel).where(UserModel.email == payload["email"])
    result = await db_session.execute(stmt)
    user = result.scalars().first()
    assert user is not None, "User should exist in the database."
    assert not user.is_active, "User should not be active before activation."

    stmt = select(ActivationTokenModel).where(ActivationTokenModel.user_id == user.id)
    result = await db_session.execute(stmt)
    token_record = result.scalars().first()
    assert token_record is not None, "Activation token was not found for the user."
    token_record.expires_at = datetime.now(timezone.utc) - timedelta(days=2)
    await db_session.commit()

    payload_activation = {
        "email": user.email,
        "token": token_record.token
    }
    response = await client.post("/api/v1/accounts/activate", json=payload_activation)
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    assert response.json()["detail"] == "Invalid or expired activation token.", "Unexpected error message for an expired token."

    await db_session.refresh(user, ["activation_token"])
    assert user.activation_token is None, "Expired activation token should be deleted by the route."


@pytest.mark.asyncio
async def test_activate_deleted_token(client, db_session, seed_user_groups):
    payload = {
        "email": "user@example.com",
        "password": "StrongPassword123!"
    }

    response = await client.post("/api/v1/accounts/register", json=payload)
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"

    stmt = select(UserModel).where(UserModel.email == payload["email"])
    result = await db_session.execute(stmt)
    user = result.scalars().first()
    assert user is not None, "User should exist in the database."
    assert not user.is_active, "User should not be active before activation."

    stmt = select(ActivationTokenModel).where(ActivationTokenModel.user_id == user.id)
    result = await db_session.execute(stmt)
    token_record = result.scalars().first()
    assert token_record is not None, "Activation token was not found for the user."

    stmt = delete(ActivationTokenModel).where(ActivationTokenModel.user_id == user.id)
    await db_session.execute(stmt)
    await db_session.commit()

    payload_activation = {
        "email": user.email,
        "token": token_record.token
    }
    response = await client.post("/api/v1/accounts/activate", json=payload_activation)
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    assert response.json()["detail"] == "Invalid or expired activation token.", "Unexpected error message for a missing token."


@pytest.mark.asyncio
async def test_activate_already_active(client, db_session, seed_user_groups):
    payload = {
        "email": "user@example.com",
        "password": "StrongPassword123!"
    }

    response = await client.post("/api/v1/accounts/register", json=payload)
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"

    stmt = select(UserModel).where(UserModel.email == payload["email"])
    result = await db_session.execute(stmt)
    user = result.scalars().first()
    assert user is not None, "User should exist in the database."
    assert not user.is_active, "User should not be active before activation."
    user.is_active = True
    await db_session.commit()
    await db_session.refresh(user)

    stmt = select(ActivationTokenModel).where(ActivationTokenModel.user_id == user.id)
    result = await db_session.execute(stmt)
    token_record = result.scalars().first()
    assert token_record is not None, "Activation token was not found for the user."

    payload_activation = {
        "email": user.email,
        "token": token_record.token
    }
    response = await client.post("/api/v1/accounts/activate", json=payload_activation)
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    assert response.json()["detail"] == "User account is already active.", "Unexpected error message for an already-active user."


@pytest.mark.asyncio
async def test_activate_via_link_success(client, db_session, seed_user_groups):
    payload = {
        "email": "user@example.com",
        "password": "StrongPassword123!"
    }

    response = await client.post("/api/v1/accounts/register", json=payload)
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"

    stmt = select(UserModel).where(UserModel.email == payload["email"])
    result = await db_session.execute(stmt)
    user = result.scalars().first()
    assert user is not None, "User should exist in the database."
    assert not user.is_active, "User should not be active before activation."

    stmt = select(ActivationTokenModel).where(ActivationTokenModel.user_id == user.id)
    result = await db_session.execute(stmt)
    token_record = result.scalars().first()
    assert token_record is not None, "Activation token was not found for the user."

    response = await client.get(f"/api/v1/accounts/activate_activation_link/?email={user.email}&token={token_record.token}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["message"] == "User account activated successfully.", "Unexpected success message."


@pytest.mark.asyncio
async def test_activate_via_link_unknown_email(client, db_session, seed_user_groups):
    payload = {
        "email": "user@example.com",
        "password": "StrongPassword123!"
    }

    response = await client.post("/api/v1/accounts/register", json=payload)
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"

    stmt = select(UserModel).where(UserModel.email == payload["email"])
    result = await db_session.execute(stmt)
    user = result.scalars().first()
    assert user is not None, "User should exist in the database."
    assert not user.is_active, "User should not be active before activation."

    stmt = select(ActivationTokenModel).where(ActivationTokenModel.user_id == user.id)
    result = await db_session.execute(stmt)
    token_record = result.scalars().first()
    assert token_record is not None, "Activation token was not found for the user."
    unknown_email = "unknowen@email.com"

    response = await client.get(f"/api/v1/accounts/activate_activation_link/?email={unknown_email}&token={token_record.token}")
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    assert response.json()["detail"] == f"A user with this email {unknown_email} does not exist.", "Unexpected error message for an unknown email."


@pytest.mark.asyncio
async def test_activate_via_link_already_active(client, db_session, seed_user_groups):
    payload = {
        "email": "user@example.com",
        "password": "StrongPassword123!"
    }

    response = await client.post("/api/v1/accounts/register", json=payload)
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"

    stmt = select(UserModel).where(UserModel.email == payload["email"])
    result = await db_session.execute(stmt)
    user = result.scalars().first()
    assert user is not None, "User should exist in the database."
    assert not user.is_active, "User should not be active before activation."
    user.is_active = True
    await db_session.commit()
    await db_session.refresh(user)

    stmt = select(ActivationTokenModel).where(ActivationTokenModel.user_id == user.id)
    result = await db_session.execute(stmt)
    token_record = result.scalars().first()
    assert token_record is not None, "Activation token was not found for the user."

    response = await client.get(f"/api/v1/accounts/activate_activation_link/?email={user.email}&token={token_record.token}")
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    assert response.json()["detail"] == "User account is already active.", "Unexpected error message for an already-active user."


@pytest.mark.asyncio
async def test_activate_via_link_expired_token(client, db_session, seed_user_groups):
    payload = {
        "email": "user@example.com",
        "password": "StrongPassword123!"
    }

    response = await client.post("/api/v1/accounts/register", json=payload)
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"

    stmt = select(UserModel).where(UserModel.email == payload["email"])
    result = await db_session.execute(stmt)
    user = result.scalars().first()
    assert user is not None, "User should exist in the database."
    assert not user.is_active, "User should not be active before activation."

    stmt = select(ActivationTokenModel).where(ActivationTokenModel.user_id == user.id)
    result = await db_session.execute(stmt)
    token_record = result.scalars().first()
    assert token_record is not None, "Activation token was not found for the user."
    token_record.expires_at = datetime.now(timezone.utc) - timedelta(days=2)
    await db_session.commit()

    response = await client.get(f"/api/v1/accounts/activate_activation_link/?email={user.email}&token={token_record.token}")
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    assert response.json()["detail"] == "Invalid or expired activation token.", "Unexpected error message for an expired/deleted token."


@pytest.mark.asyncio
async def test_activate_via_link_deleted_token(client, db_session, seed_user_groups):
    payload = {
        "email": "user@example.com",
        "password": "StrongPassword123!"
    }

    response = await client.post("/api/v1/accounts/register", json=payload)
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"

    stmt = select(UserModel).where(UserModel.email == payload["email"])
    result = await db_session.execute(stmt)
    user = result.scalars().first()
    assert user is not None, "User should exist in the database."
    assert not user.is_active, "User should not be active before activation."

    stmt = select(ActivationTokenModel).where(ActivationTokenModel.user_id == user.id)
    result = await db_session.execute(stmt)
    token_record = result.scalars().first()
    assert token_record is not None, "Activation token was not found for the user."
    await db_session.delete(token_record)
    await db_session.commit()

    response = await client.get(f"/api/v1/accounts/activate_activation_link/?email={user.email}&token={token_record.token}")
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    assert response.json()["detail"] == "Invalid or expired activation token.", "Unexpected error message for an expired/deleted token."


@pytest.mark.asyncio
async def test_resend_activation_success(client, db_session, seed_user_groups):
    payload = {
        "email": "user@example.com",
        "password": "StrongPassword123!"
    }

    response = await client.post("/api/v1/accounts/register", json=payload)
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"

    stmt = select(UserModel).where(UserModel.email == payload["email"])
    result = await db_session.execute(stmt)
    user = result.scalars().first()
    assert user is not None, "User should exist in the database."
    assert not user.is_active, "User should not be active before activation."

    stmt = select(ActivationTokenModel).where(ActivationTokenModel.user_id == user.id)
    result = await db_session.execute(stmt)
    original_token_record = result.scalars().first()
    assert original_token_record is not None, "Activation token was not found for the user."
    original_token = original_token_record.token

    payload_resend_activation = {
        "email": "user@example.com",
    }

    response = await client.post("/api/v1/accounts/resend-activation", json=payload_resend_activation)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["message"] == "Activation link was send to your email", "Unexpected success message."

    stmt = select(ActivationTokenModel).where(ActivationTokenModel.user_id == user.id).execution_options(
        populate_existing=True
    )
    result = await db_session.execute(stmt)
    new_token_record = result.scalars().first()
    assert original_token != new_token_record.token, "New activation token should differ from the original one."

    stmt = select(func.count(ActivationTokenModel.id)).where(ActivationTokenModel.user_id == user.id)
    token_count = await db_session.scalar(stmt)
    assert token_count == 1, "Only one activation token row should exist per user."


@pytest.mark.asyncio
async def test_resend_activation_unknown_email(client, db_session, seed_user_groups):
    payload = {
        "email": "user@example.com",
        "password": "StrongPassword123!"
    }

    response = await client.post("/api/v1/accounts/register", json=payload)
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"

    stmt = select(UserModel).where(UserModel.email == payload["email"])
    result = await db_session.execute(stmt)
    user = result.scalars().first()
    assert user is not None, "User should exist in the database."
    assert not user.is_active, "User should not be active before activation."

    stmt = select(ActivationTokenModel).where(ActivationTokenModel.user_id == user.id)
    result = await db_session.execute(stmt)
    token_record = result.scalars().first()
    assert token_record is not None, "Activation token was not found for the user."

    payload_unknown_email = {
        "email": "unknown@example.com",
    }

    response = await client.post("/api/v1/accounts/resend-activation", json=payload_unknown_email)
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    assert response.json()["detail"] == f'A user with this email {payload_unknown_email["email"]} does not exist.', "Unexpected error message for an unknown email."


@pytest.mark.asyncio
async def test_resend_activation_already_active(client, db_session, seed_user_groups):
    payload = {
        "email": "user@example.com",
        "password": "StrongPassword123!"
    }

    response = await client.post("/api/v1/accounts/register", json=payload)
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"

    stmt = select(UserModel).where(UserModel.email == payload["email"])
    result = await db_session.execute(stmt)
    user = result.scalars().first()
    assert user is not None, "User should exist in the database."
    assert not user.is_active, "User should not be active before activation."
    user.is_active = True
    await db_session.commit()
    await db_session.refresh(user)

    payload_resend_activation = {
        "email": "user@example.com",
    }

    response = await client.post("/api/v1/accounts/resend-activation", json=payload_resend_activation)
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    assert response.json()["detail"] == "User account is already active.", "Unexpected error message for an already-active user."


@pytest.mark.asyncio
async def test_login_success(client, db_session, seed_user_groups, jwt_manager):
    group = (await db_session.execute(select(UserGroup).where(UserGroup.name == UserGroupEnum.USER))).scalars().first()
    user = UserModel.create(
        email="user@example.com",
        raw_password="StrongPassword123!",
        group_id=group.id
    )
    user.is_active = True
    db_session.add(user)
    await db_session.commit()

    login_payload = {
        "email": "user@example.com",
        "password": "StrongPassword123!"
    }

    response = await client.post("/api/v1/accounts/login/", json=login_payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    response_data = response.json()
    assert response_data["access_token"] is not None, "Access token is missing or empty."
    assert response_data["refresh_token"] is not None, "Refresh token is missing or empty."
    access_token_data = jwt_manager.decode_access_token(response_data["access_token"])
    assert access_token_data["user_id"] == user.id, "Access token does not contain the correct user id."
    refresh_token_data = jwt_manager.decode_refresh_token(response_data["refresh_token"])
    assert refresh_token_data["user_id"] == user.id, "Refresh token does not contain the correct user id."

    stmt = select(RefreshTokenModel).where(RefreshTokenModel.user_id == user.id)
    result = await db_session.execute(stmt)
    refresh_token_record = result.scalars().first()
    assert refresh_token_record is not None, "Refresh token was not stored in the database."
    assert refresh_token_record.token == response_data["refresh_token"], "Stored refresh token does not match the returned one."

    now = datetime.now(timezone.utc)

    if refresh_token_record.expires_at.tzinfo is None:
        refresh_token_record.expires_at = refresh_token_record.expires_at.replace(tzinfo=timezone.utc)

    assert refresh_token_record.expires_at > now, "Refresh token should not already be expired."


@pytest.mark.asyncio
async def test_login_invalid_credentials(client, db_session, seed_user_groups):
    group = (await db_session.execute(select(UserGroup).where(UserGroup.name == UserGroupEnum.USER))).scalars().first()
    user = UserModel.create(
        email="user@example.com",
        raw_password="StrongPassword123!",
        group_id=group.id
    )
    user.is_active = True
    db_session.add(user)
    await db_session.commit()

    invalid_login_payload = {
        "email": "invaliduser@example.com",
        "password": "InvalidStrongPassword123!"
    }

    response = await client.post("/api/v1/accounts/login/", json=invalid_login_payload)
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    assert response.json()["detail"] == "Invalid email or password.", "Unexpected error message for invalid credentials."


@pytest.mark.asyncio
async def test_login_inactive_user(client, db_session, seed_user_groups):
    group = (await db_session.execute(select(UserGroup).where(UserGroup.name == UserGroupEnum.USER))).scalars().first()
    user = UserModel.create(
        email="user@example.com",
        raw_password="StrongPassword123!",
        group_id=group.id
    )
    db_session.add(user)
    await db_session.commit()

    login_payload = {
        "email": "user@example.com",
        "password": "StrongPassword123!"
    }

    response = await client.post("/api/v1/accounts/login/", json=login_payload)
    assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    assert response.json()["detail"] == "User account is not activated.", "Unexpected error message for an inactive user."


@pytest.mark.asyncio
async def test_login_commit_error(client, db_session, seed_user_groups):
    group = (await db_session.execute(select(UserGroup).where(UserGroup.name == UserGroupEnum.USER))).scalars().first()
    user = UserModel.create(
        email="user@example.com",
        raw_password="StrongPassword123!",
        group_id=group.id
    )
    user.is_active = True
    db_session.add(user)
    await db_session.commit()

    with patch("routes.accounts.AsyncSession.commit", side_effect=SQLAlchemyError):
        login_payload = {
            "email": "user@example.com",
            "password": "StrongPassword123!"
        }
        response = await client.post("/api/v1/accounts/login/", json=login_payload)
        assert response.status_code == 500, f"Expected 500, got {response.status_code}"
        assert response.json()["detail"] == "An error occurred while processing the request.", "Unexpected error message for a commit failure."


@pytest.mark.asyncio
async def test_refresh_token_success(client, db_session, seed_user_groups, jwt_manager):
    group = (await db_session.execute(select(UserGroup).where(UserGroup.name == UserGroupEnum.USER))).scalars().first()
    user = UserModel.create(
        email="user@example.com",
        raw_password="StrongPassword123!",
        group_id=group.id
    )
    user.is_active = True
    db_session.add(user)
    await db_session.commit()

    login_payload = {
        "email": "user@example.com",
        "password": "StrongPassword123!"
    }

    response = await client.post("/api/v1/accounts/login/", json=login_payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    refresh_token_payload = {
        "refresh_token": response.json()["refresh_token"]
    }

    response = await client.post("/api/v1/accounts/refresh", json=refresh_token_payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    response_data = response.json()
    assert response_data["access_token"] is not None, "Access token is missing or empty."
    access_token_data = jwt_manager.decode_access_token(response_data["access_token"])
    assert access_token_data["user_id"] == user.id, "Access token does not contain the correct user id."


@pytest.mark.asyncio
async def test_refresh_token_expired(client, db_session, seed_user_groups, jwt_manager):
    group = (await db_session.execute(select(UserGroup).where(UserGroup.name == UserGroupEnum.USER))).scalars().first()
    user = UserModel.create(
        email="user@example.com",
        raw_password="StrongPassword123!",
        group_id=group.id
    )
    user.is_active = True
    db_session.add(user)
    await db_session.commit()

    login_payload = {
        "email": "user@example.com",
        "password": "StrongPassword123!"
    }

    response = await client.post("/api/v1/accounts/login/", json=login_payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    stmt = select(RefreshTokenModel).where(RefreshTokenModel.token == response.json()["refresh_token"])
    result = await db_session.execute(stmt)
    refresh_token = result.scalars().first()
    refresh_token.token = jwt_manager.create_refresh_token(data={"user_id": user.id}, expires_delta=timedelta(days=-2))
    refresh_token.expires_at = datetime.now(timezone.utc) + timedelta(days=-2)
    await db_session.commit()
    await db_session.refresh(refresh_token)

    refresh_token_payload = {
        "refresh_token": refresh_token.token
    }

    response = await client.post("/api/v1/accounts/refresh", json=refresh_token_payload)
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    assert response.json()["detail"] == "Token has expired.", "Unexpected error message for a refresh token missing from the database."


@pytest.mark.asyncio
async def test_refresh_token_not_found(client, db_session, seed_user_groups, jwt_manager):
    group = (await db_session.execute(select(UserGroup).where(UserGroup.name == UserGroupEnum.USER))).scalars().first()
    user = UserModel.create(
        email="user@example.com",
        raw_password="StrongPassword123!",
        group_id=group.id
    )
    user.is_active = True
    db_session.add(user)
    await db_session.commit()

    login_payload = {
        "email": "user@example.com",
        "password": "StrongPassword123!"
    }

    response = await client.post("/api/v1/accounts/login/", json=login_payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    stmt = select(RefreshTokenModel).where(RefreshTokenModel.token == response.json()["refresh_token"])
    result = await db_session.execute(stmt)
    refresh_token = result.scalars().first()
    await db_session.delete(refresh_token)
    await db_session.commit()

    refresh_token_payload = {
        "refresh_token": refresh_token.token
    }

    response = await client.post("/api/v1/accounts/refresh", json=refresh_token_payload)
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    assert response.json()["detail"] == "Refresh token not found.", "Unexpected error message for a refresh token missing from the database."


@pytest.mark.asyncio
async def test_refresh_token_user_not_found(client, db_session, seed_user_groups, jwt_manager):
    token = jwt_manager.create_refresh_token(data={"user_id": 9999})
    token_record = RefreshTokenModel(user_id=9999, expires_at=datetime.now(timezone.utc) + timedelta(days=1), token=token)
    db_session.add(token_record)
    await db_session.commit()

    refresh_token_payload = {
        "refresh_token": token
    }

    response = await client.post("/api/v1/accounts/refresh", json=refresh_token_payload)
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    assert response.json()["detail"] == "Invalid Token", "Unexpected error message when the token's user no longer exists."


@pytest.mark.asyncio
async def test_logout_success(client, db_session, seed_user_groups, jwt_manager):
    group = (await db_session.execute(select(UserGroup).where(UserGroup.name == UserGroupEnum.USER))).scalars().first()
    user = UserModel.create(
        email="user@example.com",
        raw_password="StrongPassword123!",
        group_id=group.id
    )
    user.is_active = True
    db_session.add(user)
    await db_session.commit()

    login_payload = {
        "email": "user@example.com",
        "password": "StrongPassword123!"
    }

    response = await client.post("/api/v1/accounts/login/", json=login_payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    logout_token_payload = {
        "refresh_token": response.json()["refresh_token"]
    }

    response = await client.post("/api/v1/accounts/logout", json=logout_token_payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    await db_session.refresh(user, ["refresh_tokens"])
    response_data = response.json()
    assert response_data["message"] == "You have been successfully log out", "Unexpected success message."
    assert user.refresh_tokens == [], "Refresh token row should be deleted after logout."


@pytest.mark.asyncio
async def test_logout_token_not_found(client, db_session, seed_user_groups):
    group = (await db_session.execute(select(UserGroup).where(UserGroup.name == UserGroupEnum.USER))).scalars().first()
    user = UserModel.create(
        email="user@example.com",
        raw_password="StrongPassword123!",
        group_id=group.id
    )
    user.is_active = True
    db_session.add(user)
    await db_session.commit()

    login_payload = {
        "email": "user@example.com",
        "password": "StrongPassword123!"
    }

    response = await client.post("/api/v1/accounts/login/", json=login_payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    stmt = select(RefreshTokenModel).where(RefreshTokenModel.token == response.json()["refresh_token"])
    result = await db_session.execute(stmt)
    refresh_token = result.scalars().first()
    await db_session.delete(refresh_token)
    await db_session.commit()

    logout_token_payload = {
        "refresh_token": response.json()["refresh_token"]
    }

    response = await client.post("/api/v1/accounts/logout", json=logout_token_payload)
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    assert response.json()["detail"] == "Refresh token not found.", "Unexpected error message for an unknown refresh token."


@pytest.mark.asyncio
async def test_read_me_success(client, db_session, seed_user_groups):
    group = (await db_session.execute(select(UserGroup).where(UserGroup.name == UserGroupEnum.USER))).scalars().first()
    user = UserModel.create(
        email="user@example.com",
        raw_password="StrongPassword123!",
        group_id=group.id
    )
    user.is_active = True
    db_session.add(user)
    await db_session.commit()

    login_payload = {
        "email": "user@example.com",
        "password": "StrongPassword123!"
    }

    response = await client.post("/api/v1/accounts/login/", json=login_payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    response = await client.get("/api/v1/accounts/me", headers={"Authorization": f'Bearer {response.json()["access_token"]}'})

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["id"] == user.id, "Returned id does not match the authenticated user."
    assert response.json()["email"] == user.email, "Returned email does not match the authenticated user."


@pytest.mark.asyncio
async def test_read_me_invalid_header_format(client):
    response = await client.get("/api/v1/accounts/me")
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    assert response.json()["detail"] == "Authorization header is missing", "Unexpected error message for a missing Authorization header."


@pytest.mark.asyncio
async def test_read_me_expired_token(client, db_session, seed_user_groups, jwt_manager):
    group = (await db_session.execute(select(UserGroup).where(UserGroup.name == UserGroupEnum.USER))).scalars().first()
    user = UserModel.create(
        email="user@example.com",
        raw_password="StrongPassword123!",
        group_id=group.id
    )
    user.is_active = True
    db_session.add(user)
    await db_session.commit()

    access_token = jwt_manager.create_access_token(data={"user_id": user.id}, expires_delta=timedelta(days=-2))

    response = await client.get("/api/v1/accounts/me", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    assert response.json()["detail"] == "Token has expired.", "Unexpected error message for an expired token."


@pytest.mark.asyncio
async def test_read_me_user_not_found(client, jwt_manager):
    access_token = jwt_manager.create_access_token(data={"user_id": 9999})

    response = await client.get("/api/v1/accounts/me", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    assert response.json()["detail"] == "User not found", "Unexpected error message when the token's user no longer exists."


@pytest.mark.asyncio
async def test_read_me_invalid_token(client, jwt_manager):
    access_token = "this-is-not-a-valid-token"

    response = await client.get("/api/v1/accounts/me", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    assert response.json()["detail"] == "Invalid token.", "Unexpected error message when the token's not valid"


@pytest.mark.asyncio
async def test_reset_password_success(client, db_session, seed_user_groups, jwt_manager):
    group = (await db_session.execute(select(UserGroup).where(UserGroup.name == UserGroupEnum.USER))).scalars().first()
    user = UserModel.create(
        email="user@example.com",
        raw_password="StrongPassword123!",
        group_id=group.id
    )
    user.is_active = True
    db_session.add(user)
    await db_session.commit()

    reset_password_request_payload = {
        "email": user.email
    }

    response = await client.post("/api/v1/accounts/password-reset/request", json=reset_password_request_payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["message"] == "If you are registered, you will receive an email with instructions.", "Unexpected success message."

    stmt = select(PasswordResetTokenModel).where(PasswordResetTokenModel.user_id == user.id)
    result = await db_session.execute(stmt)
    reset_token_record = result.scalars().first()

    reset_password_complete_payload = {
        "email": user.email,
        "token": reset_token_record.token,
        "new_password": "NewStrongPassword123!"
    }

    response = await client.post("/api/v1/accounts/password-reset/complete", json=reset_password_complete_payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["message"] == "Password was successfully reset!", "Unexpected success message."
    await db_session.refresh(user)
    assert user.verify_password(reset_password_complete_payload["new_password"]) is True


@pytest.mark.asyncio
async def test_reset_password_invalid_email_or_token(client, db_session, seed_user_groups, jwt_manager):
    group = (await db_session.execute(select(UserGroup).where(UserGroup.name == UserGroupEnum.USER))).scalars().first()
    user = UserModel.create(
        email="user@example.com",
        raw_password="StrongPassword123!",
        group_id=group.id
    )
    user.is_active = True
    db_session.add(user)
    await db_session.commit()

    reset_password_request_payload = {
        "email": user.email
    }

    response = await client.post("/api/v1/accounts/password-reset/request", json=reset_password_request_payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["message"] == "If you are registered, you will receive an email with instructions.", "Unexpected success message."

    stmt = select(PasswordResetTokenModel).where(PasswordResetTokenModel.user_id == user.id)
    result = await db_session.execute(stmt)
    reset_token_record = result.scalars().first()

    invalid_email_payload = {
        "email": "invalidemail@example.com",
        "token": reset_token_record.token,
        "new_password": "NewStrongPassword123!"
    }
    response = await client.post("/api/v1/accounts/password-reset/complete", json=invalid_email_payload)
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    assert response.json()["detail"] == "Invalid email or token.", "Unexpected error message."

    invalid_token_payload = {
        "email": "user@example.com",
        "token": "this-is-not-a-valid-token",
        "new_password": "NewStrongPassword123!"
    }
    response = await client.post("/api/v1/accounts/password-reset/complete", json=invalid_token_payload)
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    assert response.json()["detail"] == "Invalid email or token.", "Unexpected error message."


@pytest.mark.asyncio
async def test_reset_password_expired_token(client, db_session, seed_user_groups, jwt_manager):
    group = (await db_session.execute(select(UserGroup).where(UserGroup.name == UserGroupEnum.USER))).scalars().first()
    user = UserModel.create(
        email="user@example.com",
        raw_password="StrongPassword123!",
        group_id=group.id
    )
    user.is_active = True
    db_session.add(user)
    await db_session.commit()

    reset_password_request_payload = {
        "email": user.email
    }

    response = await client.post("/api/v1/accounts/password-reset/request", json=reset_password_request_payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["message"] == "If you are registered, you will receive an email with instructions.", "Unexpected success message."

    stmt = select(PasswordResetTokenModel).where(PasswordResetTokenModel.user_id == user.id)
    result = await db_session.execute(stmt)
    reset_token_record = result.scalars().first()
    reset_token_record.expires_at = datetime.now(timezone.utc) + timedelta(days=-2)
    await db_session.commit()
    await db_session.refresh(reset_token_record)

    expired_token_payload = {
        "email": user.email,
        "token": reset_token_record.token,
        "new_password": "NewStrongPassword123!"
    }
    response = await client.post("/api/v1/accounts/password-reset/complete", json=expired_token_payload)
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    assert response.json()["detail"] == "Invalid email or token.", "Unexpected error message."


@pytest.mark.asyncio
async def test_reset_password_inactive_user(client, db_session, seed_user_groups, jwt_manager):
    group = (await db_session.execute(select(UserGroup).where(UserGroup.name == UserGroupEnum.USER))).scalars().first()
    user = UserModel.create(
        email="user@example.com",
        raw_password="StrongPassword123!",
        group_id=group.id
    )
    db_session.add(user)
    await db_session.commit()

    reset_password_request_payload = {
        "email": user.email
    }

    response = await client.post("/api/v1/accounts/password-reset/request", json=reset_password_request_payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["message"] == "If you are registered, you will receive an email with instructions.", "Unexpected success message."


@pytest.mark.asyncio
async def test_reset_password_commit_error(client, db_session, seed_user_groups):
    group = (await db_session.execute(select(UserGroup).where(UserGroup.name == UserGroupEnum.USER))).scalars().first()
    user = UserModel.create(
        email="user@example.com",
        raw_password="StrongPassword123!",
        group_id=group.id
    )
    user.is_active = True
    db_session.add(user)
    await db_session.commit()

    reset_password_request_payload = {
        "email": user.email
    }

    response = await client.post("/api/v1/accounts/password-reset/request", json=reset_password_request_payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["message"] == "If you are registered, you will receive an email with instructions.", "Unexpected success message."

    stmt = select(PasswordResetTokenModel).where(PasswordResetTokenModel.user_id == user.id)
    result = await db_session.execute(stmt)
    reset_token_record = result.scalars().first()

    reset_password_complete_payload = {
        "email": user.email,
        "token": reset_token_record.token,
        "new_password": "NewStrongPassword123!"
    }
    with patch("routes.accounts.AsyncSession.commit", side_effect=SQLAlchemyError):
        response = await client.post("/api/v1/accounts/password-reset/complete", json=reset_password_complete_payload)
        assert response.status_code == 500, f"Expected 500, got {response.status_code}"
        assert response.json()["detail"] == "An error occurred while resetting the password.", "Unexpected error message for a commit failure."


@pytest.mark.asyncio
async def test_change_password_success(client, db_session, seed_user_groups, jwt_manager):
    group = (await db_session.execute(select(UserGroup).where(UserGroup.name == UserGroupEnum.USER))).scalars().first()
    user = UserModel.create(
        email="user@example.com",
        raw_password="StrongPassword123!",
        group_id=group.id
    )
    user.is_active = True
    db_session.add(user)
    await db_session.commit()

    access_token = jwt_manager.create_access_token({"user_id": user.id})

    payload = {
        "old_password": "StrongPassword123!",
        "new_password": "NewStrongPassword123!"
    }

    response = await client.post("/api/v1/accounts/change-password", json=payload, headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["message"] == "Password was changed successfully!", "Unexpected success message."
    await db_session.refresh(user)
    assert user.verify_password(payload["new_password"]) is True, "Password was not updated in the database."


@pytest.mark.asyncio
async def test_change_password_wrong_old_password(client, db_session, seed_user_groups, jwt_manager):
    group = (await db_session.execute(select(UserGroup).where(UserGroup.name == UserGroupEnum.USER))).scalars().first()
    user = UserModel.create(
        email="user@example.com",
        raw_password="StrongPassword123!",
        group_id=group.id
    )
    user.is_active = True
    db_session.add(user)
    await db_session.commit()

    access_token = jwt_manager.create_access_token({"user_id": user.id})

    payload = {
        "old_password": "WrongOldPassword123!",
        "new_password": "NewStrongPassword123!"
    }

    response = await client.post("/api/v1/accounts/change-password", json=payload, headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    assert response.json()["detail"] == "Old password is incorrect.", "Unexpected success message."


@pytest.mark.asyncio
async def test_change_password_invalid_token(client):
    payload = {
        "old_password": "StrongPassword123!",
        "new_password": "NewStrongPassword123!"
    }

    access_token = "this-is-not-a-valid-token"

    response = await client.post("/api/v1/accounts/change-password", json=payload, headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    assert response.json()["detail"] == "Invalid token.", "Unexpected error message when the token's not valid"


@pytest.mark.asyncio
async def test_change_password_expired_token(client, db_session, seed_user_groups, jwt_manager):
    group = (await db_session.execute(select(UserGroup).where(UserGroup.name == UserGroupEnum.USER))).scalars().first()
    user = UserModel.create(
        email="user@example.com",
        raw_password="StrongPassword123!",
        group_id=group.id
    )
    user.is_active = True
    db_session.add(user)
    await db_session.commit()

    payload = {
        "old_password": "StrongPassword123!",
        "new_password": "NewStrongPassword123!"
    }

    access_token = jwt_manager.create_access_token({"user_id": user.id}, expires_delta=timedelta(days=-2))

    response = await client.post("/api/v1/accounts/change-password", json=payload, headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    assert response.json()["detail"] == "Token has expired.", "Unexpected error message when the token's expired"


@pytest.mark.asyncio
async def test_change_password_user_not_found(client, db_session, seed_user_groups, jwt_manager):
    access_token = jwt_manager.create_access_token({"user_id": 9999})

    payload = {
        "old_password": "StrongPassword123!",
        "new_password": "NewStrongPassword123!"
    }

    response = await client.post("/api/v1/accounts/change-password", json=payload, headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    assert response.json()["detail"] == "Invalid token!", "Unexpected error message when the token's user no longer exists."


@pytest.mark.asyncio
async def test_change_password_commit_error(client, db_session, seed_user_groups, jwt_manager):
    group = (await db_session.execute(select(UserGroup).where(UserGroup.name == UserGroupEnum.USER))).scalars().first()
    user = UserModel.create(
        email="user@example.com",
        raw_password="StrongPassword123!",
        group_id=group.id
    )
    user.is_active = True
    db_session.add(user)
    await db_session.commit()

    payload = {
        "old_password": "StrongPassword123!",
        "new_password": "NewStrongPassword123!"
    }

    access_token = jwt_manager.create_access_token({"user_id": user.id})
    with patch("routes.accounts.AsyncSession.commit", side_effect=SQLAlchemyError):
        response = await client.post("/api/v1/accounts/change-password", json=payload, headers={"Authorization": f"Bearer {access_token}"})

        assert response.status_code == 500, f"Expected 500, got {response.status_code}"
        assert response.json()["detail"] == "An error occurred while resetting the password.", "Unexpected error message for a commit failure."


@pytest.mark.asyncio
async def test_change_user_group_success(client, db_session, seed_user_groups, jwt_manager):
    group_user = (await db_session.execute(select(UserGroup).where(UserGroup.name == UserGroupEnum.USER))).scalars().first()
    target_user = UserModel.create(
        email="user@example.com",
        raw_password="StrongPassword123!",
        group_id=group_user.id
    )
    db_session.add(target_user)

    group_admin = (await db_session.execute(select(UserGroup).where(UserGroup.name == UserGroupEnum.ADMIN))).scalars().first()
    user_admin = UserModel.create(
        email="useradmin@example.com",
        raw_password="StrongPassword123!",
        group_id=group_admin.id
    )
    user_admin.is_active = True
    db_session.add(user_admin)
    await db_session.commit()

    payload = {
        "group": UserGroupEnum.MODERATOR
    }

    access_token = jwt_manager.create_access_token(data={"user_id": user_admin.id})

    response = await client.patch(f"/api/v1/accounts/admin/users/{target_user.id}/group", json=payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["message"] == f'User group was successfully changed to {payload["group"].value!r}.', "Unexpected success message."
    await db_session.refresh(target_user, ["group_id", "group"])
    assert target_user.group.name == UserGroupEnum.MODERATOR, "Target user's group was not updated in the database."


@pytest.mark.asyncio
async def test_change_user_group_forbidden(client, db_session, seed_user_groups, jwt_manager):
    group_user = (await db_session.execute(select(UserGroup).where(UserGroup.name == UserGroupEnum.USER))).scalars().first()
    user_false_admin = UserModel.create(
        email="useradmin@example.com",
        raw_password="StrongPassword123!",
        group_id=group_user.id
    )
    user_false_admin.is_active = True
    db_session.add(user_false_admin)
    await db_session.commit()

    payload = {
        "group": UserGroupEnum.MODERATOR
    }

    access_token = jwt_manager.create_access_token(data={"user_id": user_false_admin.id})
    target_user_id = 9999

    response = await client.patch(f"/api/v1/accounts/admin/users/{target_user_id}/group", json=payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    assert response.json()["detail"] == "You do not have permission to perform this action.", "Unexpected error message for a non-admin caller."


@pytest.mark.asyncio
async def test_change_user_group_already_in_group(client, db_session, seed_user_groups, jwt_manager):
    group_user = (await db_session.execute(select(UserGroup).where(UserGroup.name == UserGroupEnum.USER))).scalars().first()
    target_user = UserModel.create(
        email="user@example.com",
        raw_password="StrongPassword123!",
        group_id=group_user.id
    )
    db_session.add(target_user)

    group_admin = (await db_session.execute(select(UserGroup).where(UserGroup.name == UserGroupEnum.ADMIN))).scalars().first()
    user_admin = UserModel.create(
        email="useradmin@example.com",
        raw_password="StrongPassword123!",
        group_id=group_admin.id
    )
    user_admin.is_active = True
    db_session.add(user_admin)
    await db_session.commit()

    payload = {
        "group": UserGroupEnum.USER
    }

    access_token = jwt_manager.create_access_token(data={"user_id": user_admin.id})

    response = await client.patch(f"/api/v1/accounts/admin/users/{target_user.id}/group", json=payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    assert response.json()["detail"] == f'User is already in the {payload["group"].value!r} group.', "Unexpected error message."


@pytest.mark.asyncio
async def test_change_user_group_target_not_found(client, db_session, seed_user_groups, jwt_manager):
    group_admin = (await db_session.execute(select(UserGroup).where(UserGroup.name == UserGroupEnum.ADMIN))).scalars().first()
    user_admin = UserModel.create(
        email="useradmin@example.com",
        raw_password="StrongPassword123!",
        group_id=group_admin.id
    )
    user_admin.is_active = True
    db_session.add(user_admin)
    await db_session.commit()

    payload = {
        "group": UserGroupEnum.MODERATOR
    }

    access_token = jwt_manager.create_access_token(data={"user_id": user_admin.id})
    target_user_id = 9999

    response = await client.patch(f"/api/v1/accounts/admin/users/{target_user_id}/group", json=payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    assert response.json()["detail"] == f"User with id {target_user_id} not found.", "Unexpected error message."


@pytest.mark.asyncio
async def test_reactivate_user_success(client, db_session, seed_user_groups, jwt_manager):
    group_user = (await db_session.execute(select(UserGroup).where(UserGroup.name == UserGroupEnum.USER))).scalars().first()
    target_user = UserModel.create(
        email="user@example.com",
        raw_password="StrongPassword123!",
        group_id=group_user.id
    )
    db_session.add(target_user)

    group_admin = (await db_session.execute(select(UserGroup).where(UserGroup.name == UserGroupEnum.ADMIN))).scalars().first()
    user_admin = UserModel.create(
        email="useradmin@example.com",
        raw_password="StrongPassword123!",
        group_id=group_admin.id
    )
    user_admin.is_active = True
    db_session.add(user_admin)
    await db_session.commit()

    payload = {
        "is_active": True
    }

    access_token = jwt_manager.create_access_token(data={"user_id": user_admin.id})

    response = await client.patch(f"/api/v1/accounts/admin/users/{target_user.id}/activate-deactivate", json=payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["message"] == "User was successfully activated.", "Unexpected error message."


@pytest.mark.asyncio
async def test_deactivate_user_success(client, db_session, seed_user_groups, jwt_manager):
    group_user = (await db_session.execute(select(UserGroup).where(UserGroup.name == UserGroupEnum.USER))).scalars().first()
    target_user = UserModel.create(
        email="user@example.com",
        raw_password="StrongPassword123!",
        group_id=group_user.id
    )
    target_user.is_active = True
    db_session.add(target_user)

    group_admin = (await db_session.execute(select(UserGroup).where(UserGroup.name == UserGroupEnum.ADMIN))).scalars().first()
    user_admin = UserModel.create(
        email="useradmin@example.com",
        raw_password="StrongPassword123!",
        group_id=group_admin.id
    )
    user_admin.is_active = True
    db_session.add(user_admin)
    await db_session.commit()

    payload = {
        "is_active": False
    }

    access_token = jwt_manager.create_access_token(data={"user_id": user_admin.id})

    response = await client.patch(f"/api/v1/accounts/admin/users/{target_user.id}/activate-deactivate", json=payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["message"] == "User was successfully deactivated.", "Unexpected error message."


@pytest.mark.asyncio
async def test_toggle_active_or_inactive_already_in_state(client, db_session, seed_user_groups, jwt_manager):
    group_user = (await db_session.execute(select(UserGroup).where(UserGroup.name == UserGroupEnum.USER))).scalars().first()
    target_user = UserModel.create(
        email="user@example.com",
        raw_password="StrongPassword123!",
        group_id=group_user.id
    )
    db_session.add(target_user)

    group_admin = (await db_session.execute(select(UserGroup).where(UserGroup.name == UserGroupEnum.ADMIN))).scalars().first()
    user_admin = UserModel.create(
        email="useradmin@example.com",
        raw_password="StrongPassword123!",
        group_id=group_admin.id
    )
    user_admin.is_active = True
    db_session.add(user_admin)
    await db_session.commit()

    payload = {
        "is_active": False
    }

    access_token = jwt_manager.create_access_token(data={"user_id": user_admin.id})

    response = await client.patch(f"/api/v1/accounts/admin/users/{target_user.id}/activate-deactivate", json=payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    assert response.json()["detail"] == "User account is already inactive.", "Unexpected error message."

    target_user.is_active = True
    await db_session.commit()

    payload = {
        "is_active": True
    }

    response = await client.patch(f"/api/v1/accounts/admin/users/{target_user.id}/activate-deactivate", json=payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    assert response.json()["detail"] == "User account is already active.", "Unexpected error message."


@pytest.mark.asyncio
async def test_toggle_active_forbidden(client, db_session, seed_user_groups, jwt_manager):
    group_user = (
        await db_session.execute(select(UserGroup).where(UserGroup.name == UserGroupEnum.USER))).scalars().first()
    user_false_admin = UserModel.create(
        email="useradmin@example.com",
        raw_password="StrongPassword123!",
        group_id=group_user.id
    )
    user_false_admin.is_active = True
    db_session.add(user_false_admin)
    await db_session.commit()

    payload = {
        "is_active": True
    }

    access_token = jwt_manager.create_access_token(data={"user_id": user_false_admin.id})
    target_user_id = 9999

    response = await client.patch(f"/api/v1/accounts/admin/users/{target_user_id}/activate-deactivate", json=payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    assert response.json()["detail"] == "You do not have permission to perform this action.", "Unexpected error message."


@pytest.mark.asyncio
async def test_toggle_active_not_found(client, db_session, seed_user_groups, jwt_manager):
    group_admin = (
        await db_session.execute(select(UserGroup).where(UserGroup.name == UserGroupEnum.ADMIN))).scalars().first()
    user_admin = UserModel.create(
        email="useradmin@example.com",
        raw_password="StrongPassword123!",
        group_id=group_admin.id
    )
    user_admin.is_active = True
    db_session.add(user_admin)
    await db_session.commit()

    payload = {
        "is_active": True
    }

    access_token = jwt_manager.create_access_token(data={"user_id": user_admin.id})
    target_user_id = 9999

    response = await client.patch(f"/api/v1/accounts/admin/users/{target_user_id}/activate-deactivate", json=payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    assert response.json()["detail"] == f"User with id {target_user_id} not found.", "Unexpected error message."
