import pytest_asyncio

from database import (
    reset_database
)
from httpx import AsyncClient, ASGITransport

from database.populate import CSVDatabaseSeeder
from main import app
from config.dependencies import get_settings
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession
from tests.doubles.stubs.emails import StubEmailSender
from tests.doubles.fakes.storage import FakeS3Storage
from config.dependencies import get_email_sender, get_s3_client
from storages.s3 import S3StorageClient
from database import get_db_contextmanager
from security.interfaces import JWTAuthManagerInterface
from security.token_manager import JWTAuthManager
from database.models.accounts import UserGroupEnum, UserGroup


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests"
    )
    config.addinivalue_line(
        "markers", "order: Specify the order of test execution"
    )
    config.addinivalue_line(
        "markers", "unit: Unit tests"
    )


@pytest_asyncio.fixture(scope="function", autouse=True)
async def reset_db(request):
    if "e2e" in request.keywords:
        yield
    else:
        await reset_database()
        yield


@pytest_asyncio.fixture(scope="session")
async def reset_db_once_for_e2e(request):
    await reset_database()


@pytest_asyncio.fixture(scope="session")
async def settings():
    return get_settings()


@pytest_asyncio.fixture(scope="session")
async def email_sender_stub():
    return StubEmailSender()


@pytest_asyncio.fixture(scope="session")
async def s3_storage_fake():
    return FakeS3Storage()


@pytest_asyncio.fixture(scope="session")
async def s3_client(settings):
    return S3StorageClient(
        endpoint_url=settings.s3_storage_endpoint,
        access_key=settings.MINIO_ROOT_USER,
        secret_key=settings.MINIO_ROOT_PASSWORD,
        bucket_name=settings.MINIO_STORAGE
    )


@pytest_asyncio.fixture(scope="function")
async def client(email_sender_stub, s3_storage_fake):
    app.dependency_overrides[get_email_sender] = lambda: email_sender_stub
    app.dependency_overrides[get_s3_client] = lambda: s3_storage_fake

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as async_client:
        yield async_client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="session")
async def e2e_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as async_client:
        yield async_client


@pytest_asyncio.fixture(scope="function")
async def db_session():
    async with get_db_contextmanager() as session:
        yield session


@pytest_asyncio.fixture(scope="session")
async def e2e_db_session():
    async with get_db_contextmanager() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def jwt_manager(settings) -> JWTAuthManagerInterface:
    return JWTAuthManager(
        secret_key_access=settings.SECRET_KEY_ACCESS,
        secret_key_refresh=settings.SECRET_KEY_REFRESH,
        algorithm=settings.JWT_SIGNING_ALGORITHM
    )


@pytest_asyncio.fixture(scope="function")
async def seed_user_groups(db_session: AsyncSession):
    groups = [{"name": group.value} for group in UserGroupEnum]
    await db_session.execute(insert(UserGroup).values(groups))
    await db_session.commit()
    yield db_session


@pytest_asyncio.fixture(scope="function")
async def seed_database(settings, db_session):
    seeder = CSVDatabaseSeeder(
        db_session=db_session,
        settings=settings,
        csv_file_path=settings.PATH_TO_MOVIES_CSV
    )

    await seeder.seed()
    yield db_session