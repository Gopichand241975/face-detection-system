"""Integration tests for ROI REST endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.face_detection import DetectionResult
from app.services.roi_service import save_roi


SESSION_A = "test-session-001"
SESSION_B = "test-session-002"


@pytest.mark.asyncio
async def test_health_liveness(client: AsyncClient):
    resp = await client.get("/health/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_health_ready(client: AsyncClient):
    resp = await client.get("/health/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["database"] == "ok"


@pytest.mark.asyncio
async def test_roi_not_found(client: AsyncClient):
    resp = await client.get("/roi/nonexistent-session/latest")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_roi_stats_not_found(client: AsyncClient):
    resp = await client.get("/roi/nonexistent-session/stats")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_save_and_retrieve_roi(client: AsyncClient, db_session: AsyncSession):
    # Seed two ROI records directly via the service
    r1 = await save_roi(db_session, SESSION_A, 1, DetectionResult(
        face_detected=True, x=10, y=20, width=80, height=90, confidence=0.92
    ))
    r2 = await save_roi(db_session, SESSION_A, 2, DetectionResult(
        face_detected=False
    ))
    await db_session.commit()

    # Paginated list
    resp = await client.get(f"/roi/{SESSION_A}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 2
    assert body["session_id"] == SESSION_A

    # Latest should be frame 2
    resp = await client.get(f"/roi/{SESSION_A}/latest")
    assert resp.status_code == 200
    latest = resp.json()
    assert latest["frame_number"] == 2
    assert latest["face_detected"] is False
    assert latest["bounding_box"] is None


@pytest.mark.asyncio
async def test_roi_stats(client: AsyncClient, db_session: AsyncSession):
    for i in range(1, 6):
        detected = i % 2 == 0   # even frames have a face
        await save_roi(db_session, SESSION_B, i, DetectionResult(
            face_detected=detected,
            x=10 if detected else None,
            y=10 if detected else None,
            width=50 if detected else None,
            height=50 if detected else None,
            confidence=0.85 if detected else None,
        ))
    await db_session.commit()

    resp = await client.get(f"/roi/{SESSION_B}/stats")
    assert resp.status_code == 200
    stats = resp.json()
    assert stats["total_frames"] == 5
    assert stats["frames_with_face"] == 2
    assert 0 < stats["detection_rate"] < 1


@pytest.mark.asyncio
async def test_sessions_list(client: AsyncClient, db_session: AsyncSession):
    await save_roi(db_session, "sess-list-test", 1, DetectionResult(face_detected=False))
    await db_session.commit()

    resp = await client.get("/roi/sessions")
    assert resp.status_code == 200
    body = resp.json()
    assert "sessions" in body
    ids = [s["session_id"] for s in body["sessions"]]
    assert "sess-list-test" in ids


@pytest.mark.asyncio
async def test_roi_list_pagination(client: AsyncClient, db_session: AsyncSession):
    sess = "pagination-test"
    for i in range(10):
        await save_roi(db_session, sess, i, DetectionResult(face_detected=False))
    await db_session.commit()

    resp = await client.get(f"/roi/{sess}?limit=5&offset=0")
    assert resp.status_code == 200
    assert resp.json()["count"] == 5

    resp2 = await client.get(f"/roi/{sess}?limit=5&offset=5")
    assert resp2.status_code == 200
    assert resp2.json()["count"] == 5


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "Face Detection API" in resp.json()["service"]
