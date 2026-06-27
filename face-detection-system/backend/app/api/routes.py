"""
API Router – three primary endpoints plus a WebSocket stream.

Endpoint summary
----------------
POST /api/v1/stream/ingest          – Receive raw video frames (multipart or binary JPEG)
GET  /api/v1/stream/feed            – Server-Sent Events / MJPEG annotated stream
GET  /api/v1/roi                    – Query stored ROI records
WS   /api/v1/ws/stream              – Bidirectional WebSocket (client pushes frames, server pushes annotated frames)
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.services.face_detector import FaceDetector
from app.services.roi_service import save_roi, get_roi_for_session, get_latest_roi

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Shared in-memory frame buffer (single-producer, multi-consumer) ───────────
# Maps session_id -> latest annotated JPEG bytes
_latest_frames: dict[str, bytes] = {}
_frame_counters: dict[str, int] = {}


# ── 1. Ingest endpoint ────────────────────────────────────────────────────────

@router.post(
    "/stream/ingest",
    summary="Receive a single video frame for processing",
    tags=["Stream"],
    status_code=200,
)
async def ingest_frame(
    file: UploadFile = File(..., description="JPEG/PNG frame from the client"),
    session_id: Optional[str] = Query(None, description="Session identifier; auto-generated if omitted"),
    db: AsyncSession = Depends(get_db),
):
    """
    **Endpoint 1 – Video Ingest**

    Accepts a raw image frame (JPEG or PNG), runs face detection, persists the
    ROI to PostgreSQL, and buffers the annotated frame for streaming.

    Returns JSON with the detected ROI (or null) and the session_id to use for
    subsequent calls.
    """
    if session_id is None:
        session_id = str(uuid.uuid4())

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file upload.")

    detector = FaceDetector(confidence_threshold=settings.FACE_CONFIDENCE_THRESHOLD)
    try:
        annotated_jpeg, bbox = detector.detect(raw)
    except Exception as exc:
        logger.exception("Detection failed: %s", exc)
        raise HTTPException(status_code=422, detail=f"Frame processing error: {exc}")
    finally:
        detector.close()

    # Update per-session frame counter
    counter = _frame_counters.get(session_id, 0) + 1
    _frame_counters[session_id] = counter

    # Store annotated frame in buffer
    _latest_frames[session_id] = annotated_jpeg

    # Persist ROI to DB (only if face detected)
    roi_data = None
    if bbox is not None:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(raw))
        fw, fh = img.size

        record = await save_roi(
            db,
            session_id=session_id,
            frame_number=counter,
            bbox=bbox,
            frame_width=fw,
            frame_height=fh,
        )
        roi_data = record.to_dict()

    return {
        "session_id": session_id,
        "frame_number": counter,
        "face_detected": bbox is not None,
        "roi": roi_data,
    }


# ── 2. Stream (serve) endpoint ────────────────────────────────────────────────

@router.get(
    "/stream/feed",
    summary="Stream annotated video as MJPEG",
    tags=["Stream"],
    response_class=StreamingResponse,
)
async def stream_feed(
    session_id: str = Query(..., description="Session ID whose frames to stream"),
):
    """
    **Endpoint 2 – Video Feed**

    Returns a multipart/x-mixed-replace MJPEG stream of annotated frames for
    the given session.  The browser (or any MJPEG client) can render this
    directly via an `<img src="...">` tag.
    """

    async def generate():
        boundary = b"--frame\r\n"
        header = b"Content-Type: image/jpeg\r\n\r\n"
        sent = 0
        while True:
            frame = _latest_frames.get(session_id)
            if frame and len(frame) != sent:
                sent = len(frame)
                yield boundary + header + frame + b"\r\n"
            await asyncio.sleep(0.033)  # ~30 fps ceiling

    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── 3. ROI data endpoint ──────────────────────────────────────────────────────

@router.get(
    "/roi",
    summary="Query stored ROI records",
    tags=["ROI"],
)
async def get_roi(
    session_id: Optional[str] = Query(None, description="Filter by session; returns latest if omitted"),
    limit: int = Query(50, ge=1, le=settings.ROI_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    **Endpoint 3 – ROI Data**

    Returns stored face bounding-box records from PostgreSQL.

    - If *session_id* is supplied → returns that session's records (newest first).
    - If omitted → returns the single most-recent detection across all sessions.
    """
    if session_id:
        records = await get_roi_for_session(db, session_id, limit=limit, offset=offset)
        return {
            "session_id": session_id,
            "count": len(records),
            "records": [r.to_dict() for r in records],
        }
    else:
        record = await get_latest_roi(db)
        if record is None:
            return {"session_id": None, "count": 0, "records": []}
        return {
            "session_id": record.session_id,
            "count": 1,
            "records": [record.to_dict()],
        }


# ── 4. WebSocket endpoint (bidirectional real-time) ───────────────────────────

@router.websocket("/ws/stream")
async def websocket_stream(
    websocket: WebSocket,
    session_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    **WebSocket – Bidirectional frame stream**

    Client sends raw JPEG bytes → server responds with annotated JPEG bytes.
    ROI data is also persisted per frame.

    Protocol:
    - Client sends binary frame data.
    - Server responds with annotated JPEG (binary).
    - Server also sends a JSON text message with ROI metadata after each frame.
    """
    await websocket.accept()

    if session_id is None:
        session_id = str(uuid.uuid4())

    detector = FaceDetector(confidence_threshold=settings.FACE_CONFIDENCE_THRESHOLD)
    logger.info("WebSocket session started: %s", session_id)

    try:
        while True:
            raw = await websocket.receive_bytes()
            if not raw:
                continue

            counter = _frame_counters.get(session_id, 0) + 1
            _frame_counters[session_id] = counter

            try:
                annotated_jpeg, bbox = detector.detect(raw)
            except Exception as exc:
                logger.warning("WS detection error: %s", exc)
                await websocket.send_text(f'{{"error": "{exc}"}}')
                continue

            _latest_frames[session_id] = annotated_jpeg

            # Send annotated frame back
            await websocket.send_bytes(annotated_jpeg)

            roi_data = None
            if bbox is not None:
                from PIL import Image
                import io
                img = Image.open(io.BytesIO(raw))
                fw, fh = img.size
                record = await save_roi(
                    db,
                    session_id=session_id,
                    frame_number=counter,
                    bbox=bbox,
                    frame_width=fw,
                    frame_height=fh,
                )
                roi_data = record.to_dict()

            import json
            await websocket.send_text(json.dumps({
                "session_id": session_id,
                "frame_number": counter,
                "face_detected": bbox is not None,
                "roi": roi_data,
            }))

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: %s", session_id)
    except Exception as exc:
        logger.exception("Unexpected WS error: %s", exc)
    finally:
        detector.close()
