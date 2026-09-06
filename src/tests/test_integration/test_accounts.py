from datetime import datetime, timezone, timedelta

import pytest
from unittest.mock import patch
from sqlalchemy import select, delete

from database.models.accounts import UserModel
from database.models.accounts import ActivationTokenModel
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
    assert created_user.is_active == False, "Newly registered user should not be active yet."

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
    assert response.json()["detail"][0]["msg"] == expected_error, f"Expected error message: Value error, {expected_error}"


@pytest.mark.asyncio
async def test_register_commit_error(client, seed_user_groups):
    payload = {
        "email": "testuser@example.com",
        "password": "StrongPassword123!"
    }

    with patch("routes.accounts.AsyncSession.commit", side_effect=SQLAlchemyError):
        response = await client.post("/api/v1/accounts/register", json=payload)

        assert response.status_code == 500, f"Expected 500, got {response.status_code}"
        assert response.json()["detail"] == f"An error occurred during user creation.", "Unexpected error message for a commit failure."


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

    payload_activation = {
        "email": user.email,
        "token": token_record.token
    }
    response = await client.post("/api/v1/accounts/activate", json=payload_activation)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["message"] == "User account activated successfully.", "Unexpected success message."

    await db_session.refresh(user, ["is_active", "activation_token"])
    assert user.is_active == True, "User should be active after successful activation."
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

    stmt = delete(ActivationTokenModel).where(ActivationTokenModel.user_id == user.id)
    result = await db_session.execute(stmt)
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

    payload_activation = {
        "email": user.email,
        "token": token_record.token
    }
    response = await client.post("/api/v1/accounts/activate", json=payload_activation)
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    assert response.json()["detail"] == "User account is already active.", "Unexpected error message for an already-active user."
