import io
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest_asyncio
from PIL import Image

from database import (
    reset_database
)
from httpx import AsyncClient, ASGITransport

from database.populate import CSVDatabaseSeeder
from main import app
from config.dependencies import get_settings
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from tests.doubles.stubs.emails import StubEmailSender
from tests.doubles.fakes.storage import FakeS3Storage
from config.dependencies import get_email_sender, get_s3_client, get_payment_gateway
from storages.s3 import S3StorageClient
from database import get_db_contextmanager
from security.interfaces import JWTAuthManagerInterface
from security.token_manager import JWTAuthManager
from database.models.accounts import UserGroup, UserModel, UserGroupEnum, UserProfileModel
from database.models.movies import CertificationModel, MovieModel, GenreModel, StarModel, DirectorModel, MovieCommentModel
from database.models.carts import CartModel, CartItem
from database.models.orders import StatusOrderEnum, OrderModel, OrderItemModel
from payments.interfaces import PaymentGatewayInterface
from tests.doubles.fakes.stripe import FakeStripeMetadata
from database.models.payments import PaymentModel, PaymentStatus


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
async def payment_gateway_fake():
    gateway = AsyncMock(spec=PaymentGatewayInterface)
    gateway.create_checkout_session.return_value = SimpleNamespace(
        id="cs_test_a1b2c3d4e5f6g7h8i9j0",
        url="https://checkout.stripe.com/c/pay/cs_test_a1b2c3d4e5f6g7h8i9j0"
    )
    return gateway


@pytest_asyncio.fixture(scope="function")
async def client(email_sender_stub, s3_storage_fake, payment_gateway_fake):
    app.dependency_overrides[get_email_sender] = lambda: email_sender_stub
    app.dependency_overrides[get_s3_client] = lambda: s3_storage_fake
    app.dependency_overrides[get_payment_gateway] = lambda: payment_gateway_fake

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


async def create_active_user_with_token(db_session, jwt_manager, group=UserGroupEnum.USER, email="user@example.com"):
    group_row = (await db_session.execute(
        select(UserGroup).where(UserGroup.name == group)
    )).scalars().first()
    user = UserModel.create(
        email=email,
        raw_password="StrongPassword123!",
        group_id=group_row.id
    )
    user.is_active = True
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    access_token = jwt_manager.create_access_token(data={"user_id": user.id})
    return user, access_token


async def create_movie(db_session, name="Inception", price=9.99, certification_name="R"):
    certification = CertificationModel(name=certification_name)
    db_session.add(certification)
    await db_session.flush()
    movie = MovieModel(
        name=name,
        year=2010,
        time=148,
        imdb=8.8,
        votes=100,
        description="A mind-bending thriller.",
        price=price,
        certification_id=certification.id
    )
    db_session.add(movie)
    await db_session.commit()
    await db_session.refresh(movie)
    return movie


async def add_item_to_cart_directly(db_session, user, movie) -> CartModel:
    cart = (await db_session.execute(select(CartModel).where(CartModel.user_id == user.id))).scalars().first()
    if not cart:
        cart = CartModel(user_id=user.id)
        db_session.add(cart)
        await db_session.flush()
    db_session.add(CartItem(cart_id=cart.id, movie_id=movie.id))
    await db_session.commit()
    await db_session.refresh(cart)
    return cart


async def create_order_directly(db_session, user, movie, status=StatusOrderEnum.PAID) -> OrderModel:
    order = OrderModel(user_id=user.id, status=status, order_sum=movie.price)
    db_session.add(order)
    await db_session.flush()
    db_session.add(OrderItemModel(order_id=order.id, movie_id=movie.id, price_at_order=movie.price))
    await db_session.commit()
    await db_session.refresh(order)
    return order


async def make_image_bytes(fmt="JPEG", size=(10, 10)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size=size, color="red").save(buffer, format=fmt)
    return buffer.getvalue()


async def create_profile_for_user(db_session, user, **fields):
    profile = UserProfileModel(user_id=user.id, **fields)
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)
    return profile


async def create_certification_directly(db_session, name="PG-13") -> CertificationModel:
    certification = CertificationModel(name=name)
    db_session.add(certification)
    await db_session.commit()
    await db_session.refresh(certification)
    return certification


async def create_genre_directly(db_session, name="Action") -> GenreModel:
    genre = GenreModel(name=name)
    db_session.add(genre)
    await db_session.commit()
    await db_session.refresh(genre)
    return genre


async def create_star_directly(db_session, name="Tom Hardy") -> StarModel:
    star = StarModel(name=name)
    db_session.add(star)
    await db_session.commit()
    await db_session.refresh(star)
    return star


async def create_director_directly(db_session, name="Christopher Nolan") -> DirectorModel:
    director = DirectorModel(name=name)
    db_session.add(director)
    await db_session.commit()
    await db_session.refresh(director)
    return director


async def create_comment_directly(db_session, user_id: int, movie_id: int, parent_id: int = None, comment="Great movie!") -> DirectorModel:
    comment = MovieCommentModel(comment=comment, user_id=user_id, movie_id=movie_id, parent_id=parent_id)
    db_session.add(comment)
    await db_session.commit()
    await db_session.refresh(comment)
    return comment


async def create_movie_full(db_session, **overrides) -> MovieModel:
    certification = overrides.pop("certification", None) or await create_certification_directly(db_session)
    defaults = dict(
        name="Inception", year=2010, time=148, imdb=8.8, votes=100,
        description="A mind-bending thriller.", price=9.99, certification_id=certification.id
    )
    defaults.update(overrides)
    movie = MovieModel(**defaults)
    db_session.add(movie)
    await db_session.commit()
    await db_session.refresh(movie)
    return movie


def build_checkout_completed_event(
        order_id,
        user_id,
        session_id="cs_test_123",
        payment_intent_id="pi_test_123",
        payment_status="paid"
):
    return {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": session_id,
                "payment_intent": payment_intent_id,
                "payment_status": payment_status,
                "metadata": FakeStripeMetadata({
                    "order_id": str(order_id),
                    "user_id": str(user_id)
                })
            }
        }
    }


async def create_payment_directly(
        db_session,
        order,
        user,
        status: PaymentStatus = PaymentStatus.SUCCESSFUL,
        external_payment_id="cs_test_123",
        payment_intent_id="pi_3Oa1b2c3D4e5F6g7H8i9J0k1"
) -> PaymentModel:
    payment = PaymentModel(
        order_id=order.id,
        user_id=user.id,
        status=status,
        external_payment_id=external_payment_id,
        payment_intent_id=payment_intent_id,
    )
    db_session.add(payment)
    await db_session.commit()
    await db_session.refresh(payment)
    return payment
