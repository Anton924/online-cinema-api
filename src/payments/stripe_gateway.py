import asyncio
from typing import Any

import stripe
from payments.interfaces import PaymentGatewayInterface


class StripeGateway(PaymentGatewayInterface):
    def __init__(self, api_key: str, webhook_secret: str) -> None:
        stripe.api_key = api_key
        self.webhook_secret = webhook_secret

    async def create_checkout_session(
            self,
            line_items: list[dict],
            metadata: dict[str, str],
            mode: str,
            success_url: str,
            cancel_url: str,
            client_reference_id: str
    ) -> Any:
        session = await asyncio.to_thread(
            stripe.checkout.Session.create,
            line_items=line_items,
            metadata=metadata,
            mode=mode,
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=client_reference_id
        )
        return session

    async def verify_webhook_event(self, payload: bytes, sig_header: str) -> Any:
        return stripe.Webhook.construct_event(payload, sig_header, self.webhook_secret)

    async def create_refund(self, payload: dict) -> Any:
        refund_params = {"payment_intent": payload["payment_intent_id"]}
        if payload.get("amount") is not None:
            refund_params["amount"] = payload["amount"]

        return await asyncio.to_thread(
            stripe.Refund.create,
            **refund_params
        )
