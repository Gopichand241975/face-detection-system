"""
Video API routes.

Endpoints
---------
POST /video/ingest          — HTTP: receive a single JPEG frame
WS   /video/ws/{session_id} — WebSocket: bidirectional streaming
GET  /video/stream/{session_id} — HTTP MJPEG stream (for <img> tag)
"""

import asyncio
import logging
import time
import uuid
from collections import deque
from typing import Dict

import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.face_detection import FaceDetectionService
from app.services.roi_service import save_roi
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory frame buffer: session_id -> deque of latest JPEG bytes
# (bounded so we never exhaust RAM)
_frame_buffers: Dict[str, deque] = {}
_BUFFER_SIZE = 5


def _get_or_create_buffer(session_id: str) -> deque:
    if session_id not in _frame_buffers:
        _frame_buffers[session_id] = deque(maxlen=_BUFFER_SIZE)
    return _frame_buffers[session_id]


# ── WebSocket — ingest + serve simultaneously ─────────────────────────────────

@router.websocket("/ws/{session_id}")
async def video_websocket(
    websocket: WebSocket,
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    WebSocket endpoint for real-time video streaming.

    Protocol
    --------
    Client → Server: raw JPEG bytes (one frame per message)
    Server → Client: annotated JPEG bytes with ROI drawn by Pillow
    """
    await websocket.accept()
    logger.info("WebSocket connected: session=%s", session_id)

    buf = _get_or_create_buffer(session_id)
    detector = FaceDetectionService()
    frame_number = 0

    try:
        while True:
            # Receive raw frame bytes from the client
            try:
                raw = await asyncio.wait_for(websocket.receive_bytes(), timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning("WebSocket timeout: session=%s", session_id)
                break

            # Decode JPEG → numpy RGB
            try:
                frame_rgb = _jpeg_to_rgb(raw)
            except Exception as exc:
                logger.warning("Frame decode error: %s", exc)
                await websocket.send_json({"error": "invalid frame data"})
                continue

            frame_number += 1

            # Detect face
            result = detector.detect(frame_rgb)

            # Persist to DB (every frame)
            try:
                await save_roi(db, session_id, frame_number, result)
                await db.commit()
            except Exception as exc:
                logger.error("DB save error: %s", exc)
                await db.rollback()

            # Draw ROI using Pillow (not OpenCV)
            annotated_jpeg = detector.draw_roi(frame_rgb, result)

            # Update the MJPEG buffer so HTTP /stream viewers see the frame
            buf.append(annotated_jpeg)

            # Send annotated frame + ROI metadata back to WS client
            await websocket.send_bytes(annotated_jpeg)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: session=%s  frames=%d", session_id, frame_number)
    except Exception as exc:
        logger.exception("WebSocket error: session=%s  err=%s", session_id, exc)
    finally:
        detector.close()


# ── HTTP MJPEG stream — for <img src="..."> usage ────────────────────────────

@router.get("/stream/{session_id}", summary="MJPEG stream for a session")
async def mjpeg_stream(session_id: str):
    """
    Serves the latest annotated frames as a Motion-JPEG stream.
    Compatible with any browser <img> or <video> element.
    """
    buf = _get_or_create_buffer(session_id)

    async def generate():
        boundary = b"--frame"
        while True:
            if buf:
                frame = buf[-1]
                yield (
                    boundary
                    + b"\r\nContent-Type: image/jpeg\r\n\r\n"
                    + frame
                    + b"\r\n"
                )
            await asyncio.sleep(1 / settings.MAX_FRAME_RATE)

    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache", "X-Session-Id": session_id},
    )


# ── Single-frame HTTP ingest ──────────────────────────────────────────────────

@router.post(
    "/ingest/{session_id}",
    status_code=status.HTTP_200_OK,
    summary="Ingest a single JPEG frame via HTTP POST",
)
async def ingest_frame(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    # Body is raw bytes — handled below
):
    """
    Alternative to WebSocket for environments that can't use WS.
    Send raw JPEG bytes as the request body.
    Returns annotated JPEG + ROI JSON.
    """
    from fastapi import Request

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Use the dedicated /video/ingest-frame route for HTTP frame upload.",
    )


@router.post(
    "/ingest-frame/{session_id}",
    summary="Upload a single raw JPEG frame and receive annotated result",
)
async def ingest_frame_http(
    session_id: str,
    request,
    db: AsyncSession = Depends(get_db),
):
    """Accepts raw JPEG bytes; returns annotated JPEG bytes + ROI metadata."""
    from fastapi import Request
    if not isinstance(request, type):
        body = await request.body()
    else:
        raise HTTPException(400, "Must send raw JPEG bytes in the request body.")

    if len(body) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Frame too large.")

    try:
        frame_rgb = _jpeg_to_rgb(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Could not decode JPEG frame.")

    detector = FaceDetectionService()
    try:
        result = detector.detect(frame_rgb)
        roi_record = await save_roi(db, session_id, 0, result)
        await db.commit()
        annotated = detector.draw_roi(frame_rgb, result)
    finally:
        detector.close()

    buf = _get_or_create_buffer(session_id)
    buf.append(annotated)

    return StreamingResponse(
        iter([annotated]),
        media_type="image/jpeg",
        headers={
            "X-Face-Detected": str(result.face_detected).lower(),
            "X-ROI-X": str(result.x or ""),
            "X-ROI-Y": str(result.y or ""),
            "X-ROI-Width": str(result.width or ""),
            "X-ROI-Height": str(result.height or ""),
            "X-Confidence": str(result.confidence or ""),
        },
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _jpeg_to_rgb(data: bytes) -> np.ndarray:
    """Decode JPEG bytes → RGB numpy array without OpenCV."""
    from PIL import Image
    import io

    img = Image.open(io.BytesIO(data)).convert("RGB")
    return np.array(img)
