
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator
import os

# PostgreSQL Connection String
# Use environment variables for flexibility
POSTGRES_USER = os.getenv("POSTGRES_USER", "factory_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "factory_password")
POSTGRES_DB = os.getenv("POSTGRES_DB", "factory_db")
# Default to localhost, assume Docker ports mapped
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "127.0.0.1") 
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# Create Async Engine
engine = create_async_engine(
    DATABASE_URL,
    echo=True, # Set to False in production
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
