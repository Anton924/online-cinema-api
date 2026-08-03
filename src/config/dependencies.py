import os

from config.settings import BaseAppSettings, TestingSettings, Settings
from fastapi import Depends
from typing import Annotated

from security.token_manager import JWTAuthManager


def get_settings() -> BaseAppSettings:
    environment = os.getenv("ENVIRONMENT", "developing")
    if environment == "testing":
        return TestingSettings()
    return Settings()

def get_jwt_auth_manager(settings: Annotated[BaseAppSettings, Depends(get_settings)]):
    return JWTAuthManager(
        secret_key_access=settings.SECRET_KEY_ACCESS,
        secret_key_refresh=settings.SECRET_KEY_REFRESH,
        algorithm=settings.JWT_SIGNING_ALGORITHM
    )
