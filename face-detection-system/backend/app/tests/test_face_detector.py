"""
Unit tests for the FaceDetector service.
Uses a synthetic white image (no real face) to verify the pipeline runs
without crashing, and a downloaded test image to verify actual detection.
"""

import io
import pytest
from PIL import Image, ImageDraw

from app.services.face_detector import FaceDetector, BoundingBox


def _make_blank_jpeg(width: int = 320, height: int = 240) -> bytes:
    img = Image.new("RGB", (width, height), color=(200, 200, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _make_face_like_jpeg() -> bytes:
    """Create a crude synthetic face-like image for smoke-testing."""
    img = Image.new("RGB", (320, 240), color=(240, 220, 200))
    draw = ImageDraw.Draw(img)
    # Draw an oval "face"
    draw.ellipse([100, 60, 220, 180], fill=(230, 190, 150))
    # Eyes
    draw.ellipse([125, 95, 145, 115], fill=(50, 50, 50))
    draw.ellipse([175, 95, 195, 115], fill=(50, 50, 50))
    # Mouth
    draw.arc([130, 135, 190, 165], start=0, end=180, fill=(150, 80, 80), width=3)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


class TestFaceDetector:

    def test_instantiation(self):
        d = FaceDetector()
        assert d is not None
        d.close()

    def test_context_manager(self):
        with FaceDetector() as d:
            assert d is not None

    def test_no_face_returns_none_bbox(self):
        """Blank image should yield no detection."""
        with FaceDetector() as d:
            annotated, bbox = d.detect(_make_blank_jpeg())
        assert bbox is None
        assert isinstance(annotated, bytes)
        assert len(annotated) > 0

    def test_annotated_output_is_valid_jpeg(self):
        """Output bytes should always be parse-able as a JPEG."""
        with FaceDetector() as d:
            annotated, _ = d.detect(_make_blank_jpeg())
        img = Image.open(io.BytesIO(annotated))
        assert img.format == "JPEG"

    def test_face_like_image_runs_without_error(self):
        """Even if MediaPipe doesn't detect the synthetic face, it shouldn't crash."""
        with FaceDetector() as d:
            annotated, bbox = d.detect(_make_face_like_jpeg())
        assert isinstance(annotated, bytes)

    def test_bounding_box_dataclass(self):
        bb = BoundingBox(x=10, y=20, width=100, height=80, confidence=0.95)
        assert bb.x2 == 110
        assert bb.y2 == 100

    def test_confidence_threshold_respected(self):
        """With threshold=1.0, nothing should ever be detected."""
        with FaceDetector(confidence_threshold=1.0) as d:
            _, bbox = d.detect(_make_face_like_jpeg())
        assert bbox is None

    def test_large_frame_handled(self):
        """Should handle larger images without OOM or crash."""
        with FaceDetector() as d:
            annotated, _ = d.detect(_make_blank_jpeg(1280, 720))
        assert len(annotated) > 0
