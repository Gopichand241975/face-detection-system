"""
Integration tests for the FastAPI endpoints.
Uses httpx AsyncClient with a SQLite in-memory database (no real PostgreSQL needed).
"""

import io
import json
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from PIL import Image

from app.main import app
from app.core.database import Base, engine


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create tables before each test, drop after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _blank_jpeg(w=320, h=240) -> bytes:
    img = Image.new("RGB", (w, h), color=(180, 180, 180))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


class TestHealth:
    @pytest.mark.asyncio
    async def test_health_returns_ok(self, client):
        r = await client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestIngestEndpoint:
    @pytest.mark.asyncio
    async def test_ingest_blank_frame(self, client):
        files = {"file": ("frame.jpg", _blank_jpeg(), "image/jpeg")}
        r = await client.post("/api/v1/stream/ingest", files=files)
        assert r.status_code == 200
        body = r.json()
        assert "session_id" in body
        assert "frame_number" in body
        assert body["frame_number"] == 1
        assert body["face_detected"] is False

    @pytest.mark.asyncio
    async def test_ingest_returns_session_id(self, client):
        files = {"file": ("frame.jpg", _blank_jpeg(), "image/jpeg")}
        r = await client.post("/api/v1/stream/ingest?session_id=test-sess-1", files=files)
        assert r.status_code == 200
        assert r.json()["session_id"] == "test-sess-1"

    @pytest.mark.asyncio
    async def test_ingest_increments_frame_counter(self, client):
        files = {"file": ("frame.jpg", _blank_jpeg(), "image/jpeg")}
        r1 = await client.post("/api/v1/stream/ingest?session_id=sess-cnt", files=files)
        r2 = await client.post("/api/v1/stream/ingest?session_id=sess-cnt", files=files)
        assert r1.json()["frame_number"] == 1
        assert r2.json()["frame_number"] == 2

    @pytest.mark.asyncio
    async def test_ingest_empty_file_returns_400(self, client):
        files = {"file": ("empty.jpg", b"", "image/jpeg")}
        r = await client.post("/api/v1/stream/ingest", files=files)
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_ingest_invalid_data_returns_422(self, client):
        files = {"file": ("bad.jpg", b"not-an-image", "image/jpeg")}
        r = await client.post("/api/v1/stream/ingest", files=files)
        assert r.status_code == 422


class TestROIEndpoint:
    @pytest.mark.asyncio
    async def test_roi_no_data_returns_empty(self, client):
        r = await client.get("/api/v1/roi?session_id=nonexistent")
        assert r.status_code == 200
        body = r.json()
        assert body["count"] == 0
        assert body["records"] == []

    @pytest.mark.asyncio
    async def test_roi_global_latest_no_data(self, client):
        r = await client.get("/api/v1/roi")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_roi_pagination_params(self, client):
        r = await client.get("/api/v1/roi?session_id=x&limit=10&offset=0")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_roi_limit_too_large(self, client):
        r = await client.get("/api/v1/roi?session_id=x&limit=9999")
        assert r.status_code == 422  # FastAPI validation rejects > ROI_PAGE_SIZE


class TestStreamFeedEndpoint:
    @pytest.mark.asyncio
    async def test_stream_starts_without_frames(self, client):
        """Feed endpoint must return 200 immediately even with no frames."""
        import asyncio
        async with client.stream("GET", "/api/v1/stream/feed?session_id=new-sess") as r:
            assert r.status_code == 200
            # Read a small chunk then stop
            async for chunk in r.aiter_bytes():
                break
