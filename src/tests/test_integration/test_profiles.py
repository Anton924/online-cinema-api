import io
from datetime import date, timedelta
from unittest.mock import patch
from sqlalchemy import select
import pytest
from PIL import Image

from database.models.accounts import UserGroupEnum, UserModel, UserGroup, UserProfileModel
from sqlalchemy.exc import SQLAlchemyError

from tests.doubles.fakes.storage import FakeS3Storage

from exceptions.storages import S3FileUploadError


async def make_image_bytes(fmt="JPEG", size=(10, 10)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size=size, color="red").save(buffer, format=fmt)
    return buffer.getvalue()


async def create_active_user_with_token(db_session, jwt_manager, group=UserGroupEnum.USER):
    group_row = (await db_session.execute(select(UserGroup).where(UserGroup.name == group))).scalars().first()
    user = UserModel.create(
        email="user@example.com",
        raw_password="StrongPassword123!",
        group_id=group_row.id
    )
    user.is_active = True
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    access_token = jwt_manager.create_access_token(data={"user_id": user.id})
    return user, access_token


async def create_profile_for_user(db_session, user, **fields):
    profile = UserProfileModel(user_id=user.id, **fields)
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)
    return profile


@pytest.mark.asyncio
async def test_create_profile_success_no_avatar(client, db_session, jwt_manager, seed_user_groups):
    profile_data = {
        "first_name": "John",
        "last_name": "Doe",
        "gender": "man",
        "date_of_birth": "1990-05-20",
        "info": "Movie enthusiast and part-time critic."
    }

    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    response = await client.post("/api/v1/profiles/me", data=profile_data, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"
    assert response.json()["first_name"] == profile_data["first_name"], "Returned first name does not match the one sent."
    assert response.json()["last_name"] == profile_data["last_name"], "Returned last name does not match the one sent."
    assert response.json()["gender"] == profile_data["gender"], "Returned gender does not match the one sent."
    assert response.json()["date_of_birth"] == profile_data["date_of_birth"], "Returned date of birth does not match the one sent."
    assert response.json()["info"] == profile_data["info"], "Returned info does not match the one sent."
    assert response.json()["avatar"] is None, "Avatar should be null when none was uploaded."
    profile_record = (await db_session.execute(select(UserProfileModel).where(UserProfileModel.user_id == user.id))).scalars().first()
    assert profile_record is not None, "Profile was not created in the database."


@pytest.mark.asyncio
async def test_create_profile_success_with_avatar(client, db_session, jwt_manager, s3_storage_fake, seed_user_groups):
    profile_data = {
        "first_name": "John",
        "last_name": "Doe",
        "gender": "man",
        "date_of_birth": "1990-05-20",
        "info": "Movie enthusiast and part-time critic."
    }
    img_bytes = await make_image_bytes()
    file = {"avatar": ("avatar.jpg", img_bytes, "image/jpeg")}
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    avatar_key = f"avatar/{user.id}.jpeg"
    avatar_url = await s3_storage_fake.get_file_url(file_name=avatar_key)
    response = await client.post("/api/v1/profiles/me", data=profile_data, headers={"Authorization": f"Bearer {access_token}"}, files=file)
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"
    assert response.json()["avatar"] == avatar_url, "Returned avatar URL does not match the fake storage key."


@pytest.mark.asyncio
async def test_create_profile_inactive_user(client, db_session, jwt_manager, s3_storage_fake, seed_user_groups):
    group_row = (await db_session.execute(select(UserGroup).where(UserGroup.name == UserGroupEnum.USER))).scalars().first()
    user = UserModel.create(
        email="user@example.com",
        raw_password="StrongPassword123!",
        group_id=group_row.id
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    access_token = jwt_manager.create_access_token(data={"user_id": user.id})

    profile_data = {
        "first_name": "John",
        "last_name": "Doe",
        "gender": "man",
        "date_of_birth": "1990-05-20",
        "info": "Movie enthusiast and part-time critic."
    }
    img_bytes = await make_image_bytes()
    file = {"avatar": ("avatar.jpg", img_bytes, "image/jpeg")}
    response = await client.post("/api/v1/profiles/me", data=profile_data, headers={"Authorization": f"Bearer {access_token}"}, files=file)
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    assert response.json()["detail"] == "User is not active" , "Unexpected error message for an inactive user."


@pytest.mark.asyncio
async def test_create_profile_conflict(client, db_session, jwt_manager, s3_storage_fake, seed_user_groups):
    img_bytes = await make_image_bytes()
    file = {"avatar": ("avatar.jpg", img_bytes, "image/jpeg")}
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    await create_profile_for_user(db_session=db_session, user=user)
    response = await client.post("/api/v1/profiles/me", headers={"Authorization": f"Bearer {access_token}"}, files=file)
    assert response.status_code == 409, f"Expected 409, got {response.status_code}"
    assert response.json()["detail"] == "Profile for this user already exists.", "Unexpected conflict error message."


@pytest.mark.asyncio
async def test_create_profile_invalid_gender(client, db_session, jwt_manager, s3_storage_fake, seed_user_groups):
    profile_data = {
        "gender": "other"
    }
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    response = await client.post("/api/v1/profiles/me", data=profile_data, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 422, f"Expected 422, got {response.status_code}"
    assert "Gender must be one of" in str(response.json()), "Unexpected validation error for an invalid gender."


@pytest.mark.asyncio
async def test_create_profile_underage(client, db_session, jwt_manager, s3_storage_fake, seed_user_groups):
    profile_data = {
        "date_of_birth": (date.today() - timedelta(days=365 * 10)).isoformat()
    }
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    response = await client.post("/api/v1/profiles/me", data=profile_data, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 422, f"Expected 422, got {response.status_code}"
    assert "You must be at least 18 years old" in str(response.json()), "Unexpected validation error for an underage date of birth."


@pytest.mark.asyncio
async def test_create_profile_birth_year_too_old(client, db_session, jwt_manager, s3_storage_fake, seed_user_groups):
    profile_data = {
        "date_of_birth": "1899-01-01"
    }
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    response = await client.post("/api/v1/profiles/me", data=profile_data, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 422, f"Expected 422, got {response.status_code}"
    assert "year must be greater than 1900" in str(response.json()), "Unexpected validation error for a pre-1900 birth date."


@pytest.mark.asyncio
async def test_create_profile_unsupported_avatar_format(client, db_session, jwt_manager, s3_storage_fake, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    img_bytes = await make_image_bytes(fmt="GIF")
    file = {"avatar": ("avatar.gif", img_bytes, "image/gif")}
    response = await client.post("/api/v1/profiles/me", headers={"Authorization": f"Bearer {access_token}"}, files=file)
    assert response.status_code == 422, f"Expected 422, got {response.status_code}"
    assert "Unsupported image format" in str(response.json()), "Unexpected validation error for an unsupported format."


@pytest.mark.asyncio
async def test_create_profile_avatar_too_large(client, db_session, jwt_manager, s3_storage_fake, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)

    file = {"avatar": ("avatar.jpg", b"0" * (1024 * 1024 + 1), "image/jpeg")}
    response = await client.post("/api/v1/profiles/me", headers={"Authorization": f"Bearer {access_token}"}, files=file)
    assert response.status_code == 422, f"Expected 422, got {response.status_code}"
    assert "Image size exceeds 1 MB" in str(response.json()), "Unexpected validation error for an oversized avatar."


@pytest.mark.asyncio
async def test_create_profile_avatar_upload_error(client, db_session, jwt_manager, s3_storage_fake, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)

    with patch.object(FakeS3Storage, "upload_file", side_effect=S3FileUploadError):
        img_bytes = await make_image_bytes(fmt="JPEG")
        file = {"avatar": ("avatar.jpg", img_bytes, "image/jpeg")}
        response = await client.post("/api/v1/profiles/me", headers={"Authorization": f"Bearer {access_token}"}, files=file)
        assert response.status_code == 500, f"Expected 500, got {response.status_code}"
        assert response.json()["detail"] == "Failed to upload avatar. Please try again later.", "Unexpected error message for a failed avatar upload."


@pytest.mark.asyncio
async def test_create_profile_commit_error(client, db_session, jwt_manager, s3_storage_fake, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)

    with patch("routes.profiles.AsyncSession.commit", side_effect=SQLAlchemyError):
        img_bytes = await make_image_bytes(fmt="JPEG")
        file = {"avatar": ("avatar.jpg", img_bytes, "image/jpeg")}
        response = await client.post("/api/v1/profiles/me", headers={"Authorization": f"Bearer {access_token}"}, files=file)
        assert response.status_code == 500, f"Expected 500, got {response.status_code}"
        assert response.json()["detail"] == "An error occurred while creating the profile.", "Unexpected error message for a commit failure."


@pytest.mark.asyncio
async def test_read_own_profile_success(client, db_session, jwt_manager, seed_user_groups):
    profile_data = {
        "first_name": "John"
    }

    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    await create_profile_for_user(db_session=db_session, user=user, **profile_data)
    response = await client.get("/api/v1/profiles/me", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["first_name"] == profile_data["first_name"], "Returned first name does not match the one sent."
    assert response.json()["avatar"] is None, "Avatar should be null when none was uploaded."


@pytest.mark.asyncio
async def test_read_own_profile_with_avatar(client, db_session, jwt_manager, seed_user_groups, s3_storage_fake):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    img_bytes = await make_image_bytes(fmt="JPEG")
    file = {"avatar": ("avatar.jpg", img_bytes, "image/jpeg")}
    response = await client.post("/api/v1/profiles/me", headers={"Authorization": f"Bearer {access_token}"}, files=file)
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"
    avatar_key = f"avatar/{user.id}.jpeg"
    avatar_url = await s3_storage_fake.get_file_url(file_name=avatar_key)
    response = await client.get("/api/v1/profiles/me", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["avatar"] == avatar_url, "Returned avatar URL does not match the fake storage key."


@pytest.mark.asyncio
async def test_read_own_profile_not_found(client, db_session, jwt_manager, seed_user_groups, s3_storage_fake):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)

    response = await client.get("/api/v1/profiles/me", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    assert response.json()["detail"] == "Profile not found.", "Unexpected error message for a missing profile."


@pytest.mark.asyncio
async def test_update_profile_success(client, db_session, jwt_manager, seed_user_groups):
    profile_data = {
        "first_name": "John",
        "last_name": "Doe",
        "gender": "man",
        "date_of_birth": date(year=1990, month=5, day=20),
        "info": "Movie enthusiast and part-time critic."
    }
    update_data = {
        "first_name": "Jane",
        "last_name": "Smith",
        "gender": "woman",
        "date_of_birth": "1995-03-15",
        "info": "Now writes reviews full-time."
    }

    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    await create_profile_for_user(db_session=db_session, user=user, **profile_data)
    response = await client.patch("/api/v1/profiles/me", json=update_data, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["first_name"] == update_data["first_name"], "Updated field was not returned."
    assert response.json()["last_name"] == update_data["last_name"], "Updated field was not returned."
    assert response.json()["gender"] == update_data["gender"], "Updated field was not returned."
    assert response.json()["date_of_birth"] == update_data["date_of_birth"], "Updated field was not returned."
    assert response.json()["info"] == update_data["info"], "Updated field was not returned."
    assert response.json()["avatar"] is None, "Avatar should be null when none was uploaded."


@pytest.mark.asyncio
async def test_update_profile_partial(client, db_session, jwt_manager, seed_user_groups):
    profile_data = {
        "first_name": "John",
        "last_name": "Doe",
        "gender": "man",
        "date_of_birth": date(year=1990, month=5, day=20),
        "info": "Movie enthusiast and part-time critic."
    }
    update_data = {
        "first_name": "Jane",
        "last_name": "Smith",
    }

    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    await create_profile_for_user(db_session=db_session, user=user, **profile_data)
    response = await client.patch("/api/v1/profiles/me", json=update_data, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["first_name"] == update_data["first_name"], "Sent field was not updated."
    assert response.json()["last_name"] == update_data["last_name"], "Sent field was not updated."
    assert response.json()["gender"] == profile_data["gender"], "Field that was not sent should stay unchanged."
    assert response.json()["date_of_birth"] == profile_data["date_of_birth"].isoformat(), "Field that was not sent should stay unchanged."
    assert response.json()["info"] == profile_data["info"], "Field that was not sent should stay unchanged."
    assert response.json()["avatar"] is None, "Avatar should be null when none was uploaded."


@pytest.mark.asyncio
async def test_update_profile_not_found(client, db_session, jwt_manager, seed_user_groups):
    update_data = {
        "first_name": "Jane",
        "last_name": "Smith",
    }

    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    response = await client.patch("/api/v1/profiles/me", json=update_data, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    assert response.json()["detail"] == "Profile not found.", "Unexpected error message for a missing profile."


@pytest.mark.asyncio
async def test_update_profile_invalid_gender(client, db_session, jwt_manager, seed_user_groups):
    profile_data = {
        "first_name": "John",
        "last_name": "Doe",
        "gender": "man",
        "date_of_birth": date(year=1990, month=5, day=20),
        "info": "Movie enthusiast and part-time critic."
    }
    update_data = {
        "gender": "other",
    }

    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    await create_profile_for_user(db_session=db_session, user=user, **profile_data)
    response = await client.patch("/api/v1/profiles/me", json=update_data, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 422, f"Expected 422, got {response.status_code}"
    assert "Gender must be one of" in str(response.json()), "Unexpected validation error for an invalid gender."



@pytest.mark.asyncio
async def test_update_profile_commit_error(client, db_session, jwt_manager, s3_storage_fake, seed_user_groups):
    update_data = {
        "first_name": "Jane",
        "last_name": "Smith",
    }
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    await create_profile_for_user(db_session=db_session, user=user)

    with patch("routes.profiles.AsyncSession.commit", side_effect=SQLAlchemyError):
        response = await client.patch("/api/v1/profiles/me", json=update_data, headers={"Authorization": f"Bearer {access_token}"})
        assert response.status_code == 500, f"Expected 500, got {response.status_code}"
        assert response.json()["detail"] == "An error occurred while updating the profile.", "Unexpected error message for a commit failure."


@pytest.mark.asyncio
async def test_update_avatar_success(client, db_session, jwt_manager, s3_storage_fake, seed_user_groups):
    profile_data = {
        "first_name": "John",
        "last_name": "Doe",
        "gender": "man",
        "date_of_birth": date(year=1990, month=5, day=20),
        "info": "Movie enthusiast and part-time critic."
    }
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    await create_profile_for_user(db_session=db_session, user=user, **profile_data)

    img_bytes = await make_image_bytes()
    new_file = {"avatar": ("new_avatar.jpg", img_bytes, "image/jpeg")}
    new_avatar_key = f"avatar/{user.id}.jpeg"
    new_avatar_url = await s3_storage_fake.get_file_url(file_name=new_avatar_key)
    response = await client.patch("/api/v1/profiles/me/avatar", files=new_file, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["avatar"] == new_avatar_url, "Returned avatar URL does not match the fake storage key."



@pytest.mark.asyncio
async def test_update_avatar_profile_not_found(client, db_session, jwt_manager, s3_storage_fake, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)

    img_bytes = await make_image_bytes()
    new_file = {"avatar": ("new_avatar.jpg", img_bytes, "image/jpeg")}
    response = await client.patch("/api/v1/profiles/me/avatar", files=new_file, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    assert response.json()["detail"] == "Profile not found.", "Unexpected error message for a missing profile."


@pytest.mark.asyncio
async def test_update_avatar_invalid_image_size(client, db_session, jwt_manager, s3_storage_fake, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)

    new_file = {"avatar": ("new_avatar.jpg", b"0" * (1024 * 1024 + 1), "image/jpeg")}
    response = await client.patch("/api/v1/profiles/me/avatar", files=new_file, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 422, f"Expected 422, got {response.status_code}"
    assert "Image size exceeds 1 MB" in str(response.json()), "Unexpected validation error for an oversized avatar."


@pytest.mark.asyncio
async def test_update_avatar_invalid_image_format(client, db_session, jwt_manager, s3_storage_fake, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)

    img_bytes = await make_image_bytes(fmt="GIF")
    new_file = {"avatar": ("new_avatar.gif", img_bytes, "image/gif")}
    response = await client.patch("/api/v1/profiles/me/avatar", files=new_file, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 422, f"Expected 422, got {response.status_code}"
    assert "Unsupported image format" in str(response.json()), "Unexpected validation error for an unsupported format."


@pytest.mark.asyncio
async def test_update_avatar_upload_error(client, db_session, jwt_manager, s3_storage_fake, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    await create_profile_for_user(db_session=db_session, user=user)

    img_bytes = await make_image_bytes()
    new_file = {"avatar": ("new_avatar.jpeg", img_bytes, "image/jpeg")}
    with patch.object(FakeS3Storage, "upload_file", side_effect=S3FileUploadError):
        response = await client.patch("/api/v1/profiles/me/avatar", files=new_file, headers={"Authorization": f"Bearer {access_token}"})
        assert response.status_code == 500, f"Expected 500, got {response.status_code}"
        assert response.json()["detail"] == "Failed to upload avatar. Please try again later.", "Unexpected error message for a failed avatar upload."


@pytest.mark.asyncio
async def test_update_avatar_commit_error(client, db_session, jwt_manager, s3_storage_fake, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    await create_profile_for_user(db_session=db_session, user=user)

    img_bytes = await make_image_bytes()
    new_file = {"avatar": ("new_avatar.jpeg", img_bytes, "image/jpeg")}
    with patch("routes.profiles.AsyncSession.commit", side_effect=SQLAlchemyError):
        response = await client.patch("/api/v1/profiles/me/avatar", files=new_file, headers={"Authorization": f"Bearer {access_token}"})
        assert response.status_code == 500, f"Expected 500, got {response.status_code}"
        assert response.json()["detail"] == "An error occurred while saving the avatar. Please try again later.", "Unexpected error message for a commit failure."

