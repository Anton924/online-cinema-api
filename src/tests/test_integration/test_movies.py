from unittest.mock import patch, AsyncMock

import pytest
from sqlalchemy import select, insert, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from tests.conftest import (
    create_active_user_with_token,
    create_certification_directly,
    create_genre_directly,
    create_star_directly,
    create_director_directly,
    create_movie_full,
    create_order_directly,
    create_comment_directly
)
from database.models.accounts import UserGroupEnum
from database.models.movies import (
    MovieModel,
    GenreModel,
    StarModel,
    DirectorModel,
    FavoriteMovieModel,
    MovieLikeDislikeModel,
    LikeDislikeEnum,
    MovieRateModel,
    MovieCommentModel
)
from database.models.orders import StatusOrderEnum
from tests.doubles.stubs.emails import StubEmailSender



@pytest.mark.asyncio
async def test_create_certification_success(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    certification_payload = {
        "name": "PG-13"
    }

    response = await client.post("/api/v1/movies/certifications", json=certification_payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"
    assert response.json()["name"] == certification_payload["name"], "Returned name does not match the one sent."


@pytest.mark.asyncio
async def test_create_certification_conflict(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    certification_payload = {
        "name": "PG-13"
    }
    certification = await create_certification_directly(db_session, **certification_payload)

    response = await client.post("/api/v1/movies/certifications", json=certification_payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 409, f"Expected 409, got {response.status_code}"
    assert response.json()["detail"] == f"A certification with this name {certification.name!r} already exists.", "Unexpected conflict error message."


@pytest.mark.asyncio
async def test_list_certifications_success(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    await create_certification_directly(db_session, name="PG-13")
    await create_certification_directly(db_session, name="PG-14")

    response = await client.get("/api/v1/movies/certifications", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert len(response.json()) == 2, "Unexpected number of certifications returned."


@pytest.mark.asyncio
async def test_list_certifications_empty(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)

    response = await client.get("/api/v1/movies/certifications", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    assert response.json()["detail"] == "No certifications found.", "Unexpected error message for an empty table."


@pytest.mark.asyncio
async def test_get_certification_success(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    certification = await create_certification_directly(db_session, name="PG-13")

    response = await client.get(f"/api/v1/movies/certifications/{certification.id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"


@pytest.mark.asyncio
async def test_get_certification_not_found(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    fake_certification_id = 9999

    response = await client.get(f"/api/v1/movies/certifications/{fake_certification_id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    assert response.json()["detail"] == f"Certification with id {fake_certification_id} not found.", "Unexpected error message for a missing certification."


@pytest.mark.asyncio
async def test_update_certification_success(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    certification = await create_certification_directly(db_session, name="PG-13")
    certification_update_payload = {
        "name": "New Name"
    }
    response = await client.patch(f"/api/v1/movies/certifications/{certification.id}", json=certification_update_payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["name"] == "New Name", "Name was not updated."


@pytest.mark.asyncio
async def test_update_certification_not_found(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    fake_certification_id = 9999
    certification_update_payload = {
        "name": "New Name"
    }
    response = await client.patch(f"/api/v1/movies/certifications/{fake_certification_id}", json=certification_update_payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    assert response.json()["detail"] == f"Certification with id {fake_certification_id} not found.", "Unexpected error message for a missing certification."


@pytest.mark.asyncio
async def test_update_certification_conflict(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    await create_certification_directly(db_session, name="PG-13")
    certification_2 = await create_certification_directly(db_session, name="R")
    certification_update_payload = {
        "name": "PG-13"
    }
    response = await client.patch(f"/api/v1/movies/certifications/{certification_2.id}", json=certification_update_payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 409, f"Expected 409, got {response.status_code}"
    assert response.json()["detail"] == f"A certification with this name {certification_update_payload["name"]!r} already exists.", "Unexpected conflict error message."


@pytest.mark.asyncio
async def test_delete_certification_success(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    certification = await create_certification_directly(db_session, name="PG-13")

    response = await client.delete(f"/api/v1/movies/certifications/{certification.id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["message"] == f"Certification {certification.name!r} was successfully deleted.", "Unexpected success message."


@pytest.mark.asyncio
async def test_delete_certification_still_assigned(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    certification = await create_certification_directly(db_session, name="PG-13")
    await create_movie_full(db_session, certification=certification)
    response = await client.delete(f"/api/v1/movies/certifications/{certification.id}", headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 409, f"Expected 409, got {response.status_code}"
    assert response.json()["detail"] == f"Cannot delete certification {certification.name!r} - it is still assigned to one or more movies.", "Unexpected conflict error message."



@pytest.mark.asyncio
async def test_create_certification_commit_error(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    certification_payload = {
        "name": "PG-13"
    }
    with patch("routes.movies.AsyncSession.commit", side_effect=SQLAlchemyError):
        response = await client.post("/api/v1/movies/certifications", json=certification_payload, headers={"Authorization": f"Bearer {access_token}"})
        assert response.status_code == 500, f"Expected 500, got {response.status_code}"
        assert response.json()["detail"] == f"An error occurred while creating the certification.", "Unexpected error message for a commit failure."


@pytest.mark.asyncio
async def test_update_certification_commit_error(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    certification = await create_certification_directly(db_session, name="PG-13")
    certification_update_payload = {
        "name": "New Name"
    }
    with patch("routes.movies.AsyncSession.commit", side_effect=SQLAlchemyError):
        response = await client.patch(f"/api/v1/movies/certifications/{certification.id}", json=certification_update_payload, headers={"Authorization": f"Bearer {access_token}"})
        assert response.status_code == 500, f"Expected 500, got {response.status_code}"
        assert response.json()["detail"] == f"An error occurred while updating the certification.", "Unexpected error message for a commit failure."


@pytest.mark.asyncio
async def test_delete_certification_commit_error(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    certification = await create_certification_directly(db_session, name="PG-13")
    with patch("routes.movies.AsyncSession.commit", side_effect=SQLAlchemyError):
        response = await client.delete(f"/api/v1/movies/certifications/{certification.id}", headers={"Authorization": f"Bearer {access_token}"})
        assert response.status_code == 500, f"Expected 500, got {response.status_code}"
        assert response.json()["detail"] == f"An error occurred while deleting the certification.", "Unexpected error message for a commit failure."
