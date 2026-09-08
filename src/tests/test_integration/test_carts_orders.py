from unittest.mock import patch

import pytest
from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError

from tests.conftest import (
    create_active_user_with_token,
    create_movie,
    add_item_to_cart_directly,
    create_order_directly
)
from database.models.accounts import UserGroupEnum
from database.models.carts import CartModel, CartItem
from database.models.orders import StatusOrderEnum
from database.models.orders import OrderModel


@pytest.mark.asyncio
async def test_add_to_cart_success_creates_cart(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    movie = await create_movie(db_session=db_session)

    response = await client.post(f"/api/v1/carts/{movie.id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["message"] == f"Movie {movie.name!r} was successfully added to your cart.", "Unexpected success message."
    cart_item = (await db_session.execute(select(CartItem).join(CartModel).where(CartModel.user_id == user.id))).scalars().first()
    assert cart_item is not None and cart_item.movie_id == movie.id, "Cart item was not created in the database."


@pytest.mark.asyncio
async def test_add_to_cart_reuses_existing_cart(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    movie_1 = await create_movie(db_session=db_session)
    movie_2 = await create_movie(db_session=db_session, name="Dune", certification_name="M")

    await add_item_to_cart_directly(db_session=db_session, user=user, movie=movie_1)
    response = await client.post(f"/api/v1/carts/{movie_2.id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    count_carts = (await db_session.execute(select(func.count(CartModel.id)).where(CartModel.user_id == user.id))).scalars().first()
    assert count_carts == 1, "A second cart row should not have been created for the same user."


@pytest.mark.asyncio
async def test_add_to_cart_movie_not_found(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    fake_movie_id = 9999

    response = await client.post(f"/api/v1/carts/{fake_movie_id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    assert response.json()["detail"] == f"Movie with id {fake_movie_id} not found.", "Unexpected error message for a missing movie."


@pytest.mark.asyncio
async def test_add_to_cart_already_in_cart(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    movie = await create_movie(db_session=db_session)

    await add_item_to_cart_directly(db_session=db_session, user=user, movie=movie)
    response = await client.post(f"/api/v1/carts/{movie.id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 409, f"Expected 409, got {response.status_code}"
    assert response.json()["detail"] == "This movie is already in your cart.", "Unexpected conflict error message."


@pytest.mark.asyncio
async def test_add_to_cart_already_purchased(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    movie = await create_movie(db_session=db_session)
    await create_order_directly(db_session, user, movie, status=StatusOrderEnum.PAID)

    response = await client.post(f"/api/v1/carts/{movie.id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 409, f"Expected 409, got {response.status_code}"
    assert response.json()["detail"] == f"The movie {movie.name!r} has been already purchased!", "Unexpected conflict error message."


@pytest.mark.asyncio
async def test_add_to_cart_commit_error(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    movie = await create_movie(db_session=db_session)

    with patch("routes.carts.AsyncSession.commit", side_effect=SQLAlchemyError):
        response = await client.post(f"/api/v1/carts/{movie.id}", headers={"Authorization": f"Bearer {access_token}"})
        assert response.status_code == 500, f"Expected 500, got {response.status_code}"
        assert response.json()["detail"] == "An error occurred while adding the movie to cart.", "Unexpected error message for a commit failure."


@pytest.mark.asyncio
async def test_remove_from_cart_success(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    movie = await create_movie(db_session=db_session)
    await add_item_to_cart_directly(db_session=db_session, user=user, movie=movie)

    response = await client.delete(f"/api/v1/carts/{movie.id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["message"] == f"Movie {movie.name!r} was removed from the cart.", "Unexpected success message."
    cart_item = (await db_session.execute(select(CartItem).join(CartModel).where(CartModel.user_id == user.id))).scalars().first()
    assert cart_item is None, "Cart item should be deleted from the database."


@pytest.mark.asyncio
async def test_remove_from_cart_movie_not_found(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    fake_movie_id = 9999

    response = await client.delete(f"/api/v1/carts/{fake_movie_id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    assert response.json()["detail"] == f"Movie with id {fake_movie_id} not found.", "Unexpected error message for a missing movie."


@pytest.mark.asyncio
async def test_remove_from_cart_no_cart(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    movie = await create_movie(db_session=db_session)

    response = await client.delete(f"/api/v1/carts/{movie.id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["message"] == "You have no movies in your cart!", "Unexpected message when no cart exists."


@pytest.mark.asyncio
async def test_remove_from_cart_not_in_cart(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    movie_1 = await create_movie(db_session=db_session)
    movie_2 = await create_movie(db_session=db_session, name="Dune", certification_name="M")

    await add_item_to_cart_directly(db_session=db_session, user=user, movie=movie_1)

    response = await client.delete(f"/api/v1/carts/{movie_2.id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    assert response.json()["detail"] == f"The movie {movie_2.name!r} is not in your cart.", "Unexpected error message for a movie not in the cart."


@pytest.mark.asyncio
async def test_remove_from_cart_commit_error(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    movie = await create_movie(db_session=db_session)
    await add_item_to_cart_directly(db_session=db_session, user=user, movie=movie)

    with patch("routes.carts.AsyncSession.commit", side_effect=SQLAlchemyError):
        response = await client.delete(f"/api/v1/carts/{movie.id}", headers={"Authorization": f"Bearer {access_token}"})
        assert response.status_code == 500, f"Expected 500, got {response.status_code}"
        assert response.json()["detail"] == "An error occurred while removing the movie from cart.", "Unexpected error message for a commit failure."


@pytest.mark.asyncio
async def test_view_cart_success(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    movie_1 = await create_movie(db_session=db_session)
    movie_2 = await create_movie(db_session=db_session, name="Dune", certification_name="M")

    await add_item_to_cart_directly(db_session=db_session, user=user, movie=movie_1)
    await add_item_to_cart_directly(db_session=db_session, user=user, movie=movie_2)
    response = await client.get(f"/api/v1/carts", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["total_items"] == 2, "Unexpected item count in the cart."
    assert float(response.json()["total_price"]) == float(movie_1.price + movie_2.price), "Unexpected total price."


@pytest.mark.asyncio
async def test_view_cart_no_cart(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)

    response = await client.get(f"/api/v1/carts", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["message"] == "You have no movies in your cart!", "Unexpected message when no cart exists."


@pytest.mark.asyncio
async def test_view_cart_empty_cart_row(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)

    cart = CartModel(user_id=user.id)
    db_session.add(cart)
    await db_session.flush()

    response = await client.get(f"/api/v1/carts", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["message"] == "You have no movies in your cart!", "Unexpected message when no cart exists."


@pytest.mark.asyncio
async def test_clear_cart_success(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    movie_1 = await create_movie(db_session=db_session)
    movie_2 = await create_movie(db_session=db_session, name="Dune", certification_name="M")

    await add_item_to_cart_directly(db_session=db_session, user=user, movie=movie_1)
    await add_item_to_cart_directly(db_session=db_session, user=user, movie=movie_2)
    response = await client.delete(f"/api/v1/carts", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["message"] == "Your cart was successfully cleared.", "Unexpected success message."
    remaining_items = (await db_session.execute(select(CartItem).join(CartModel).where(CartModel.user_id == user.id))).scalars().all()
    assert remaining_items == [], "Cart items were not deleted from the database."


@pytest.mark.asyncio
async def test_clear_cart_no_cart(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)

    response = await client.delete(f"/api/v1/carts", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["message"] == "Your cart was successfully cleared.", "Clearing a nonexistent cart should still report success."


@pytest.mark.asyncio
async def test_clear_cart_commit_error(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    movie_1 = await create_movie(db_session=db_session)
    movie_2 = await create_movie(db_session=db_session, name="Dune", certification_name="M")

    await add_item_to_cart_directly(db_session=db_session, user=user, movie=movie_1)
    await add_item_to_cart_directly(db_session=db_session, user=user, movie=movie_2)
    with patch("routes.carts.AsyncSession.commit", side_effect=SQLAlchemyError):
        response = await client.delete(f"/api/v1/carts", headers={"Authorization": f"Bearer {access_token}"})
        assert response.status_code == 500, f"Expected 500, got {response.status_code}"
        assert response.json()["detail"] == "An error occurred while clearing the cart.", "Unexpected error message for a commit failure."

