"""Unit/integration tests for roi_service CRUD functions."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.face_detection import DetectionResult
from app.services.roi_service import (
    save_roi,
    get_roi_by_session,
    get_latest_roi,
    get_session_stats,
    list_sessions,
)

SESSION = "service-test-session"


@pytest.mark.asyncio
async def test_save_roi_face_detected(db_session: AsyncSession):
    result = DetectionResult(
        face_detected=True, x=5, y=10, width=100, height=120, confidence=0.97
    )
    record = await save_roi(db_session, SESSION, 1, result)
    await db_session.commit()

    assert record.id is not None
    assert record.face_detected is True
    assert record.x == 5
    assert record.confidence == pytest.approx(0.97, abs=1e-4)


@pytest.mark.asyncio
async def test_save_roi_no_face(db_session: AsyncSession):
    result = DetectionResult(face_detected=False)
    record = await save_roi(db_session, SESSION, 2, result)
    await db_session.commit()

    assert record.face_detected is False
    assert record.x is None
    assert record.confidence is None


@pytest.mark.asyncio
async def test_get_roi_by_session_returns_desc(db_session: AsyncSession):
    sess = "desc-order-test"
    for i in range(1, 4):
        await save_roi(db_session, sess, i, DetectionResult(face_detected=False))
    await db_session.commit()

    records = await get_roi_by_session(db_session, sess)
    frame_numbers = [r.frame_number for r in records]
    assert frame_numbers == sorted(frame_numbers, reverse=True)


@pytest.mark.asyncio
async def test_get_latest_roi_none_when_empty(db_session: AsyncSession):
    record = await get_latest_roi(db_session, "empty-session-xyz")
    assert record is None


@pytest.mark.asyncio
async def test_to_dict_structure(db_session: AsyncSession):
    result = DetectionResult(
        face_detected=True, x=1, y=2, width=3, height=4, confidence=0.5
    )
    record = await save_roi(db_session, "dict-test", 1, result)
    await db_session.commit()

    d = record.to_dict()
    assert "id" in d
    assert "bounding_box" in d
    assert d["bounding_box"]["x"] == 1
    assert d["confidence"] == pytest.approx(0.5, abs=1e-4)


@pytest.mark.asyncio
async def test_to_dict_no_face(db_session: AsyncSession):
    record = await save_roi(db_session, "dict-test-nf", 1, DetectionResult(face_detected=False))
    await db_session.commit()

    d = record.to_dict()
    assert d["bounding_box"] is None
    assert d["face_detected"] is False


@pytest.mark.asyncio
async def test_session_stats_detection_rate(db_session: AsyncSession):
    sess = "stats-rate-test"
    for i in range(1, 11):
        # 5 with face, 5 without
        await save_roi(db_session, sess, i, DetectionResult(
            face_detected=(i <= 5),
            x=10 if i <= 5 else None,
            y=10 if i <= 5 else None,
            width=50 if i <= 5 else None,
            height=50 if i <= 5 else None,
            confidence=0.9 if i <= 5 else None,
        ))
    await db_session.commit()

    stats = await get_session_stats(db_session, sess)
    assert stats["total_frames"] == 10
    assert stats["frames_with_face"] == 5
    assert stats["detection_rate"] == pytest.approx(0.5, abs=1e-4)
