"""
pytest configuration and shared fixtures.

Uses an in-memory SQLite database so tests run without Postgres.
"""

import asyncio
import io
import os
from typing import AsyncGenerator

import numpy as np
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Point at SQLite BEFORE importing any app modules that read DATABASE_URL
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["CORS_ORIGINS"] = '["*"]'

from app.main import app
from app.db.database import Base, get_db


# ── In-memory SQLite engine ───────────────────────────────────────────────────

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient wired to the FastAPI app with a test DB session."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ── Image helpers ─────────────────────────────────────────────────────────────

def make_rgb_frame(width: int = 320, height: int = 240) -> np.ndarray:
    """Create a blank RGB numpy array (no face — used for unit tests)."""
    return np.zeros((height, width, 3), dtype=np.uint8)


def make_jpeg_bytes(width: int = 320, height: int = 240) -> bytes:
    """Create a minimal JPEG byte string."""
    img = Image.fromarray(make_rgb_frame(width, height), "RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()
