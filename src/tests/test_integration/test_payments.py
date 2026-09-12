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


@pytest.mark.asyncio
async def test_webhook_checkout_completed_success(settings, client, db_session, seed_user_groups, payment_gateway_fake, jwt_manager):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, group=UserGroupEnum.USER)
    movie = await create_movie(db_session=db_session)
    order = await create_order_directly(db_session, user, movie, status=StatusOrderEnum.PENDING)

    payment_gateway_fake.verify_webhook_event.return_value = build_checkout_completed_event(user_id=user.id, order_id=order.id)

    response = await client.post("/api/v1/payments/webhook")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["message"] == f"Payment for order #{order.id} was successfully processed", "Unexpected success message."
    record_payment = (await db_session.execute(select(PaymentModel).where(PaymentModel.order_id == order.id))).scalars().first()
    assert record_payment is not None and record_payment.status == PaymentStatus.SUCCESSFUL, "Payment row was not created with the expected status."
    order = (await db_session.execute(select(OrderModel).where(OrderModel.user_id == user.id).execution_options(populate_existing=True))).scalars().first()
    assert order.status == StatusOrderEnum.PAID, "Order was not marked as paid."


@pytest.mark.asyncio
async def test_webhook_invalid_signature(settings, client, db_session, seed_user_groups, payment_gateway_fake, jwt_manager):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, group=UserGroupEnum.USER)
    movie = await create_movie(db_session=db_session)
    order = await create_order_directly(db_session, user, movie, status=StatusOrderEnum.PENDING)

    with patch.object(payment_gateway_fake, "verify_webhook_event", side_effect=SignatureVerificationError(message="Error", sig_header="sig_header")):
        response = await client.post("/api/v1/payments/webhook")
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert response.json()["detail"] == "Invalid Stripe signature.", "Unexpected success message."


@pytest.mark.asyncio
async def test_webhook_event_already_processed(settings, client, db_session, seed_user_groups, payment_gateway_fake, jwt_manager):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, group=UserGroupEnum.USER)
    movie = await create_movie(db_session=db_session)
    order = await create_order_directly(db_session, user, movie, status=StatusOrderEnum.PENDING)

    payment_gateway_fake.verify_webhook_event.return_value = build_checkout_completed_event(user_id=user.id, order_id=order.id)

    await db_session.execute(
        insert(PaymentModel).values(
            order_id=order.id,
            user_id=user.id,
            status=PaymentStatus.SUCCESSFUL,
            external_payment_id="cs_test_123",
            payment_intent_id="pi_3Oa1b2c3D4e5F6g7H8i9J0k1",
        )
    )
    await db_session.commit()

    response = await client.post("/api/v1/payments/webhook")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["message"] == "Event already processed.", "Unexpected message for a duplicate webhook delivery."


@pytest.mark.asyncio
async def test_webhook_payment_still_processing(settings, client, db_session, seed_user_groups, payment_gateway_fake, jwt_manager):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, group=UserGroupEnum.USER)
    movie = await create_movie(db_session=db_session)
    order = await create_order_directly(db_session, user, movie, status=StatusOrderEnum.PENDING)

    payment_gateway_fake.verify_webhook_event.return_value = build_checkout_completed_event(user_id=user.id, order_id=order.id, payment_status="unpaid")

    await db_session.execute(
        insert(PaymentModel).values(
            order_id=order.id,
            user_id=user.id,
            status=PaymentStatus.SUCCESSFUL,
            external_payment_id="cs_test_123",
            payment_intent_id="pi_3Oa1b2c3D4e5F6g7H8i9J0k1",
        )
    )
    await db_session.commit()

    response = await client.post("/api/v1/payments/webhook")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["message"] == "Payment is still processing.", "Unexpected message."


@pytest.mark.asyncio
async def test_webhook_unrecognized_event_ignored(settings, client, db_session, seed_user_groups, payment_gateway_fake, jwt_manager):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, group=UserGroupEnum.USER)
    movie = await create_movie(db_session=db_session)
    order = await create_order_directly(db_session, user, movie, status=StatusOrderEnum.PENDING)

    payment_gateway_fake.verify_webhook_event.return_value = {"type": "payment_intent.created", "data": {"object": {}}}

    await db_session.execute(
        insert(PaymentModel).values(
            order_id=order.id,
            user_id=user.id,
            status=PaymentStatus.SUCCESSFUL,
            external_payment_id="cs_test_123",
            payment_intent_id="pi_3Oa1b2c3D4e5F6g7H8i9J0k1",
        )
    )
    await db_session.commit()

    response = await client.post("/api/v1/payments/webhook")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json()["message"] == "Event ignored.", "Unexpected message for an unhandled event type."


@pytest.mark.asyncio
async def test_webhook_commit_error(settings, client, db_session, seed_user_groups, payment_gateway_fake, jwt_manager):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, group=UserGroupEnum.USER)
    movie = await create_movie(db_session=db_session)
    order = await create_order_directly(db_session, user, movie, status=StatusOrderEnum.PENDING)

    payment_gateway_fake.verify_webhook_event.return_value = build_checkout_completed_event(user_id=user.id, order_id=order.id)

    with patch("routes.payments.AsyncSession.commit", side_effect=SQLAlchemyError):
        response = await client.post("/api/v1/payments/webhook")
        assert response.status_code == 500, f"Expected 500, got {response.status_code}"
        assert response.json()["detail"] == f"An error occurred while processing the payment", "Unexpected error message for a commit failure."


@pytest.mark.asyncio
async def test_payment_success_page(settings, client, db_session, seed_user_groups, payment_gateway_fake, jwt_manager):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, group=UserGroupEnum.USER)
    response = await client.get("/api/v1/payments/success?session_id=cs_test_123")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json() == {"status": "success", "session_id": "cs_test_123"}, "Unexpected response body."


@pytest.mark.asyncio
async def test_payment_cancel_page(settings, client, db_session, seed_user_groups, payment_gateway_fake, jwt_manager):
    _, access_token = await create_active_user_with_token(db_session, jwt_manager, group=UserGroupEnum.USER)
    response = await client.get("/api/v1/payments/cancel")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json() == {"status": "cancelled"}, "Unexpected response body."


@pytest.mark.asyncio
async def test_list_payments_success(settings, client, db_session, seed_user_groups, payment_gateway_fake, jwt_manager):
    user_1, access_token = await create_active_user_with_token(db_session, jwt_manager, group=UserGroupEnum.USER)
    user_2, _ = await create_active_user_with_token(db_session, jwt_manager, group=UserGroupEnum.USER, email="user_2@example.com")
    movie = await create_movie(db_session=db_session)
    order_user_1 = OrderModel(user_id=user_1.id, status=StatusOrderEnum.PAID, order_sum=movie.price)
    order_user_2 = OrderModel(user_id=user_2.id, status=StatusOrderEnum.PAID, order_sum=movie.price)
    db_session.add(order_user_1)
    db_session.add(order_user_2)
    await db_session.flush()
    order_item = OrderItemModel(order_id=order_user_1.id, movie_id=movie.id, price_at_order=movie.price)
    payment_user_1 = PaymentModel(
        order_id = order_user_1.id,
        user_id = user_1.id,
        status = PaymentStatus.SUCCESSFUL,
        external_payment_id = "cs_test_123",
        payment_intent_id = "pi_3Oa1b2c3D4e5F6g7H8i9J0k1",
    )
    payment_user_2 = PaymentModel(
        order_id = order_user_2.id,
        user_id = user_2.id,
        status = PaymentStatus.SUCCESSFUL,
        external_payment_id = "cs_test_321",
        payment_intent_id = "pi_3Oa1b2c3D4e5F6g7H8i9J0k2",
    )
    db_session.add(order_item)
    db_session.add(payment_user_1)
    db_session.add(payment_user_2)
    await db_session.flush()
    payment_item=PaymentItemModel(payment_id=payment_user_1.id, price_at_payment=movie.price, order_item_id=order_item.id)
    db_session.add(payment_item)
    await db_session.commit()


    response = await client.get("/api/v1/payments", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert len(response.json()) == 1, "Should return only the current user's payments."
    assert response.json()[0]["items_count"] == 1, "Unexpected items_count."


@pytest.mark.asyncio
async def test_list_payments_empty(settings, client, db_session, seed_user_groups, payment_gateway_fake, jwt_manager):
    user, access_token = await create_active_user_with_token(db_session, jwt_manager, group=UserGroupEnum.USER)

    response = await client.get("/api/v1/payments", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert response.json() == [], "Expected an empty list, not a 404."
