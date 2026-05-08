"""
Face detection service.

Uses MediaPipe Face Detection — explicitly avoids OpenCV.
Drawing uses Pillow (PIL) to render the axis-aligned minimal bounding box.
"""

import io
import logging
from dataclasses import dataclass
from typing import Optional

import mediapipe as mp
import numpy as np
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)


@dataclass
class DetectionResult:
    face_detected: bool
    x: Optional[int] = None
    y: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    confidence: Optional[float] = None


class FaceDetectionService:
    """
    Wraps MediaPipe short-range face detector.

    Thread / async note: MediaPipe objects are NOT thread-safe — each
    instance should be used from a single task / thread.  The streaming
    endpoint creates one instance per WebSocket connection.
    """

    BOX_COLOR = (0, 255, 0)        # Green rectangle
    BOX_WIDTH = 3                   # Border thickness (px)
    LABEL_COLOR = (0, 255, 0)
    LABEL_BG = (0, 0, 0, 160)      # Semi-transparent black label background

    def __init__(self, min_detection_confidence: float = 0.5):
        self._mp_face = mp.solutions.face_detection
        self._detector = self._mp_face.FaceDetection(
            model_selection=0,                          # 0 = short range (≤2 m)
            min_detection_confidence=min_detection_confidence,
        )
        logger.info("FaceDetectionService initialised (MediaPipe).")

    # ── Public API ────────────────────────────────────────────────────────────

    def detect(self, frame_rgb: np.ndarray) -> DetectionResult:
        """
        Run face detection on an RGB numpy array.

        Returns a DetectionResult.  Bounding-box coordinates are in
        absolute pixels relative to the frame dimensions.
        """
        h, w = frame_rgb.shape[:2]
        results = self._detector.process(frame_rgb)

        if not results.detections:
            return DetectionResult(face_detected=False)

        # Task states only one face — take the highest-confidence detection
        best = max(results.detections, key=lambda d: d.score[0])
        bbox = best.location_data.relative_bounding_box

        # Convert relative → absolute, clamp to frame boundaries
        x = max(0, int(bbox.xmin * w))
        y = max(0, int(bbox.ymin * h))
        bw = min(int(bbox.width * w), w - x)
        bh = min(int(bbox.height * h), h - y)

        return DetectionResult(
            face_detected=True,
            x=x,
            y=y,
            width=bw,
            height=bh,
            confidence=round(float(best.score[0]), 4),
        )

    def draw_roi(self, frame_rgb: np.ndarray, result: DetectionResult) -> bytes:
        """
        Draw an axis-aligned minimal bounding box on the frame using Pillow
        (NOT OpenCV) and return the annotated frame as JPEG bytes.
        """
        img = Image.fromarray(frame_rgb, mode="RGB")

        if result.face_detected:
            draw = ImageDraw.Draw(img, "RGBA")

            x1, y1 = result.x, result.y
            x2, y2 = result.x + result.width, result.y + result.height

            # Draw the rectangle outline (axis-aligned minimal bounding box)
            for i in range(self.BOX_WIDTH):
                draw.rectangle(
                    [x1 - i, y1 - i, x2 + i, y2 + i],
                    outline=self.BOX_COLOR,
                )

            # Confidence label
            label = f"Face {result.confidence:.0%}"
            label_x, label_y = x1, max(0, y1 - 22)

            # Label background
            draw.rectangle(
                [label_x, label_y, label_x + len(label) * 8 + 4, label_y + 20],
                fill=self.LABEL_BG,
            )
            draw.text((label_x + 2, label_y + 2), label, fill=self.LABEL_COLOR)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80)
        return buf.getvalue()

    def close(self) -> None:
        self._detector.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
