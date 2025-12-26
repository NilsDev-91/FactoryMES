
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator
import os

# PostgreSQL Connection String
POSTGRES_USER = os.getenv("POSTGRES_USER", "factory_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "factory_password")
POSTGRES_DB = os.getenv("POSTGRES_DB", "factory_db")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "127.0.0.1") 
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

DEFAULT_DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
# DEFAULT_DATABASE_URL = "sqlite+aiosqlite:///factory.db"

# Use DATABASE_URL env var if available, otherwise default to constructed string
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

# Create Async Engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False, # Set to False in production
    future=True
)

# Async Session Factory
async_session_maker = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# Dependency for FastAPI
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
