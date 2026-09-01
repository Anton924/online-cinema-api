import os

from config.settings import BaseAppSettings, TestingSettings, Settings
from fastapi import Depends
from typing import Annotated

from security.token_manager import JWTAuthManager
from notifications.emails import EmailSender
from notifications.interfaces import EmailSenderInterface
from security.interfaces import JWTAuthManagerInterface
from payments.interfaces import PaymentGatewayInterface
from payments.stripe_gateway import StripeGateway


def get_settings() -> BaseAppSettings:
    environment = os.getenv("ENVIRONMENT", "developing")
    if environment == "testing":
        return TestingSettings()
    return Settings()


def get_jwt_auth_manager(settings: Annotated[BaseAppSettings, Depends(get_settings)]) -> JWTAuthManagerInterface:
    return JWTAuthManager(
        secret_key_access=settings.SECRET_KEY_ACCESS,
        secret_key_refresh=settings.SECRET_KEY_REFRESH,
        algorithm=settings.JWT_SIGNING_ALGORITHM
    )


def get_email_sender(
        settings: Annotated[BaseAppSettings, Depends(get_settings)]
) -> EmailSenderInterface:
    return EmailSender(
        hostname=settings.EMAIL_HOST,
        port=settings.EMAIL_PORT,
        email=settings.EMAIL_HOST_USER,
        password=settings.EMAIL_HOST_PASSWORD,
        use_tls=settings.EMAIL_USE_TLS,
        template_dir=settings.PATH_TO_EMAIL_TEMPLATES_DIR,
        activation_email_template_name=settings.ACTIVATION_EMAIL_TEMPLATE_NAME,
        activation_complete_email_template_name=settings.ACTIVATION_COMPLETE_EMAIL_TEMPLATE_NAME,
        password_email_template_name=settings.PASSWORD_RESET_TEMPLATE_NAME,
        password_complete_email_template_name=settings.PASSWORD_RESET_COMPLETE_TEMPLATE_NAME,
        reply_to_comment_email_template_name=settings.REPLY_TO_COMMENT_TEMPLATE_NAME
    )


def get_payment_gateway(
    settings: Annotated[BaseAppSettings, Depends(get_settings)]
) -> PaymentGatewayInterface:
    return StripeGateway(
        api_key=settings.STRIPE_SECRET_KEY,
        webhook_secret=settings.STRIPE_WEBHOOK_SECRET
    )
