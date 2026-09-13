import pytest

from tests.conftest import (
    make_image_bytes,
    create_movie_full,
    create_certification_directly
)
from database.models.accounts import UserModel
from database.models.orders import StatusOrderEnum


@pytest.mark.asyncdio
@pytest.mark.e2e
@pytest.mark.order(7)
async def test_07_add_to_cart(e2e_client, e2e_db_session, e2e_state):
    access_token = e2e_state["access_token"]
    movie = await create_movie_full(
        e2e_db_session,
        name="E2E Test Movie",
        year=2024,
        time=120,
        imdb=7.5,
        votes=500,
        description="A movie created specifically for the e2e purchase journey.",
        price=9.99
    )
    response = await e2e_client.post(f"/api/v1/carts/{movie.id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["message"] == f"Movie {movie.name!r} was successfully added to your cart.", "Unexpected success message."


@pytest.mark.asyncdio
@pytest.mark.e2e
@pytest.mark.order(8)
async def test_10_view_cart(e2e_client, e2e_state):
    access_token = e2e_state["access_token"]
    response = await e2e_client.get("/api/v1/carts", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert len(response.json()["items"]) == 1, "Cart should contain exactly the one movie added in step 9."
    assert response.json()["total_items"] == 1, "Unexpected total_items count."


@pytest.mark.asyncdio
@pytest.mark.e2e
@pytest.mark.order(9)
async def test_18_create_order(e2e_client, e2e_state):
    access_token = e2e_state["access_token"]
    response = await e2e_client.post("/api/v1/orders", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"
    assert response.json()["status"] == StatusOrderEnum.PENDING, "A freshly created order should be pending, not paid."
    assert response.json()["items"][0]["movie"]["name"] == "E2E Test Movie", "Order does not contain the movie added to the cart."
    e2e_state["order_id"] = response.json()["id"]


@pytest.mark.asyncdio
@pytest.mark.e2e
@pytest.mark.order(10)
async def test_12_view_order(e2e_client, e2e_state):
    access_token = e2e_state["access_token"]
    response = await e2e_client.get(f"/api/v1/orders/{e2e_state['order_id']}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["id"] == e2e_state["order_id"], "Order created in step 11 is not retrievable in a separate request."
