"""SQLAlchemy ORM model for Region of Interest (ROI) records."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, Float, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class ROIRecord(Base):
    """
    Stores the axis-aligned minimal bounding box for a detected face
    in a single video frame.

    Columns
    -------
    id          : UUID primary key
    session_id  : groups frames belonging to one streaming session
    frame_number: sequential frame counter within the session
    timestamp   : UTC wall-clock time when the frame was processed
    x, y        : top-left corner of the bounding box (pixels)
    width       : bounding-box width  (pixels)
    height      : bounding-box height (pixels)
    confidence  : detector confidence score [0.0 – 1.0]
    face_detected: whether a face was found in this frame
    """

    __tablename__ = "roi_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    frame_number: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Bounding box — nullable when no face is detected
    x: Mapped[int | None] = mapped_column(Integer, nullable=True)
    y: Mapped[int | None] = mapped_column(Integer, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)

    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    face_detected: Mapped[bool] = mapped_column(default=False, nullable=False)

    __table_args__ = (
        Index("ix_roi_session_frame", "session_id", "frame_number"),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "session_id": self.session_id,
            "frame_number": self.frame_number,
            "timestamp": self.timestamp.isoformat(),
            "face_detected": self.face_detected,
            "bounding_box": {
                "x": self.x,
                "y": self.y,
                "width": self.width,
                "height": self.height,
            } if self.face_detected else None,
            "confidence": self.confidence,
        }
