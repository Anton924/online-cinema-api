from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseAppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    BASE_DIR: Path = Path(__file__).parent.parent
    PATH_TO_DB: str = str(BASE_DIR / "database" / "source" / "movies.db")
    PATH_TO_MOVIES_CSV: str = str(BASE_DIR / "database" / "seed_db" / "imdb_movies.csv")

    PATH_TO_EMAIL_TEMPLATES_DIR: str = str(BASE_DIR / "notifications" / "templates")
    ACTIVATION_EMAIL_TEMPLATE_NAME: str = "activation_request.html"
    ACTIVATION_COMPLETE_EMAIL_TEMPLATE_NAME: str = "activation_complete.html"
    PASSWORD_RESET_TEMPLATE_NAME: str = "password_reset_request.html"
    PASSWORD_RESET_COMPLETE_TEMPLATE_NAME: str = "password_reset_complete.html"
    REPLY_TO_COMMENT_TEMPLATE_NAME: str = "comment_reply_notification.html"

    LOGIN_TIME_DAYS: int = 7

    EMAIL_HOST: str = "host"
    EMAIL_PORT: int = 25
    EMAIL_HOST_USER: str = "testuser"
    EMAIL_HOST_PASSWORD: str = "test_password"
    EMAIL_USE_TLS: bool = True
    MAILHOG_API_PORT: int = 8025

    STRIPE_SECRET_KEY: str = "sk_test_your_key_here"
    STRIPE_WEBHOOK_SECRET: str = "whsec_your_secret_here"
    STRIPE_SUCCESS_URL: str = "http://localhost:8000/api/v1/payments/success?session_id={CHECKOUT_SESSION_ID}"
    STRIPE_CANCEL_URL: str = "http://localhost:8000/api/v1/payments/canceled"

    MINIO_HOST: str = "minio-cinema"
    MINIO_PORT: int = 9000
    MINIO_ROOT_USER: str = "minioadmin"
    MINIO_ROOT_PASSWORD: str = "some_password"
    MINIO_STORAGE: str = "cinema-storage"

    @property
    def s3_storage_endpoint(self) -> str:
        return f"http://{self.MINIO_HOST}:{self.MINIO_PORT}"


class Settings(BaseAppSettings):
    ADMIN_EMAIL: str = "admin@admin.com"
    ADMIN_PASSWORD: str = "Admin123!"
    POSTGRES_USER: str = "test_user"
    POSTGRES_PASSWORD: str = "test_password"
    POSTGRES_HOST: str = "test_host"
    POSTGRES_DB_PORT: int = 5432
    POSTGRES_DB: str = "test_db"

    SECRET_KEY_ACCESS: str = "SECRET_KEY_ACCESS"
    SECRET_KEY_REFRESH: str = "SECRET_KEY_REFRESH"
    JWT_SIGNING_ALGORITHM: str = "HS256"


class TestingSettings(Settings):
    SECRET_KEY_ACCESS: str = "SECRET_KEY_ACCESS"
    SECRET_KEY_REFRESH: str = "SECRET_KEY_REFRESH"
    JWT_SIGNING_ALGORITHM: str = "HS256"

    def model_post_init(self, __context: dict[str, Any] | None = None) -> None:
        object.__setattr__(self, "PATH_TO_DB", ":memory:")
        object.__setattr__(
            self,
            "PATH_TO_MOVIES_CSV",
            str(self.BASE_DIR / "database" / "seed_data" / "test_data.csv")
        )
