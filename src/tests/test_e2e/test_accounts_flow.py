import pytest
import validators
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from tests.conftest import (
    fetch_latest_email_for,
    parse_email_link,
    create_active_user_with_token,
    create_comment_directly,
    create_movie_full
)

from database.models.accounts import ActivationTokenModel, UserModel, RefreshTokenModel, PasswordResetTokenModel, UserGroupEnum


@pytest.mark.asyncdio
@pytest.mark.e2e
@pytest.mark.order(1)
async def test_01_register(e2e_client, e2e_db_session, reset_db_once_for_e2e, settings, seed_user_groups):
    payload = {"email": "e2e_user@example.com", "password": "StrongPassword123!"}

    response = await e2e_client.post("/api/v1/accounts/register", json=payload)
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"
    assert response.json()["email"] == "e2e_user@example.com", "New account should been created."
    assert response.json()["is_active"] is False, "New account should start inactive."
    message = await fetch_latest_email_for(settings, payload["email"])
    assert message["Content"]["Headers"]["Subject"][0] == "Account Activation", "Unexpected activation email subject."
    email_text, link = parse_email_link(message)
    assert email_text == payload["email"] and validators.url(link), "Activation email content/link is malformed."


@pytest.mark.asyncdio
@pytest.mark.e2e
@pytest.mark.order(2)
async def test_02_activate(e2e_client, e2e_db_session, settings):
    user = (await e2e_db_session.execute(select(UserModel).where(UserModel.email == "e2e_user@example.com"))).scalars().first()
    token_record = (await e2e_db_session.execute(select(ActivationTokenModel).join(UserModel).where(UserModel.email == "e2e_user@example.com"))).scalars().first()
    payload = {"email": "e2e_user@example.com", "token": token_record.token}

    response = await e2e_client.post("/api/v1/accounts/activate", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["message"] == "User account activated successfully.", "User is not active after activation."
    await e2e_db_session.refresh(user)
    assert user.is_active is True, "New account should start inactive."
    message = await fetch_latest_email_for(settings, payload["email"])
    assert message["Content"]["Headers"]["Subject"][0] == "Account Activated Successfully", "Unexpected activation-complete email subject."


@pytest.mark.asyncdio
@pytest.mark.e2e
@pytest.mark.order(3)
async def test_03_login(e2e_client, e2e_db_session, settings, e2e_state):
    payload = {"email": "e2e_user@example.com", "password": "StrongPassword123!"}

    response = await e2e_client.post("/api/v1/accounts/login", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert "access_token" in response.json() and response.json()["token_type"] == "bearer", "Login did not return a usable token pair."
    stored_token = (await e2e_db_session.execute(select(RefreshTokenModel).options(joinedload(RefreshTokenModel.user)).where(RefreshTokenModel.token == response.json()["refresh_token"]))).scalars().first()
    assert stored_token is not None, "Refresh token was not stored in the database."
    assert stored_token.user.email == payload["email"], f"Token's user email has to be {payload['email']}"
    e2e_state["access_token"] = response.json()["access_token"]


@pytest.mark.asyncdio
@pytest.mark.e2e
@pytest.mark.order(4)
async def test_04_request_password_reset(e2e_client, e2e_db_session, settings):
    payload = {"email": "e2e_user@example.com"}

    response = await e2e_client.post("/api/v1/accounts/password-reset/request", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["message"] == "If you are registered, you will receive an email with instructions.", "Unexpected password-reset-request message."
    reset_token_record = (await e2e_db_session.execute(select(PasswordResetTokenModel).join(UserModel).where(UserModel.email == payload["email"]))).scalars().first()
    assert reset_token_record is not None, "Password reset token was not created."
    message = await fetch_latest_email_for(settings, payload["email"])
    assert message["Content"]["Headers"]["Subject"][0] == "Password Reset Request", "Unexpected password-reset email subject."
    email_text, link = parse_email_link(message)
    assert email_text == payload["email"] and validators.url(link), "Reset token email content/link is malformed."


@pytest.mark.asyncdio
@pytest.mark.e2e
@pytest.mark.order(5)
async def test_05_reset_password(e2e_client, e2e_db_session, settings):
    reset_token_record = (await e2e_db_session.execute(select(PasswordResetTokenModel).join(UserModel).where(UserModel.email == "e2e_user@example.com"))).scalars().first()
    payload = {"email": "e2e_user@example.com", "token": reset_token_record.token, "new_password": "NewSecurePassword123!"}

    response = await e2e_client.post("/api/v1/accounts/password-reset/complete", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["message"] == "Password was successfully reset!", "Unexpected password-reset-complete message."
    deleted_token = (await e2e_db_session.execute(select(PasswordResetTokenModel).join(UserModel).where(UserModel.email == payload["email"]))).scalars().first()
    assert deleted_token is None, "Password reset token was not deleted."
    message = await fetch_latest_email_for(settings, payload["email"])
    assert message["Content"]["Headers"]["Subject"][0] == "Your Password Has Been Successfully Reset", "Unexpected reset-complete email subject."


@pytest.mark.asyncdio
@pytest.mark.e2e
@pytest.mark.order(6)
async def test_06_comment_reply_notification(e2e_client, e2e_db_session, settings, jwt_manager):
    user = (await e2e_db_session.execute(select(UserModel).where(UserModel.email == "e2e_user@example.com"))).scalars().first()

    movie = await create_movie_full(db_session=e2e_db_session)
    parent_comment = await create_comment_directly(db_session=e2e_db_session, user_id=user.id, movie_id=movie.id)
    reply_comment_payload = {
        "comment": "Agree!",
        "parent_id": parent_comment.id
    }
    replier, access_token = await create_active_user_with_token(e2e_db_session, jwt_manager, UserGroupEnum.USER, email="replier@example.com")

    response = await e2e_client.post(f"/api/v1/movies/{movie.id}/comments", json=reply_comment_payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["message"] == f"Your comment on {movie.name!r} was successfully added.", "Unexpected success message."
    message = await fetch_latest_email_for(settings, user.email)
    assert message["Content"]["Headers"]["Subject"][0] == f"{replier.email!r} Replied To Your Comment", "Unexpected reset-complete email subject."