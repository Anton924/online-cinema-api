from decimal import Decimal

import pytest
from unittest.mock import patch, AsyncMock
from sqlalchemy import select, insert

from sqlalchemy.exc import SQLAlchemyError
from stripe import StripeError, SignatureVerificationError

from tests.conftest import (
    create_movie,
    create_order_directly,
    create_active_user_with_token,
    build_checkout_completed_event,
    create_payment_directly
)
from database.models.orders import StatusOrderEnum, OrderModel, OrderItemModel
from database.models.payments import PaymentModel, PaymentStatus, PaymentItemModel
from database.models.accounts import UserModel, UserGroup, UserGroupEnum


@pytest.mark.asyncio
async def test_create_payment_session_success(client, db_session, seed_user_groups, payment_gateway_fake, jwt_manager):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    movie = await create_movie(db_session=db_session)
    order = await create_order_directly(db_session, user, movie, status=StatusOrderEnum.PENDING)

    response = await client.post(f"/api/v1/payments/{order.id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["checkout_url"] == payment_gateway_fake.create_checkout_session.return_value.url, "Unexpected checkout URL returned."
    payment_gateway_fake.create_checkout_session.assert_awaited_once(), "Expected the gateway to be called exactly once."


@pytest.mark.asyncio
async def test_create_payment_session_order_not_found(client, db_session, seed_user_groups, payment_gateway_fake, jwt_manager):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    fake_order_id = 9999

    response = await client.post(f"/api/v1/payments/{fake_order_id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    assert response.json()["detail"] == f"Order with id {fake_order_id} not found.", "Unexpected error message for a missing order."


@pytest.mark.asyncio
async def test_create_payment_session_forbidden(client, db_session, seed_user_groups, payment_gateway_fake, jwt_manager):
    user_with_order, _ = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    movie = await create_movie(db_session=db_session)
    order = await create_order_directly(db_session, user_with_order, movie, status=StatusOrderEnum.PENDING)

    payer, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER, email="payer@example.com")

    response = await client.post(f"/api/v1/payments/{order.id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    assert response.json()["detail"] == "You can pay only for your own orders!", "Unexpected error message."


@pytest.mark.asyncio
async def test_create_payment_session_not_pending(client, db_session, seed_user_groups, payment_gateway_fake, jwt_manager):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    movie = await create_movie(db_session=db_session)
    order = await create_order_directly(db_session, user, movie, status=StatusOrderEnum.CANCELED)

    response = await client.post(f"/api/v1/payments/{order.id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 409, f"Expected 409, got {response.status_code}"
    assert response.json()["detail"] == "Only pending orders can be paid.", "Unexpected conflict error message."


@pytest.mark.asyncio
async def test_create_payment_session_already_has_payment(client, db_session, seed_user_groups, payment_gateway_fake, jwt_manager):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    movie = await create_movie(db_session=db_session)
    order = await create_order_directly(db_session, user, movie, status=StatusOrderEnum.PENDING)
    await db_session.execute(
        insert(PaymentModel).values(
            order_id=order.id,
            user_id=user.id,
            status=PaymentStatus.SUCCESSFUL,
            external_payment_id="cs_test_a1b2c3d4e5f6g7h8i9j0",
            payment_intent_id="pi_3Oa1b2c3D4e5F6g7H8i9J0k1",
        )
    )
    await db_session.commit()

    response = await client.post(f"/api/v1/payments/{order.id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 409, f"Expected 409, got {response.status_code}"
    assert response.json()["detail"] == "A payment for this order already exists.", "A payment for this order already exists."


@pytest.mark.asyncio
async def test_create_payment_session_stripe_error(client, db_session, seed_user_groups, payment_gateway_fake, jwt_manager):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, UserGroupEnum.USER)
    movie = await create_movie(db_session=db_session)
    order = await create_order_directly(db_session, user, movie, status=StatusOrderEnum.PENDING)

    with patch.object(payment_gateway_fake, "create_checkout_session", side_effect=StripeError()):
        response = await client.post(f"/api/v1/payments/{order.id}", headers={"Authorization": f"Bearer {access_token}"})
        assert response.status_code == 500, f"Expected 500, got {response.status_code}"
        assert response.json()["detail"] == "An error occurred while creating the payment session.", "Unexpected checkout URL returned."
