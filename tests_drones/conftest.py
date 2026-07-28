"""
Fixtures for the drone orchard survey pipeline tests. Deliberately isolated
from the repo's root tests/ directory (tests/conftest.py imports several
modules that don't exist anywhere in the codebase - app.database.base,
app.api.main, app.core.config, app.core.security - and can't be collected).
Everything here runs against an in-memory SQLite DB - no real hardware or
Postgres required.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.auth import create_access_token
import app.models.user as user_models  # noqa: F401 - registers User/Farm/etc on Base
import app.models.drone as drone_models  # noqa: F401 - registers drone tables on Base
from app.models.user import Farm, User

import main as main_module


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def test_user(db_session):
    user = User(
        phone_number="+254700000000",
        email="farmer@example.com",
        full_name="Test Farmer",
        hashed_password="not-a-real-hash",
        role="farmer",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def other_user(db_session):
    user = User(
        phone_number="+254711111111",
        email="other@example.com",
        full_name="Other Farmer",
        hashed_password="not-a-real-hash",
        role="farmer",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_farm(db_session, test_user):
    farm = Farm(
        owner_id=test_user.id,
        name="Test Orchard",
        latitude=37.77,
        longitude=-122.4,
        size_acres=5.0,
        crop_type="mango",
    )
    db_session.add(farm)
    await db_session.commit()
    await db_session.refresh(farm)
    return farm


@pytest.fixture
def auth_headers(test_user):
    token = create_access_token({"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_auth_headers(other_user):
    token = create_access_token({"sub": str(other_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def client(db_session):
    async def _get_db_override():
        yield db_session

    main_module.app.dependency_overrides[get_db] = _get_db_override
    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    main_module.app.dependency_overrides.clear()
