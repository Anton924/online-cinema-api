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


@pytest.mark.asyncio
async def test_create_genre_success(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    genre_payload = {
        "name": "Action"
    }

    response = await client.post("/api/v1/movies/genres", json=genre_payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"
    assert response.json()["name"] == genre_payload["name"], "Returned name does not match the one sent."


@pytest.mark.asyncio
async def test_create_genre_conflict(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    genre_payload = {
        "name": "Action"
    }
    genre = await create_genre_directly(db_session, **genre_payload)

    response = await client.post("/api/v1/movies/genres", json=genre_payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 409, f"Expected 409, got {response.status_code}"
    assert response.json()["detail"] == f"A genre with this name {genre.name!r} already exists.", "Unexpected conflict error message."


@pytest.mark.asyncio
async def test_list_genre_success(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    await create_genre_directly(db_session, name="Action")
    await create_genre_directly(db_session, name="Adventure")

    response = await client.get("/api/v1/movies/genres", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert len(response.json()) == 2, "Unexpected number of genres returned."


@pytest.mark.asyncio
async def test_list_genres_empty(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)

    response = await client.get("/api/v1/movies/genres", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    assert response.json()["detail"] == "No genres found.", "Unexpected error message for an empty table."


@pytest.mark.asyncio
async def test_get_genre_success(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    certification = await create_certification_directly(db_session, name="PG-13")
    genre = await create_genre_directly(db_session, name="Action")
    await create_movie_full(db_session, certification=certification, genres=[genre], name="Inception", year=2010, time=148)
    await create_movie_full(db_session, certification=certification, genres=[genre], name="Interstellar", year=2014, time=169)


    response = await client.get(f"/api/v1/movies/genres/{genre.id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["movie_count"] == 2, "Unexpected movie count for the genre."


@pytest.mark.asyncio
async def test_get_genre_not_found(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    fake_genre_id = 9999

    response = await client.get(f"/api/v1/movies/genres/{fake_genre_id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    assert response.json()["detail"] == f"Genre with id {fake_genre_id} not found.", "Unexpected error message for a missing genre."


@pytest.mark.asyncio
async def test_update_genre_success(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    genre = await create_genre_directly(db_session, name="Action")
    genre_update_payload = {
        "name": "New Name"
    }
    response = await client.patch(f"/api/v1/movies/genres/{genre.id}", json=genre_update_payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["name"] == "New Name", "Name was not updated."


@pytest.mark.asyncio
async def test_get_genre_movies_success(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    certification = await create_certification_directly(db_session, name="PG-13")
    genre = await create_genre_directly(db_session, name="Action")

    movie = await create_movie_full(db_session, certification=certification, genres=[genre])
    response = await client.get(f"/api/v1/movies/genres/{genre.id}/movies", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert len(response.json()) == 1, "Unexpected number of movies returned for the genre."
    assert response.json()[0]["name"] == movie.name, "Returned movie does not match the one attached to the genre."


@pytest.mark.asyncio
async def test_get_genre_movies_not_found(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    fake_genre_id = 9999

    response = await client.get(f"/api/v1/movies/genres/{fake_genre_id}/movies", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    assert response.json()["detail"] == f"Genre with id {fake_genre_id} not found.", "Unexpected error message for a missing genre."


@pytest.mark.asyncio
async def test_get_genre_movies_empty(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    genre = await create_genre_directly(db_session, name="Action")
    response = await client.get(f"/api/v1/movies/genres/{genre.id}/movies", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["message"] == f"No movies for {genre.name} genre.", "Unexpected message for a genre with no movies."

@pytest.mark.asyncio
async def test_update_genre_not_found(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    fake_genre_id = 9999
    genre_update_payload = {
        "name": "New Name"
    }
    response = await client.patch(f"/api/v1/movies/genres/{fake_genre_id}", json=genre_update_payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    assert response.json()["detail"] == f"Genre with id {fake_genre_id} not found.", "Unexpected error message for a missing genre."


@pytest.mark.asyncio
async def test_update_genre_conflict(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    await create_genre_directly(db_session, name="Action")
    genre_2 = await create_genre_directly(db_session, name="Adventure")
    genre_update_payload = {
        "name": "Action"
    }
    response = await client.patch(f"/api/v1/movies/genres/{genre_2.id}", json=genre_update_payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 409, f"Expected 409, got {response.status_code}"
    assert response.json()["detail"] == f"A genre with this name {genre_update_payload["name"]!r} already exists.", "Unexpected conflict error message."


@pytest.mark.asyncio
async def test_delete_genre_success(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    genre = await create_genre_directly(db_session, name="Action")

    response = await client.delete(f"/api/v1/movies/genres/{genre.id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["message"] == f"Genre {genre.name!r} was successfully deleted.", "Unexpected success message."


@pytest.mark.asyncio
async def test_create_genre_commit_error(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    genre_payload = {
        "name": "Action"
    }
    with patch("routes.movies.AsyncSession.commit", side_effect=SQLAlchemyError):
        response = await client.post("/api/v1/movies/genres", json=genre_payload, headers={"Authorization": f"Bearer {access_token}"})
        assert response.status_code == 500, f"Expected 500, got {response.status_code}"
        assert response.json()["detail"] == f"An error occurred while creating the genre.", "Unexpected error message for a commit failure."


@pytest.mark.asyncio
async def test_update_genre_commit_error(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    genre = await create_genre_directly(db_session, name="Action")
    genre_update_payload = {
        "name": "New Name"
    }
    with patch("routes.movies.AsyncSession.commit", side_effect=SQLAlchemyError):
        response = await client.patch(f"/api/v1/movies/genres/{genre.id}", json=genre_update_payload, headers={"Authorization": f"Bearer {access_token}"})
        assert response.status_code == 500, f"Expected 500, got {response.status_code}"
        assert response.json()["detail"] == f"An error occurred while updating the genre.", "Unexpected error message for a commit failure."


@pytest.mark.asyncio
async def test_delete_genre_commit_error(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    genre = await create_genre_directly(db_session, name="Action")
    with patch("routes.movies.AsyncSession.commit", side_effect=SQLAlchemyError):
        response = await client.delete(f"/api/v1/movies/genres/{genre.id}", headers={"Authorization": f"Bearer {access_token}"})
        assert response.status_code == 500, f"Expected 500, got {response.status_code}"
        assert response.json()["detail"] == f"An error occurred while deleting the genre.", "Unexpected error message for a commit failure."


@pytest.mark.asyncio
async def test_create_star_success(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    star_payload = {
        "name": "Tom Hardy"
    }

    response = await client.post("/api/v1/movies/stars", json=star_payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"
    assert response.json()["name"] == star_payload["name"], "Returned name does not match the one sent."


@pytest.mark.asyncio
async def test_create_star_conflict(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    star_payload = {
        "name": "Tom Hardy"
    }
    star = await create_star_directly(db_session, **star_payload)

    response = await client.post("/api/v1/movies/stars", json=star_payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 409, f"Expected 409, got {response.status_code}"
    assert response.json()["detail"] == f"A star with this name {star.name!r} already exists.", "Unexpected conflict error message."


@pytest.mark.asyncio
async def test_list_star_success(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    await create_star_directly(db_session, name="Tom Hardy")
    await create_star_directly(db_session, name="Leonardo DiCaprio")

    response = await client.get("/api/v1/movies/stars", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert len(response.json()) == 2, "Unexpected number of stars returned."


@pytest.mark.asyncio
async def test_list_stars_empty(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)

    response = await client.get("/api/v1/movies/stars", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    assert response.json()["detail"] == "No stars found.", "Unexpected error message for an empty table."


@pytest.mark.asyncio
async def test_get_star_success(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    star = await create_star_directly(db_session, name="PG-13")

    response = await client.get(f"/api/v1/movies/stars/{star.id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"


@pytest.mark.asyncio
async def test_get_star_not_found(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    fake_star_id = 9999

    response = await client.get(f"/api/v1/movies/stars/{fake_star_id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    assert response.json()["detail"] == f"Star with id {fake_star_id} not found.", "Unexpected error message for a missing star."


@pytest.mark.asyncio
async def test_update_star_success(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    star = await create_star_directly(db_session, name="Tom Hardy")
    star_update_payload = {
        "name": "New Name"
    }
    response = await client.patch(f"/api/v1/movies/stars/{star.id}", json=star_update_payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["name"] == "New Name", "Name was not updated."


@pytest.mark.asyncio
async def test_update_star_not_found(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    fake_star_id = 9999
    star_update_payload = {
        "name": "New Name"
    }
    response = await client.patch(f"/api/v1/movies/stars/{fake_star_id}", json=star_update_payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    assert response.json()["detail"] == f"Star with id {fake_star_id} not found.", "Unexpected error message for a missing star."


@pytest.mark.asyncio
async def test_update_star_conflict(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    await create_star_directly(db_session, name="Tom Hardy")
    star_2 = await create_star_directly(db_session, name="Leonardo DiCaprio")
    star_update_payload = {
        "name": "Tom Hardy"
    }
    response = await client.patch(f"/api/v1/movies/stars/{star_2.id}", json=star_update_payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 409, f"Expected 409, got {response.status_code}"
    assert response.json()["detail"] == f"A star with this name {star_update_payload["name"]!r} already exists.", "Unexpected conflict error message."


@pytest.mark.asyncio
async def test_delete_star_success(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    star = await create_star_directly(db_session, name="Tom Hardy")

    response = await client.delete(f"/api/v1/movies/stars/{star.id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["message"] == f"Star {star.name!r} was successfully deleted.", "Unexpected success message."


@pytest.mark.asyncio
async def test_create_star_commit_error(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    star_payload = {
        "name": "Tom Hardy"
    }
    with patch("routes.movies.AsyncSession.commit", side_effect=SQLAlchemyError):
        response = await client.post("/api/v1/movies/stars", json=star_payload, headers={"Authorization": f"Bearer {access_token}"})
        assert response.status_code == 500, f"Expected 500, got {response.status_code}"
        assert response.json()["detail"] == f"An error occurred while creating the star.", "Unexpected error message for a commit failure."


@pytest.mark.asyncio
async def test_update_star_commit_error(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    star = await create_star_directly(db_session, name="Tom Hardy")
    star_update_payload = {
        "name": "New Name"
    }
    with patch("routes.movies.AsyncSession.commit", side_effect=SQLAlchemyError):
        response = await client.patch(f"/api/v1/movies/stars/{star.id}", json=star_update_payload, headers={"Authorization": f"Bearer {access_token}"})
        assert response.status_code == 500, f"Expected 500, got {response.status_code}"
        assert response.json()["detail"] == f"An error occurred while updating the star.", "Unexpected error message for a commit failure."


@pytest.mark.asyncio
async def test_delete_star_commit_error(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    star = await create_star_directly(db_session, name="Tom Hardy")
    with patch("routes.movies.AsyncSession.commit", side_effect=SQLAlchemyError):
        response = await client.delete(f"/api/v1/movies/stars/{star.id}", headers={"Authorization": f"Bearer {access_token}"})
        assert response.status_code == 500, f"Expected 500, got {response.status_code}"
        assert response.json()["detail"] == f"An error occurred while deleting the star.", "Unexpected error message for a commit failure."
