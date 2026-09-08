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


@pytest.mark.asyncio
async def test_view_user_cart_success(client, db_session, jwt_manager, seed_user_groups):
    target_user, _ = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    movie = await create_movie(db_session=db_session)

    await add_item_to_cart_directly(db_session=db_session, user=target_user, movie=movie)

    admin, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN, email="admin@example.com")
    response = await client.get(f"/api/v1/carts/users/{target_user.id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["user_email"] == target_user.email, "Returned cart is not for the requested user."


@pytest.mark.asyncio
async def test_view_user_cart_forbidden(client, db_session, jwt_manager, seed_user_groups):
    target_user, _ = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    movie = await create_movie(db_session=db_session)

    await add_item_to_cart_directly(db_session=db_session, user=target_user, movie=movie)

    fake_admin, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER, email="fake_admin@example.com")
    response = await client.get(f"/api/v1/carts/users/{target_user.id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    assert response.json()["detail"] == "You do not have permission to perform this action.", "Unexpected error message for a non-privileged caller."


@pytest.mark.asyncio
async def test_view_user_cart_user_not_found(client, db_session, jwt_manager, seed_user_groups):
    fake_user_id = 9999
    admin, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN, email="admin@example.com")
    response = await client.get(f"/api/v1/carts/users/{fake_user_id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    assert response.json()["detail"] == f"User with id {fake_user_id} not found.", "Unexpected error message for a missing user."


@pytest.mark.asyncio
async def test_view_user_cart_empty(client, db_session, jwt_manager, seed_user_groups):
    target_user, _ = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)

    admin, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN, email="admin@example.com")
    response = await client.get(f"/api/v1/carts/users/{target_user.id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["message"] == f"User {target_user.email!r} has no movies in the cart.", "Unexpected message for an empty target cart."


@pytest.mark.asyncio
async def test_list_orders_success(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    movie_1 = await create_movie(db_session=db_session)
    movie_2 = await create_movie(db_session=db_session, name="Dune", certification_name="M")

    await create_order_directly(db_session=db_session, user=user, movie=movie_1)
    await create_order_directly(db_session=db_session, user=user, movie=movie_2)

    response = await client.get(f"/api/v1/orders", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert len(response.json()) == 2, "Unexpected number of orders returned."
    assert response.json()[0]["items_count"] == 1, "Unexpected item count for an order."


@pytest.mark.asyncio
async def test_list_orders_empty(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)

    response = await client.get(f"/api/v1/orders", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json() == [], "Expected an empty list when the user has no orders."


@pytest.mark.asyncio
async def test_create_order_success(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    movie = await create_movie(db_session=db_session)

    await add_item_to_cart_directly(db_session=db_session, user=user, movie=movie)

    response = await client.post(f"/api/v1/orders", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"
    assert float(response.json()["order_sum"]) == float(movie.price), "Order sum does not match the movie price."
    remaining_cart_items = (await db_session.execute(select(CartItem).join(CartModel).where(CartModel.user_id == user.id))).scalars().all()
    assert remaining_cart_items == [], "Cart should be emptied after the order is created."


@pytest.mark.asyncio
async def test_create_order_empty_cart(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)

    response = await client.post(f"/api/v1/orders", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    assert response.json()["detail"] == "Your cart is empty.", "Unexpected error message for an empty cart."


@pytest.mark.asyncio
async def test_create_order_already_purchased(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    movie = await create_movie(db_session=db_session)

    await create_order_directly(db_session=db_session, user=user, movie=movie, status=StatusOrderEnum.PAID)
    await add_item_to_cart_directly(db_session=db_session, user=user, movie=movie)

    response = await client.post(f"/api/v1/orders", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 409, f"Expected 409, got {response.status_code}"
    assert response.json()["detail"] == f"Movie {movie.name!r} has already been purchased.", "Unexpected conflict error message."
    orders_count = (await db_session.execute(select(func.count(OrderModel.id)).where(OrderModel.user_id == user.id))).scalar()
    assert orders_count == 1, "The failed new order should not have been persisted (only the pre-existing paid one)."


@pytest.mark.asyncio
async def test_create_order_commit_error(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    movie = await create_movie(db_session=db_session)

    await add_item_to_cart_directly(db_session=db_session, user=user, movie=movie)

    with patch("routes.orders.AsyncSession.commit", side_effect=SQLAlchemyError):
        response = await client.post(f"/api/v1/orders", headers={"Authorization": f"Bearer {access_token}"})
        assert response.status_code == 500, f"Expected 500, got {response.status_code}"
        assert response.json()["detail"] == "An error occurred while creating the order.", "Unexpected error message for a commit failure."


@pytest.mark.asyncio
async def test_view_order_success(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    movie = await create_movie(db_session=db_session)

    order = await create_order_directly(db_session=db_session, user=user, movie=movie)

    response = await client.get(f"/api/v1/orders/{order.id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["id"] == order.id, "Returned order id does not match."
    assert len(response.json()["items"]) == 1, "Unexpected number of order items."


@pytest.mark.asyncio
async def test_view_order_not_found(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    fake_order_id = 9999

    response = await client.get(f"/api/v1/orders/{fake_order_id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    assert response.json()["detail"] == f"Order with id {fake_order_id} not found.", "Unexpected error message for a missing order."


@pytest.mark.asyncio
async def test_view_order_forbidden(client, db_session, jwt_manager, seed_user_groups):
    user_order_owner, _ = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    movie = await create_movie(db_session=db_session)

    order = await create_order_directly(db_session=db_session, user=user_order_owner, movie=movie)

    user_viewer, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER, email="user_viewer@example.com")

    response = await client.get(f"/api/v1/orders/{order.id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    assert response.json()["detail"] == "You can view only your own orders!", "Unexpected error message for viewing another user's order."


@pytest.mark.asyncio
async def test_cancel_order_success(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    movie = await create_movie(db_session=db_session)

    order = await create_order_directly(db_session=db_session, user=user, movie=movie, status=StatusOrderEnum.PENDING)

    response = await client.post(f"/api/v1/orders/{order.id}/cancel", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["message"] == f"Order #{order.id} was successfully canceled.", "Unexpected success message."
    await db_session.refresh(order)
    assert order.status == StatusOrderEnum.CANCELED, "Order status was not updated in the database."


@pytest.mark.asyncio
async def test_cancel_order_not_found(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    fake_order_id = 9999

    response = await client.post(f"/api/v1/orders/{fake_order_id}/cancel", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    assert response.json()["detail"] == f"Order with id {fake_order_id} not found.", "Unexpected error message for a missing order."


@pytest.mark.asyncio
async def test_cancel_order_forbidden(client, db_session, jwt_manager, seed_user_groups):
    user_order_owner, _ = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    movie = await create_movie(db_session=db_session)
    order = await create_order_directly(db_session=db_session, user=user_order_owner, movie=movie, status=StatusOrderEnum.PENDING)

    user_canceler, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER, email="user_canceler@example.com")

    response = await client.post(f"/api/v1/orders/{order.id}/cancel", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    assert response.json()["detail"] == "You can cancel only your own orders!", "Unexpected error message for canceling another user's order."


@pytest.mark.asyncio
async def test_cancel_order_not_pending(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    movie = await create_movie(db_session=db_session)

    order = await create_order_directly(db_session=db_session, user=user, movie=movie, status=StatusOrderEnum.PAID)

    response = await client.post(f"/api/v1/orders/{order.id}/cancel", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 409, f"Expected 409, got {response.status_code}"
    assert response.json()["detail"] == "Only pending orders can be canceled.", "Unexpected error message for a non-pending order."


@pytest.mark.asyncio
async def test_cancel_order_commit_error(client, db_session, jwt_manager, seed_user_groups):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    movie = await create_movie(db_session=db_session)

    order = await create_order_directly(db_session=db_session, user=user, movie=movie, status=StatusOrderEnum.PENDING)
    with patch("routes.orders.AsyncSession.commit", side_effect=SQLAlchemyError):
        response = await client.post(f"/api/v1/orders/{order.id}/cancel", headers={"Authorization": f"Bearer {access_token}"})
        assert response.status_code == 500, f"Expected 500, got {response.status_code}"
        assert response.json()["detail"] == "An error occurred while canceling the order.", "Unexpected error message for a commit failure."



@pytest.mark.asyncio
async def test_view_user_orders_success(client, db_session, jwt_manager, seed_user_groups):
    target_user, _ = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    movie = await create_movie(db_session=db_session)

    order = await create_order_directly(db_session=db_session, user=target_user, movie=movie, status=StatusOrderEnum.PENDING)

    admin, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN, email="admin@example.com")
    response = await client.get(f"/api/v1/orders/users/{target_user.id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["user_email"] == target_user.email, "Returned orders are not for the requested user."
    assert len(response.json()["orders"]) == 1, "Unexpected number of orders returned."


@pytest.mark.asyncio
async def test_view_user_orders_forbidden(client, db_session, jwt_manager, seed_user_groups):
    target_user, _ = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    movie = await create_movie(db_session=db_session)

    await create_order_directly(db_session=db_session, user=target_user, movie=movie, status=StatusOrderEnum.PENDING)

    fake_admin, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER, email="fake_admin@example.com")
    response = await client.get(f"/api/v1/orders/users/{target_user.id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    assert response.json()["detail"] == "You do not have permission to perform this action.", "Unexpected error message for a non-privileged caller."


@pytest.mark.asyncio
async def test_view_user_orders_user_not_found(client, db_session, jwt_manager, seed_user_groups):
    fake_user_id = 9999

    admin, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.ADMIN, email="admin@example.com")
    response = await client.get(f"/api/v1/orders/users/{fake_user_id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    assert response.json()["detail"] == f"User with id {fake_user_id} not found.", "Unexpected error message for a missing user."
