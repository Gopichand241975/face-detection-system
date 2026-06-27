"""
Face detection service using MediaPipe (no OpenCV).

MediaPipe's FaceDetection model returns bounding boxes as normalised
[0, 1] relative coordinates.  We convert those to absolute pixel coords
and build an axis-aligned minimal bounding box (AABB / ROI).

Drawing is done with Pillow – OpenCV is NOT imported anywhere in this file.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from typing import Optional

import mediapipe as mp
import numpy as np
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)

_mp_face = mp.solutions.face_detection


@dataclass
class BoundingBox:
    """Axis-aligned minimal bounding box in absolute pixel coordinates."""
    x: float       # left
    y: float       # top
    width: float
    height: float
    confidence: float

    @property
    def x2(self) -> float:
        return self.x + self.width

    @property
    def y2(self) -> float:
        return self.y + self.height


class FaceDetector:
    """
    Wraps MediaPipe FaceDetection.
    Thread-local usage: instantiate once per worker/process.
    """

    def __init__(self, confidence_threshold: float = 0.5):
        self._detector = _mp_face.FaceDetection(
            model_selection=1,               # 1 = full-range model (up to 5 m)
            min_detection_confidence=confidence_threshold,
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def detect(self, frame_bytes: bytes) -> tuple[bytes, Optional[BoundingBox]]:
        """
        Detect the (single) face in *frame_bytes* (JPEG/PNG image data).

        Returns
        -------
        annotated_jpeg : bytes
            JPEG image with a white bounding-box rectangle drawn by Pillow.
        bbox : BoundingBox or None
            The detected face ROI, or None if no face was found.
        """
        pil_image = Image.open(io.BytesIO(frame_bytes)).convert("RGB")
        bbox = self._run_detection(pil_image)

        if bbox is not None:
            pil_image = self._draw_roi(pil_image, bbox)

        buf = io.BytesIO()
        pil_image.save(buf, format="JPEG", quality=85)
        return buf.getvalue(), bbox

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _run_detection(self, pil_image: Image.Image) -> Optional[BoundingBox]:
        """Convert PIL → numpy, run MediaPipe, return first detection."""
        rgb_array = np.array(pil_image)          # H×W×3  uint8  RGB
        h, w = rgb_array.shape[:2]

        result = self._detector.process(rgb_array)

        if not result.detections:
            return None

        # Take the highest-confidence detection (task says only one face)
        detection = max(result.detections, key=lambda d: d.score[0])
        rel_bb = detection.location_data.relative_bounding_box
        score = float(detection.score[0])

        # Convert normalised → absolute pixel coords
        x = max(0.0, rel_bb.xmin * w)
        y = max(0.0, rel_bb.ymin * h)
        bw = min(rel_bb.width * w, w - x)
        bh = min(rel_bb.height * h, h - y)

        return BoundingBox(x=x, y=y, width=bw, height=bh, confidence=score)

    @staticmethod
    def _draw_roi(image: Image.Image, bbox: BoundingBox) -> Image.Image:
        """
        Draw an axis-aligned minimal bounding box using Pillow (no OpenCV).
        Colour: bright green (#00FF41) with a 2-pixel border.
        """
        draw = ImageDraw.Draw(image)
        draw.rectangle(
            [bbox.x, bbox.y, bbox.x2, bbox.y2],
            outline="#00FF41",
            width=3,
        )
        # Confidence label above the box
        label = f"{bbox.confidence * 100:.1f}%"
        draw.text((bbox.x + 4, max(0, bbox.y - 18)), label, fill="#00FF41")
        return image

    def close(self):
        self._detector.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
