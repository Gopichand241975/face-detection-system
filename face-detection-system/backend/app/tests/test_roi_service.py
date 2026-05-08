"""Unit tests for the ROI database service layer."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.core.database import Base
from app.services.face_detector import BoundingBox
from app.services.roi_service import save_roi, get_roi_for_session, get_latest_roi


TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSession = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestSession() as session:
        yield session
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


def _bbox(conf=0.9):
    return BoundingBox(x=50, y=60, width=120, height=130, confidence=conf)


class TestSaveROI:
    @pytest.mark.asyncio
    async def test_save_returns_record(self, db):
        rec = await save_roi(
            db, session_id="s1", frame_number=1,
            bbox=_bbox(), frame_width=640, frame_height=480,
        )
        assert rec.id is not None
        assert rec.session_id == "s1"
        assert rec.frame_number == 1
        assert rec.confidence == pytest.approx(0.9, abs=1e-4)

    @pytest.mark.asyncio
    async def test_save_multiple_records(self, db):
        for i in range(5):
            await save_roi(
                db, session_id="s2", frame_number=i,
                bbox=_bbox(0.8 + i * 0.01), frame_width=320, frame_height=240,
            )
        records = await get_roi_for_session(db, "s2")
        assert len(records) == 5


class TestGetROIForSession:
    @pytest.mark.asyncio
    async def test_empty_session_returns_empty(self, db):
        records = await get_roi_for_session(db, "no-such-session")
        assert records == []

    @pytest.mark.asyncio
    async def test_returns_correct_session_only(self, db):
        await save_roi(db, session_id="A", frame_number=1, bbox=_bbox(), frame_width=320, frame_height=240)
        await save_roi(db, session_id="B", frame_number=1, bbox=_bbox(), frame_width=320, frame_height=240)
        recs = await get_roi_for_session(db, "A")
        assert all(r.session_id == "A" for r in recs)

    @pytest.mark.asyncio
    async def test_limit_respected(self, db):
        for i in range(10):
            await save_roi(db, session_id="lim", frame_number=i, bbox=_bbox(), frame_width=320, frame_height=240)
        recs = await get_roi_for_session(db, "lim", limit=3)
        assert len(recs) == 3


class TestGetLatestROI:
    @pytest.mark.asyncio
    async def test_latest_returns_none_when_empty(self, db):
        rec = await get_latest_roi(db)
        assert rec is None

    @pytest.mark.asyncio
    async def test_latest_returns_most_recent(self, db):
        await save_roi(db, session_id="lat", frame_number=1, bbox=_bbox(), frame_width=320, frame_height=240)
        await save_roi(db, session_id="lat", frame_number=99, bbox=_bbox(0.99), frame_width=320, frame_height=240)
        rec = await get_latest_roi(db, "lat")
        assert rec is not None
