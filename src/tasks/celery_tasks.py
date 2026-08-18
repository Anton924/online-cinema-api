import asyncio
from datetime import datetime, timezone

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from tasks.celery_app import app

from database.models.accounts import (
    ActivationTokenModel,
    PasswordResetTokenModel,
    RefreshTokenModel
)

from database.session_postgresql import POSTGRESQL_DATABASE_URL


@app.task
def clean_data_from_expired_tokens():
    asyncio.run(_clean_expired_tokens())



async def _clean_expired_tokens():
    engine = create_async_engine(POSTGRESQL_DATABASE_URL, echo=False)
    session_local = async_sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )
    now = datetime.now(timezone.utc)
    async with session_local() as db:
        token_tables = [
            ActivationTokenModel,
            PasswordResetTokenModel,
            RefreshTokenModel
        ]
        for token_model in token_tables:
            await db.execute(delete(token_model).where(token_model.expires_at < now))
            await db.commit()


