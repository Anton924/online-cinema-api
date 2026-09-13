import aioboto3
import pytest
from sqlalchemy import select

from tests.conftest import (
    make_image_bytes
)
from database.models.accounts import ActivationTokenModel, UserModel, RefreshTokenModel, PasswordResetTokenModel


@pytest.mark.asyncdio
@pytest.mark.e2e
@pytest.mark.order(11)
async def test_13_create_profile(e2e_client, e2e_db_session, settings, jwt_manager, e2e_state):
    access_token = e2e_state["access_token"]
    payload = {
        "first_name": "E2E",
        "last_name": "Tester",
        "gender": "man",
        "date_of_birth": "1995-05-20",
        "info": "Created by the e2e suite."
    }


    response = await e2e_client.post("/api/v1/profiles/me", json=payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"
    assert response.json()["avatar"] is None, "A freshly created profile should have no avatar yet."


@pytest.mark.asyncdio
@pytest.mark.e2e
@pytest.mark.order(12)
async def test_14_upload_avatar(e2e_client, e2e_db_session, settings, jwt_manager, e2e_state):
    user = (await e2e_db_session.execute(select(UserModel).where(UserModel.email == "e2e_user@example.com"))).scalars().first()
    access_token = e2e_state["access_token"]
    avatar_bytes = make_image_bytes()
    avatar_file = {
        "avatar": ("avatar.jpeg", avatar_bytes, "image/jpeg")
    }


    response = await e2e_client.patch("/api/v1/profiles/me/avatar", files=avatar_file, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200 and response.json()["avatar"] is not None, "Expected 200 with a real avatar URL."
    session = aioboto3.Session()
    async with session.client(
        "s3",
        endpoint_url=settings.s3_storage_endpoint,
        aws_access_key_id=settings.MINIO_ROOT_USER,
        aws_secret_access_key=settings.MINIO_ROOT_PASSWORD
    ) as s3:
        list_responses = await s3.list_objects_v2(
            Bucket=settings.MINIO_STORAGE,
            Prefix=f"avatar/{user.id}"
        )
    assert "Contents" in list_responses, "Avatar was not found in MinIO!"


@pytest.mark.asyncdio
@pytest.mark.e2e
@pytest.mark.order(13)
async def test_15_delete_avatar(e2e_client, e2e_db_session, settings, jwt_manager, e2e_state):
    user = (await e2e_db_session.execute(select(UserModel).where(UserModel.email == "e2e_user@example.com"))).scalars().first()
    access_token = e2e_state["access_token"]

    response = await e2e_client.delete("/api/v1/profiles/me/avatar", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200 and response.json()["avatar"] is None, "Expected 200 with no avatar."
    session = aioboto3.Session()
    async with session.client(
        "s3",
        endpoint_url=settings.s3_storage_endpoint,
        aws_access_key_id=settings.MINIO_ROOT_USER,
        aws_secret_access_key=settings.MINIO_ROOT_PASSWORD
    ) as s3:
        list_responses = await s3.list_objects_v2(
            Bucket=settings.MINIO_STORAGE,
            Prefix=f"avatar/{user.id}"
        )
    assert "Contents" not in list_responses, "Avatar was found in MinIO!"