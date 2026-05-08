"""Unit tests for FaceDetectionService (no DB, no HTTP)."""

import io
import numpy as np
import pytest
from PIL import Image

from app.services.face_detection import FaceDetectionService, DetectionResult


class TestDetectionResult:
    def test_default_no_face(self):
        r = DetectionResult(face_detected=False)
        assert r.face_detected is False
        assert r.x is None
        assert r.confidence is None

    def test_with_face(self):
        r = DetectionResult(face_detected=True, x=10, y=20, width=50, height=60, confidence=0.95)
        assert r.face_detected is True
        assert r.x == 10
        assert r.width == 50


class TestFaceDetectionService:
    @pytest.fixture
    def svc(self):
        s = FaceDetectionService(min_detection_confidence=0.5)
        yield s
        s.close()

    def test_detect_blank_frame_no_face(self, svc):
        """A blank black frame should yield no detection."""
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        result = svc.detect(frame)
        assert result.face_detected is False
        assert result.x is None

    def test_draw_roi_no_face_returns_jpeg(self, svc):
        """draw_roi should always return valid JPEG bytes."""
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        result = DetectionResult(face_detected=False)
        jpeg = svc.draw_roi(frame, result)
        assert isinstance(jpeg, bytes)
        assert len(jpeg) > 0
        # Verify it is actually a JPEG
        img = Image.open(io.BytesIO(jpeg))
        assert img.format == "JPEG"

    def test_draw_roi_with_face_renders_box(self, svc):
        """draw_roi with a face result should produce a different image (box drawn)."""
        frame = np.full((240, 320, 3), 128, dtype=np.uint8)
        no_face_jpeg = svc.draw_roi(frame, DetectionResult(face_detected=False))

        result = DetectionResult(
            face_detected=True, x=50, y=50, width=100, height=100, confidence=0.9
        )
        face_jpeg = svc.draw_roi(frame, result)

        # Files should differ (box pixels change the output)
        assert no_face_jpeg != face_jpeg

    def test_draw_roi_bounding_box_clamps(self, svc):
        """Bounding box near/at frame edge should not raise."""
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        result = DetectionResult(
            face_detected=True, x=0, y=0, width=100, height=100, confidence=0.8
        )
        jpeg = svc.draw_roi(frame, result)
        assert isinstance(jpeg, bytes)

    def test_context_manager(self):
        with FaceDetectionService() as svc:
            frame = np.zeros((100, 100, 3), dtype=np.uint8)
            r = svc.detect(frame)
            assert isinstance(r, DetectionResult)


class TestJpegDecode:
    """Test the JPEG→RGB helper (imported from video route)."""

    def test_jpeg_roundtrip(self):
        from app.api.routes.video import _jpeg_to_rgb
        frame = np.full((120, 160, 3), 200, dtype=np.uint8)
        buf = io.BytesIO()
        Image.fromarray(frame).save(buf, format="JPEG", quality=95)
        decoded = _jpeg_to_rgb(buf.getvalue())
        assert decoded.shape == (120, 160, 3)

    def test_invalid_bytes_raises(self):
        from app.api.routes.video import _jpeg_to_rgb
        with pytest.raises(Exception):
            _jpeg_to_rgb(b"not a jpeg")
