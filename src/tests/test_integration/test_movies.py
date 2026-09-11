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


@pytest.mark.asyncio
async def test_create_director_success(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    director_payload = {
        "name": "Christopher Nolan"
    }

    response = await client.post("/api/v1/movies/directors", json=director_payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"
    assert response.json()["name"] == director_payload["name"], "Returned name does not match the one sent."


@pytest.mark.asyncio
async def test_create_director_conflict(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    director_payload = {
        "name": "Christopher Nolan"
    }
    director = await create_director_directly(db_session, **director_payload)

    response = await client.post("/api/v1/movies/directors", json=director_payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 409, f"Expected 409, got {response.status_code}"
    assert response.json()["detail"] == f"A director with this name {director.name!r} already exists.", "Unexpected conflict error message."


@pytest.mark.asyncio
async def test_list_director_success(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    await create_director_directly(db_session, name="Christopher Nolan")
    await create_director_directly(db_session, name="Denis Villeneuve")

    response = await client.get("/api/v1/movies/directors", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert len(response.json()) == 2, "Unexpected number of directors returned."


@pytest.mark.asyncio
async def test_list_directors_empty(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)

    response = await client.get("/api/v1/movies/directors", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    assert response.json()["detail"] == "No directors found.", "Unexpected error message for an empty table."


@pytest.mark.asyncio
async def test_get_director_success(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    director = await create_director_directly(db_session, name="PG-13")

    response = await client.get(f"/api/v1/movies/directors/{director.id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"


@pytest.mark.asyncio
async def test_get_director_not_found(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    fake_director_id = 9999

    response = await client.get(f"/api/v1/movies/directors/{fake_director_id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    assert response.json()["detail"] == f"Director with id {fake_director_id} not found.", "Unexpected error message for a missing director."


@pytest.mark.asyncio
async def test_update_director_success(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    director = await create_director_directly(db_session, name="Christopher Nolan")
    director_update_payload = {
        "name": "New Name"
    }
    response = await client.patch(f"/api/v1/movies/directors/{director.id}", json=director_update_payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["name"] == "New Name", "Name was not updated."


@pytest.mark.asyncio
async def test_update_director_not_found(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    fake_director_id = 9999
    director_update_payload = {
        "name": "New Name"
    }
    response = await client.patch(f"/api/v1/movies/directors/{fake_director_id}", json=director_update_payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    assert response.json()["detail"] == f"Director with id {fake_director_id} not found.", "Unexpected error message for a missing director."


@pytest.mark.asyncio
async def test_update_director_conflict(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    await create_director_directly(db_session, name="Christopher Nolan")
    director_2 = await create_director_directly(db_session, name="Denis Villeneuve")
    director_update_payload = {
        "name": "Christopher Nolan"
    }
    response = await client.patch(f"/api/v1/movies/directors/{director_2.id}", json=director_update_payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 409, f"Expected 409, got {response.status_code}"
    assert response.json()["detail"] == f"A director with this name {director_update_payload["name"]!r} already exists.", "Unexpected conflict error message."


@pytest.mark.asyncio
async def test_delete_director_success(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    director = await create_director_directly(db_session, name="Christopher Nolan")

    response = await client.delete(f"/api/v1/movies/directors/{director.id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["message"] == f"Director {director.name!r} was successfully deleted.", "Unexpected success message."


@pytest.mark.asyncio
async def test_create_director_commit_error(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    director_payload = {
        "name": "Christopher Nolan"
    }
    with patch("routes.movies.AsyncSession.commit", side_effect=SQLAlchemyError):
        response = await client.post("/api/v1/movies/directors", json=director_payload, headers={"Authorization": f"Bearer {access_token}"})
        assert response.status_code == 500, f"Expected 500, got {response.status_code}"
        assert response.json()["detail"] == f"An error occurred while creating the director.", "Unexpected error message for a commit failure."



@pytest.mark.asyncio
async def test_update_director_commit_error(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    director = await create_director_directly(db_session, name="Christopher Nolan")
    director_update_payload = {
        "name": "New Name"
    }
    with patch("routes.movies.AsyncSession.commit", side_effect=SQLAlchemyError):
        response = await client.patch(f"/api/v1/movies/directors/{director.id}", json=director_update_payload, headers={"Authorization": f"Bearer {access_token}"})
        assert response.status_code == 500, f"Expected 500, got {response.status_code}"
        assert response.json()["detail"] == f"An error occurred while updating the director.", "Unexpected error message for a commit failure."


@pytest.mark.asyncio
async def test_delete_director_commit_error(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    director = await create_director_directly(db_session, name="Christopher Nolan")
    with patch("routes.movies.AsyncSession.commit", side_effect=SQLAlchemyError):
        response = await client.delete(f"/api/v1/movies/directors/{director.id}", headers={"Authorization": f"Bearer {access_token}"})
        assert response.status_code == 500, f"Expected 500, got {response.status_code}"
        assert response.json()["detail"] == f"An error occurred while deleting the director.", "Unexpected error message for a commit failure."




@pytest.mark.asyncio
async def test_create_movie_success_with_names(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    certification = await create_certification_directly(db_session, name="PG-13")
    movie_payload = {
        "name": "Inception",
        "year": 2010,
        "time": 148,
        "imdb": 8.8,
        "votes": 100,
        "description": "...",
        "price": "9.99",
        "certification_id": certification.id,
        "genre_ids_or_names": ["Sci-Fi"],
        "star_ids_or_names": ["Tom Hardy"],
        "director_ids_or_names": ["Christopher Nolan"]
    }
    response = await client.post(f"/api/v1/movies", json=movie_payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"
    assert response.json()["genres"][0]["name"] == "Sci-Fi", "Genre was not attached to the movie."
    genre_row = (await db_session.execute(select(GenreModel).where(GenreModel.name == "Sci-Fi"))).scalars().first()
    assert genre_row is not None, "A new Genre row should have been created for the unrecognized name."
    star_row = (await db_session.execute(select(StarModel).where(StarModel.name == "Tom Hardy"))).scalars().first()
    assert star_row is not None, "A new Star row should have been created for the unrecognized name."
    director_row = (await db_session.execute(select(DirectorModel).where(DirectorModel.name == "Christopher Nolan"))).scalars().first()
    assert director_row is not None, "A new Star row should have been created for the unrecognized name."


@pytest.mark.asyncio
async def test_create_movie_success_with_ids(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    certification = await create_certification_directly(db_session, name="PG-13")
    genre = await create_genre_directly(db_session=db_session, name="Sci-Fi")
    star = await create_star_directly(db_session=db_session, name="Tom Hardy")
    director = await create_director_directly(db_session=db_session, name="Christopher Nolan")
    movie_payload = {
        "name": "Inception",
        "year": 2010,
        "time": 148,
        "imdb": 8.8,
        "votes": 100,
        "description": "...",
        "price": "9.99",
        "certification_id": certification.id,
        "genre_ids_or_names": [genre.id],
        "star_ids_or_names": [star.id],
        "director_ids_or_names": [director.id]
    }
    response = await client.post(f"/api/v1/movies", json=movie_payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"
    assert response.json()["genres"][0]["name"] == "Sci-Fi", "Genre was not attached to the movie."
    genre_row = (await db_session.execute(select(GenreModel).where(GenreModel.name == "Sci-Fi"))).scalars().first()
    assert genre_row is not None, "A new Genre row should have been created for the unrecognized name."
    star_row = (await db_session.execute(select(StarModel).where(StarModel.name == "Tom Hardy"))).scalars().first()
    assert star_row is not None, "A new Star row should have been created for the unrecognized name."
    director_row = (await db_session.execute(select(DirectorModel).where(DirectorModel.name == "Christopher Nolan"))).scalars().first()
    assert director_row is not None, "A new Star row should have been created for the unrecognized name."


@pytest.mark.asyncio
async def test_create_movie_certification_not_found(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    fake_certification_id = 9999
    movie_payload = {
        "name": "Inception",
        "year": 2010,
        "time": 148,
        "imdb": 8.8,
        "votes": 100,
        "description": "...",
        "price": "9.99",
        "certification_id": fake_certification_id,
        "genre_ids_or_names": ["Sci-Fi"],
        "star_ids_or_names": ["Tom Hardy"],
        "director_ids_or_names": ["Christopher Nolan"]
    }
    response = await client.post(f"/api/v1/movies", json=movie_payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    assert response.json()["detail"] == f"Certification with id {fake_certification_id} not found.", "Unexpected error message."


@pytest.mark.asyncio
async def test_create_movie_genre_id_not_found(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    certification = await create_certification_directly(db_session, name="PG-13")
    fake_genre_id = 9999
    movie_payload = {
        "name": "Inception",
        "year": 2010,
        "time": 148,
        "imdb": 8.8,
        "votes": 100,
        "description": "...",
        "price": "9.99",
        "certification_id": certification.id,
        "genre_ids_or_names": [fake_genre_id],
        "star_ids_or_names": ["Tom Hardy"],
        "director_ids_or_names": ["Christopher Nolan"]
    }
    response = await client.post(f"/api/v1/movies", json=movie_payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    assert response.json()["detail"] == f"Genre with id {fake_genre_id} not found.", "Unexpected error message."


@pytest.mark.asyncio
async def test_create_movie_star_id_not_found(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    certification = await create_certification_directly(db_session, name="PG-13")
    fake_star_id = 9999
    movie_payload = {
        "name": "Inception",
        "year": 2010,
        "time": 148,
        "imdb": 8.8,
        "votes": 100,
        "description": "...",
        "price": "9.99",
        "certification_id": certification.id,
        "genre_ids_or_names": ["Sci-Fi"],
        "star_ids_or_names": [fake_star_id],
        "director_ids_or_names": ["Christopher Nolan"]
    }
    response = await client.post(f"/api/v1/movies", json=movie_payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    assert response.json()["detail"] == f"Star with id {fake_star_id} not found.", "Unexpected error message."


@pytest.mark.asyncio
async def test_create_movie_director_id_not_found(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    certification = await create_certification_directly(db_session, name="PG-13")
    fake_director_id = 9999
    movie_payload = {
        "name": "Inception",
        "year": 2010,
        "time": 148,
        "imdb": 8.8,
        "votes": 100,
        "description": "...",
        "price": "9.99",
        "certification_id": certification.id,
        "genre_ids_or_names": ["Sci-Fi"],
        "star_ids_or_names": ["Tom Hardy"],
        "director_ids_or_names": [fake_director_id]
    }
    response = await client.post(f"/api/v1/movies", json=movie_payload,
                                 headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    assert response.json()["detail"] == f"Director with id {fake_director_id} not found.", "Unexpected error message."


@pytest.mark.asyncio
async def test_create_movie_conflict(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    certification = await create_certification_directly(db_session, name="PG-13")
    await create_movie_full(db_session, certification=certification)
    movie_payload = {
        "name": "Inception",
        "year": 2010,
        "time": 148,
        "imdb": 8.8,
        "votes": 100,
        "description": "...",
        "price": "9.99",
        "certification_id": certification.id,
        "genre_ids_or_names": ["Sci-Fi"],
        "star_ids_or_names": ["Tom Hardy"],
        "director_ids_or_names": ["Christopher Nolan"]
    }
    response = await client.post(f"/api/v1/movies", json=movie_payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 409, f"Expected 409, got {response.status_code}"
    assert response.json()["detail"] == "A movie with this name, year, and duration already exists.", "Unexpected conflict error message."


@pytest.mark.asyncio
async def test_create_movie_commit_error(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    certification = await create_certification_directly(db_session, name="PG-13")
    genre = await create_genre_directly(db_session=db_session, name="Sci-Fi")
    star = await create_star_directly(db_session=db_session, name="Tom Hardy")
    director = await create_director_directly(db_session=db_session, name="Christopher Nolan")
    movie_payload = {
        "name": "Inception",
        "year": 2010,
        "time": 148,
        "imdb": 8.8,
        "votes": 100,
        "description": "...",
        "price": "9.99",
        "certification_id": certification.id,
        "genre_ids_or_names": [genre.id],
        "star_ids_or_names": [star.id],
        "director_ids_or_names": [director.id]
    }
    with patch("routes.movies.AsyncSession.commit", side_effect=SQLAlchemyError):
        response = await client.post(f"/api/v1/movies", json=movie_payload, headers={"Authorization": f"Bearer {access_token}"})
        assert response.status_code == 500, f"Expected 500, got {response.status_code}"
        assert response.json()["detail"] == "An error occurred while creating the movie.", "Unexpected error message for a commit failure."


@pytest.mark.asyncio
async def test_list_movies_success(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    certification = await create_certification_directly(db_session, name="PG-13")
    movies_data = [
        {"name": "Inception", "year": 2010, "time": 148, "imdb": 8.8, "votes": 2400000,
         "description": "A thief who steals corporate secrets through dream-sharing technology.",
         "price": 9.99, "certification": certification},
        {"name": "The Dark Knight", "year": 2008, "time": 152, "imdb": 9.0, "votes": 2700000,
         "description": "Batman faces the Joker, a criminal mastermind who plunges Gotham into anarchy.",
         "price": 12.99, "certification": certification},
        {"name": "Interstellar", "year": 2014, "time": 169, "imdb": 8.6, "votes": 2000000,
         "description": "A team of explorers travel through a wormhole in space in an attempt to save humanity.",
         "price": 11.49, "certification": certification},
    ]
    for movie_data in movies_data:
        await create_movie_full(db_session=db_session, **movie_data)

    response = await client.get(f"/api/v1/movies", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["total"] == 3, "Unexpected total count."
    assert len(response.json()["items"]) == 3, "Unexpected number of items on the page."


@pytest.mark.asyncio
async def test_list_movies_empty(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)

    response = await client.get(f"/api/v1/movies", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["total"] == 0 and response.json()["items"] == [], "Expected an empty paginated envelope, not a 404."


@pytest.mark.asyncio
async def test_list_movies_pagination(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    certification = await create_certification_directly(db_session, name="PG-13")
    movies_data = [
        {"name": "Inception", "year": 2010, "time": 148, "imdb": 8.8, "votes": 2400000,
         "description": "A thief who steals corporate secrets through dream-sharing technology.",
         "price": 9.99, "certification": certification},
        {"name": "The Dark Knight", "year": 2008, "time": 152, "imdb": 9.0, "votes": 2700000,
         "description": "Batman faces the Joker, a criminal mastermind who plunges Gotham into anarchy.",
         "price": 12.99, "certification": certification},
        {"name": "Interstellar", "year": 2014, "time": 169, "imdb": 8.6, "votes": 2000000,
         "description": "A team of explorers travel through a wormhole in space in an attempt to save humanity.",
         "price": 11.49, "certification": certification},
    ]
    for movie_data in movies_data:
        await create_movie_full(db_session=db_session, **movie_data)

    response = await client.get(f"/api/v1/movies?page=2&per_page=2", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert len(response.json()["items"]) == 1, "Unexpected number of items on the second page."
    assert response.json()["total_pages"] == 2, "Unexpected total page count."


@pytest.mark.asyncio
async def test_list_movies_search(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    certification = await create_certification_directly(db_session, name="PG-13")
    movies_data = [
        {"name": "Inception", "year": 2010, "time": 148, "imdb": 8.8, "votes": 2400000,
         "description": "A thief who steals corporate secrets through dream-sharing technology.",
         "price": 9.99, "certification": certification},
        {"name": "The Dark Knight", "year": 2008, "time": 152, "imdb": 9.0, "votes": 2700000,
         "description": "Batman faces the Joker, a criminal mastermind who plunges Gotham into anarchy.",
         "price": 12.99, "certification": certification},
        {"name": "Interstellar", "year": 2014, "time": 169, "imdb": 8.6, "votes": 2000000,
         "description": "A team of explorers travel through a wormhole in space in an attempt to save humanity.",
         "price": 11.49, "certification": certification},
    ]
    for movie_data in movies_data:
        await create_movie_full(db_session=db_session, **movie_data)

    response = await client.get(f"/api/v1/movies?search=incep", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert len(response.json()["items"]) == 1, "Search should match only the Inception movie."
    assert response.json()["total"] == 3, "Unexpected total movie count."


@pytest.mark.asyncio
async def test_list_movies_genre_filter(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    certification = await create_certification_directly(db_session, name="PG-13")
    genre_1 = await create_genre_directly(db_session=db_session, name="Sci-Fi")
    genre_2 = await create_genre_directly(db_session=db_session, name="Action")
    movies = []
    movies_data = [
        {"name": "Inception", "year": 2010, "time": 148, "imdb": 8.8, "votes": 2400000,
         "description": "A thief who steals corporate secrets through dream-sharing technology.",
         "price": 9.99, "certification": certification, "genres": [genre_1]},
        {"name": "The Dark Knight", "year": 2008, "time": 152, "imdb": 9.0, "votes": 2700000,
         "description": "Batman faces the Joker, a criminal mastermind who plunges Gotham into anarchy.",
         "price": 12.99, "certification": certification, "genres": [genre_2]},
    ]
    for movie_data in movies_data:
        movies.append(await create_movie_full(db_session=db_session, **movie_data))

    response = await client.get(f"/api/v1/movies?genre_id={genre_1.id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert len(response.json()["items"]) == 1, "genre_id filter should return only Inception movie."
    assert response.json()["items"][0]["name"] == movies[0].name, "genre_id filter returned the wrong movie."


@pytest.mark.asyncio
async def test_list_movies_year_filter(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    certification = await create_certification_directly(db_session, name="PG-13")
    movies = []
    movies_data = [
        {"name": "Inception", "year": 2010, "time": 148, "imdb": 8.8, "votes": 2400000,
         "description": "A thief who steals corporate secrets through dream-sharing technology.",
         "price": 9.99, "certification": certification},
        {"name": "The Dark Knight", "year": 2008, "time": 152, "imdb": 9.0, "votes": 2700000,
         "description": "Batman faces the Joker, a criminal mastermind who plunges Gotham into anarchy.",
         "price": 12.99, "certification": certification},
        {"name": "Interstellar", "year": 2014, "time": 169, "imdb": 8.6, "votes": 2000000,
         "description": "A team of explorers travel through a wormhole in space in an attempt to save humanity.",
         "price": 11.49, "certification": certification},
    ]
    for movie_data in movies_data:
        movies.append(await create_movie_full(db_session=db_session, **movie_data))

    response = await client.get("/api/v1/movies?year=2010", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert len(response.json()["items"]) == 1 and response.json()["items"][0]["name"] == movies[0].name, "year filter should return only the 2010 movie."


@pytest.mark.asyncio
async def test_list_movies_price_range(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    certification = await create_certification_directly(db_session, name="PG-13")
    movies = []
    movies_data = [
        {"name": "Inception", "year": 2010, "time": 148, "imdb": 8.8, "votes": 2400000,
         "description": "A thief who steals corporate secrets through dream-sharing technology.",
         "price": 5.99, "certification": certification},
        {"name": "The Dark Knight", "year": 2008, "time": 152, "imdb": 9.0, "votes": 2700000,
         "description": "Batman faces the Joker, a criminal mastermind who plunges Gotham into anarchy.",
         "price": 9.99, "certification": certification},
        {"name": "Interstellar", "year": 2014, "time": 169, "imdb": 8.6, "votes": 2000000,
         "description": "A team of explorers travel through a wormhole in space in an attempt to save humanity.",
         "price": 19.99, "certification": certification},
    ]
    for movie_data in movies_data:
        movies.append(await create_movie_full(db_session=db_session, **movie_data))

    response = await client.get("/api/v1/movies?price_min=8&price_max=15", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert len(response.json()["items"]) == 1 and response.json()["items"][0]["price"] == str(movies[1].price), "price_min/price_max range returned the wrong movies."


@pytest.mark.asyncio
async def test_list_movies_sort_by_price_desc(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    certification = await create_certification_directly(db_session, name="PG-13")
    movies_data = [
        {"name": "Inception", "year": 2010, "time": 148, "imdb": 8.8, "votes": 2400000,
         "description": "A thief who steals corporate secrets through dream-sharing technology.",
         "price": 5.99, "certification": certification},
        {"name": "The Dark Knight", "year": 2008, "time": 152, "imdb": 9.0, "votes": 2700000,
         "description": "Batman faces the Joker, a criminal mastermind who plunges Gotham into anarchy.",
         "price": 9.99, "certification": certification},
        {"name": "Interstellar", "year": 2014, "time": 169, "imdb": 8.6, "votes": 2000000,
         "description": "A team of explorers travel through a wormhole in space in an attempt to save humanity.",
         "price": 19.99, "certification": certification},
    ]
    for movie_data in movies_data:
        await create_movie_full(db_session=db_session, **movie_data)

    response = await client.get("/api/v1/movies?sort_by=price&order=desc", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert [item["price"] for item in response.json()["items"]] == ["19.99", "9.99", "5.99"], "price_min/price_max range returned the wrong movies."



@pytest.mark.asyncio
async def test_get_movie_success(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    movie = await create_movie_full(db_session=db_session)

    response = await client.get(f"/api/v1/movies/{movie.id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["name"] == movie.name, "Returned movie does not match the requested id."


@pytest.mark.asyncio
async def test_get_movie_not_found(client, db_session, jwt_manager, seed_user_groups):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    fake_movie_id = 9999

    response = await client.get(f"/api/v1/movies/{fake_movie_id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    assert response.json()["detail"] == f"Movie with id {fake_movie_id} not found.", "Unexpected error message for a missing movie."


@pytest.mark.asyncio
async def test_list_favorite_movies_success(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    movie = await create_movie_full(db_session=db_session)
    await db_session.execute(insert(FavoriteMovieModel).values(user_id=user.id, movie_id=movie.id))
    await db_session.commit()

    response = await client.get("/api/v1/movies/favorites", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert len(response.json()["items"]) == 1 and response.json()["items"][0]["name"] == movie.name, "Favorites list did not return the expected movie."


@pytest.mark.asyncio
async def test_list_favorite_movies_empty(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)

    response = await client.get("/api/v1/movies/favorites", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["items"] == [] and response.json()["total"] == 0, "Expected an empty paginated envelope for a user with no favorites."


@pytest.mark.asyncio
async def test_update_movie_success(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    movie = await create_movie_full(db_session=db_session)
    movie_update_payload = {"price": "14.99"}

    response = await client.patch(f"/api/v1/movies/{movie.id}", json=movie_update_payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["price"] == "14.99", "Price was not updated."


@pytest.mark.asyncio
async def test_update_movie_conflict(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    certification = await create_certification_directly(db_session, name="PG-13")
    movies = []
    movies_data = [
        {"name": "Inception", "year": 2010, "time": 148, "imdb": 8.8, "votes": 2400000,
         "description": "A thief who steals corporate secrets through dream-sharing technology.",
         "price": 5.99, "certification": certification},
        {"name": "The Dark Knight", "year": 2008, "time": 152, "imdb": 9.0, "votes": 2700000,
         "description": "Batman faces the Joker, a criminal mastermind who plunges Gotham into anarchy.",
         "price": 9.99, "certification": certification},
        {"name": "Interstellar", "year": 2014, "time": 169, "imdb": 8.6, "votes": 2000000,
         "description": "A team of explorers travel through a wormhole in space in an attempt to save humanity.",
         "price": 19.99, "certification": certification},
    ]
    for movie_data in movies_data:
        movies.append(await create_movie_full(db_session=db_session, **movie_data))
    movie_update_payload = {
        "name": "Inception",
        "year": 2010,
        "time": 148
    }

    response = await client.patch(f"/api/v1/movies/{movies[1].id}", json=movie_update_payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 409, f"Expected 409, got {response.status_code}"
    assert response.json()["detail"] == "A movie with this name, year, and duration already exists.", "Unexpected conflict error message."


@pytest.mark.asyncio
async def test_update_movie_certification_not_found(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    movie = await create_movie_full(db_session=db_session)
    movie_update_payload = {
        "certification_id": 9999
    }

    response = await client.patch(f"/api/v1/movies/{movie.id}", json=movie_update_payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    assert response.json()["detail"] == f"Certification with id {movie_update_payload["certification_id"]} not found.", "Unexpected error message for a missing certification."


@pytest.mark.asyncio
async def test_update_movie_not_found(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    movie_update_payload = {"price": "14.99"}
    fake_movie_id = 9999

    response = await client.patch(f"/api/v1/movies/{fake_movie_id}", json=movie_update_payload, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    assert response.json()["detail"] == f"Movie with id {fake_movie_id} not found.", "Unexpected error message for a missing movie."


@pytest.mark.asyncio
async def test_update_movie_commit_error(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    movie = await create_movie_full(db_session=db_session)
    movie_update_payload = {"price": "14.99"}

    with patch("routes.movies.AsyncSession.commit", side_effect=SQLAlchemyError):
        response = await client.patch(f"/api/v1/movies/{movie.id}", json=movie_update_payload, headers={"Authorization": f"Bearer {access_token}"})
        assert response.status_code == 500, f"Expected 500, got {response.status_code}"
        assert response.json()["detail"] == "An error occurred while updating the movie.", "Unexpected error message for a commit failure."


@pytest.mark.asyncio
async def test_delete_movie_success(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    movie = await create_movie_full(db_session=db_session)

    response = await client.delete(f"/api/v1/movies/{movie.id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["message"] == f"Movie {movie.name!r} was successfully deleted.", "Unexpected success message."

    stmt = select(MovieModel).where(MovieModel.id == movie.id).execution_options(populate_existing=True)
    result = await db_session.execute(stmt)
    deleted_movie = result.scalars().first()
    assert deleted_movie is None, "Movie should be deleted from the database."


@pytest.mark.asyncio
async def test_delete_movie_not_found(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    fake_movie_id = 9999

    response = await client.delete(f"/api/v1/movies/{fake_movie_id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    assert response.json()["detail"] == f"Movie with id {fake_movie_id} not found.", "Unexpected error message for a missing movie."


@pytest.mark.asyncio
async def test_delete_movie_already_purchased(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    movie = await create_movie_full(db_session=db_session)
    await create_order_directly(db_session, user, movie, status=StatusOrderEnum.PAID)

    response = await client.delete(f"/api/v1/movies/{movie.id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 409, f"Expected 409, got {response.status_code}"
    assert response.json()["detail"] == f"Cannot delete movie {movie.name!r} - it has already been purchased by one or more users.", "Unexpected conflict error message."


@pytest.mark.asyncio
async def test_delete_movie_commit_error(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN)
    movie = await create_movie_full(db_session=db_session)

    with patch("routes.movies.AsyncSession.commit", side_effect=SQLAlchemyError):
        response = await client.delete(f"/api/v1/movies/{movie.id}", headers={"Authorization": f"Bearer {access_token}"})
        assert response.status_code == 500, f"Expected 500, got {response.status_code}"
        assert response.json()["detail"] == "An error occurred while deleting the movie.", "Unexpected error message for a commit failure."


@pytest.mark.asyncio
async def test_add_to_favorites_success(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    movie = await create_movie_full(db_session=db_session)

    response = await client.post(f"/api/v1/movies/{movie.id}/favorites", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["message"] == f"Movie {movie.name!r} was successfully added to favorites for {user.email}", "Unexpected success message."

    stmt = select(MovieModel).where(MovieModel.id == movie.id).options(joinedload(MovieModel.favorited_by)).execution_options(populate_existing=True)
    result = await db_session.execute(stmt)
    movie = result.scalars().first()
    assert movie.favorited_by is not None, "Movie should be added to user's favourite."


@pytest.mark.asyncio
async def test_add_to_favorites_movie_not_found(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    fake_movie_id = 9999

    response = await client.post(f"/api/v1/movies/{fake_movie_id}/favorites", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    assert response.json()["detail"] == f"Movie with id {fake_movie_id} not found.", "Unexpected error message for a missing movie."


@pytest.mark.asyncio
async def test_add_to_favorites_already_favorited(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    movie = await create_movie_full(db_session=db_session)

    response = await client.post(f"/api/v1/movies/{movie.id}/favorites", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["message"] == f"Movie {movie.name!r} was successfully added to favorites for {user.email}", "Unexpected success message."

    response = await client.post(f"/api/v1/movies/{movie.id}/favorites", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 409, f"Expected 409, got {response.status_code}"
    assert response.json()["detail"] == "This movie is already in your favorites.", "Unexpected conflict error message."


@pytest.mark.asyncio
async def test_remove_from_favorites_success(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    movie = await create_movie_full(db_session=db_session, favorited_by=[user])

    response = await client.delete(f"/api/v1/movies/{movie.id}/favorites", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["message"] == f"Movie {movie.name!r} was removed from favorites for {user.email}", "Unexpected success message."


@pytest.mark.asyncio
async def test_remove_from_favorites_movie_not_found(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    fake_movie_id = 9999

    response = await client.delete(f"/api/v1/movies/{fake_movie_id}/favorites", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    assert response.json()["detail"] == f"Movie with id {fake_movie_id} not found.", "Unexpected error message for a missing movie."


@pytest.mark.asyncio
async def test_remove_from_favorites_not_favorited(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    movie = await create_movie_full(db_session=db_session)

    response = await client.delete(f"/api/v1/movies/{movie.id}/favorites", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    assert response.json()["detail"] == "This movie is not in your favorites.", "Unexpected error message for removing a non-favorited movie."


@pytest.mark.asyncio
async def test_add_to_favorites_commit_error(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    movie = await create_movie_full(db_session=db_session, favorited_by=[user])

    with patch("routes.movies.AsyncSession.commit", side_effect=SQLAlchemyError):
        response = await client.delete(f"/api/v1/movies/{movie.id}/favorites", headers={"Authorization": f"Bearer {access_token}"})
        assert response.status_code == 500, f"Expected 500, got {response.status_code}"
        assert response.json()["detail"] == "An error occurred while deleting the movie from favorites.", "Unexpected error message for a commit failure."


@pytest.mark.asyncio
async def test_remove_from_favorites_commit_error(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    movie = await create_movie_full(db_session=db_session)
    with patch("routes.movies.AsyncSession.commit", side_effect=SQLAlchemyError):
        response = await client.post(f"/api/v1/movies/{movie.id}/favorites", headers={"Authorization": f"Bearer {access_token}"})
        assert response.status_code == 500, f"Expected 200, got {response.status_code}"
        assert response.json()["detail"] == "An error occurred while adding the movie to favorites.", "Unexpected error message for a commit failure."
