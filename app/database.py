from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for models
Base = declarative_base()


# Dependency to get DB session
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# SQLAlchemy relationship() targets declared as strings (e.g. "Diagnosis")
# only resolve against classes that have actually been imported somewhere -
# configuring the mapper for User/Farm without diagnosis.py/sensor.py/
# permit.py already loaded raises InvalidRequestError ("failed to locate a
# name"). Importing the full model set here, after Base is defined, means
# anything that does `from app.database import ...` (every script and
# router already does) gets a fully resolvable registry, instead of each
# caller having to know and import the whole transitive relationship graph
# by hand. Import order doesn't matter - SQLAlchemy resolves all string
# relationships together once every module below has executed.
from app.models import user as _user_models  # noqa: E402,F401
from app.models import diagnosis as _diagnosis_models  # noqa: E402,F401
from app.models import sensor as _sensor_models  # noqa: E402,F401
from app.models import permit as _permit_models  # noqa: E402,F401
from app.models import drone as _drone_models  # noqa: E402,F401
