"""Database CRUD operations for ROI records."""

from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.roi import ROIRecord
from app.services.face_detector import BoundingBox
from app.core.config import settings

logger = logging.getLogger(__name__)


async def save_roi(
    db: AsyncSession,
    *,
    session_id: str,
    frame_number: int,
    bbox: BoundingBox,
    frame_width: int,
    frame_height: int,
) -> ROIRecord:
    """Persist a single ROI detection to the database."""
    record = ROIRecord(
        session_id=session_id,
        frame_number=frame_number,
        x=round(bbox.x, 2),
        y=round(bbox.y, 2),
        width=round(bbox.width, 2),
        height=round(bbox.height, 2),
        confidence=round(bbox.confidence, 4),
        frame_width=frame_width,
        frame_height=frame_height,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)
    logger.debug("Saved ROI frame=%d session=%s", frame_number, session_id)
    return record


async def get_roi_for_session(
    db: AsyncSession,
    session_id: str,
    limit: int = settings.ROI_PAGE_SIZE,
    offset: int = 0,
) -> List[ROIRecord]:
    """Return ROI records for a given session, newest first."""
    result = await db.execute(
        select(ROIRecord)
        .where(ROIRecord.session_id == session_id)
        .order_by(desc(ROIRecord.frame_number))
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


async def get_latest_roi(
    db: AsyncSession,
    session_id: Optional[str] = None,
) -> Optional[ROIRecord]:
    """Return the single most-recent ROI record (optionally scoped to a session)."""
    query = select(ROIRecord).order_by(desc(ROIRecord.timestamp))
    if session_id:
        query = query.where(ROIRecord.session_id == session_id)
    result = await db.execute(query.limit(1))
    return result.scalar_one_or_none()
