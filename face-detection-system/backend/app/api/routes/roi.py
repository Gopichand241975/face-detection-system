"""
ROI (Region of Interest) REST API.

Endpoints
---------
GET /roi/{session_id}          — paginated ROI records for a session
GET /roi/{session_id}/latest   — most recent ROI record
GET /roi/{session_id}/stats    — session-level aggregation
GET /roi/sessions              — list all sessions
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.roi_service import (
    get_roi_by_session,
    get_latest_roi,
    get_session_stats,
    list_sessions,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/sessions",
    summary="List all streaming sessions",
)
async def sessions(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    data = await list_sessions(db, limit=limit)
    return {"sessions": data, "count": len(data)}


@router.get(
    "/{session_id}",
    summary="Paginated ROI records for a session",
)
async def roi_list(
    session_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    records = await get_roi_by_session(db, session_id, limit=limit, offset=offset)
    return {
        "session_id": session_id,
        "count": len(records),
        "records": [r.to_dict() for r in records],
    }


@router.get(
    "/{session_id}/latest",
    summary="Most recent ROI record for a session",
)
async def roi_latest(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    record = await get_latest_roi(db, session_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No ROI data found for session '{session_id}'.",
        )
    return record.to_dict()


@router.get(
    "/{session_id}/stats",
    summary="Aggregate statistics for a session",
)
async def roi_stats(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    stats = await get_session_stats(db, session_id)
    if stats["total_frames"] == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No data found for session '{session_id}'.",
        )
    return stats
