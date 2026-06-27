"""SQLAlchemy ORM model for Region-of-Interest data."""

import uuid
from datetime import datetime

from sqlalchemy import Column, String, Float, Integer, DateTime, func
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class ROIRecord(Base):
    """
    Stores every detected face bounding box (axis-aligned minimal bounding box).

    Columns
    -------
    id            : UUID primary key
    session_id    : Groups frames belonging to one streaming session
    frame_number  : Sequential frame index within the session
    timestamp     : Wall-clock time of detection (UTC)
    x             : Left edge of bounding box (pixels)
    y             : Top edge of bounding box (pixels)
    width         : Width of bounding box (pixels)
    height        : Height of bounding box (pixels)
    confidence    : Detection confidence score [0, 1]
    frame_width   : Width of the source frame (pixels)
    frame_height  : Height of the source frame (pixels)
    """

    __tablename__ = "roi_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(64), nullable=False, index=True)
    frame_number = Column(Integer, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)
    width = Column(Float, nullable=False)
    height = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    frame_width = Column(Integer, nullable=False)
    frame_height = Column(Integer, nullable=False)

    def to_dict(self):
        return {
            "id": str(self.id),
            "session_id": self.session_id,
            "frame_number": self.frame_number,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "confidence": self.confidence,
            "frame_width": self.frame_width,
            "frame_height": self.frame_height,
        }
