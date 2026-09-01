from abc import ABC, abstractmethod
from typing import Any


class PaymentGatewayInterface(ABC):
    @abstractmethod
    async def create_checkout_session(
            self,
            line_items: list[dict],
            metadata: dict[str, str],
            mode: str,
            success_url: str,
            cancel_url: str,
            client_reference_id: str
    ) -> Any:
        pass

    @abstractmethod
    async def verify_webhook_event(self, payload: bytes, sig_header: str) -> Any:
        pass

    @abstractmethod
    async def create_refund(self, payload: dict) -> Any:
        pass
