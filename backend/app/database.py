import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/fraudnet")
if DATABASE_URL.startswith("postgresql://") and not DATABASE_URL.startswith("postgresql+asyncpg://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

SYNC_DATABASE_URL = os.getenv("SYNC_DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/fraudnet")
if SYNC_DATABASE_URL.startswith("postgresql+asyncpg://"):
    SYNC_DATABASE_URL = SYNC_DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)

# Async engine for FastAPI
async_engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

# Sync engine for seeding/migrations/simulator
sync_engine = create_engine(SYNC_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
