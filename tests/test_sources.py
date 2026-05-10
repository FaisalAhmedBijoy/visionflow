"""
Tests for VisionFlow video source ingestion.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from visionflow.ingestion.base import BaseSource
from visionflow.ingestion.file import FileSource
from visionflow.ingestion.webcam import WebcamSource


# ------------------------------------------------------------------ #
# Concrete stub for BaseSource (abstract class)
# ------------------------------------------------------------------ #

class _StubSource(BaseSource):
    """Minimal concrete implementation of BaseSource for testing."""

    def __init__(self, source_id: str = "stub", fps: int = 30) -> None:
        super().__init__(source_id, fps)
        self.connected = False

    async def connect(self) -> None:
        self.connected = True

    async def disconnect(self) -> None:
        self.connected = False

    async def read_frame(self) -> Optional[np.ndarray]:
        return np.zeros((480, 640, 3), dtype=np.uint8)


# ------------------------------------------------------------------ #
# BaseSource tests
# ------------------------------------------------------------------ #

class TestBaseSource:
    """Tests for the BaseSource lifecycle."""

    def test_initial_state(self) -> None:
        source = _StubSource("cam1", fps=25)
        assert source.source_id == "cam1"
        assert source.fps == 25
        assert source.is_running is False

    @pytest.mark.asyncio
    async def test_start_calls_connect(self) -> None:
        source = _StubSource("cam1")
        await source.start()
        assert source.connected is True
        assert source.is_running is True

    @pytest.mark.asyncio
    async def test_stop_calls_disconnect(self) -> None:
        source = _StubSource("cam1")
        await source.start()
        await source.stop()
        assert source.connected is False
        assert source.is_running is False

    @pytest.mark.asyncio
    async def test_double_start_is_idempotent(self) -> None:
        source = _StubSource("cam1")
        await source.start()
        await source.start()  # Should not raise
        assert source.is_running is True

    @pytest.mark.asyncio
    async def test_stop_when_not_running_is_safe(self) -> None:
        source = _StubSource("cam1")
        await source.stop()  # Should not raise

    def test_repr(self) -> None:
        source = _StubSource("cam1", fps=25)
        r = repr(source)
        assert "cam1" in r
        assert "25" in r


# ------------------------------------------------------------------ #
# FileSource tests
# ------------------------------------------------------------------ #

class TestFileSource:
    """Tests for FileSource using a mocked OpenCV VideoCapture."""

    def _make_mock_cap(
        self,
        is_opened: bool = True,
        fps: float = 30.0,
        frame: Optional[np.ndarray] = None,
        read_success: bool = True,
    ) -> MagicMock:
        cap = MagicMock()
        cap.isOpened.return_value = is_opened
        cap.get.return_value = fps
        cap.read.return_value = (read_success, frame if frame is not None else np.zeros((480, 640, 3), dtype=np.uint8))
        return cap

    def test_default_source_id_is_file_path(self) -> None:
        src = FileSource("video.mp4")
        assert src.source_id == "video.mp4"

    def test_custom_source_id(self) -> None:
        src = FileSource("video.mp4", source_id="my_cam")
        assert src.source_id == "my_cam"

    @pytest.mark.asyncio
    async def test_connect_sets_fps_from_file(self) -> None:
        src = FileSource("video.mp4", source_id="v", fps=1)
        mock_cap = self._make_mock_cap(fps=60.0)
        with patch("cv2.VideoCapture", return_value=mock_cap):
            await src.connect()
        assert src.fps == 60

    @pytest.mark.asyncio
    async def test_connect_fails_if_file_not_opened(self) -> None:
        src = FileSource("nonexistent.mp4")
        mock_cap = self._make_mock_cap(is_opened=False)
        with patch("cv2.VideoCapture", return_value=mock_cap):
            with pytest.raises(RuntimeError, match="Failed to open video file"):
                await src.connect()

    @pytest.mark.asyncio
    async def test_read_frame_returns_ndarray(self) -> None:
        src = FileSource("video.mp4", source_id="v")
        frame_data = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_cap = self._make_mock_cap(frame=frame_data)
        with patch("cv2.VideoCapture", return_value=mock_cap):
            await src.connect()
            frame = await src.read_frame()
        assert frame is not None
        assert isinstance(frame, np.ndarray)

    @pytest.mark.asyncio
    async def test_read_frame_returns_none_at_eof(self) -> None:
        src = FileSource("video.mp4", source_id="v")
        mock_cap = self._make_mock_cap(read_success=False)
        with patch("cv2.VideoCapture", return_value=mock_cap):
            await src.connect()
            frame = await src.read_frame()
        assert frame is None

    @pytest.mark.asyncio
    async def test_disconnect_releases_capture(self) -> None:
        src = FileSource("video.mp4", source_id="v")
        mock_cap = self._make_mock_cap()
        with patch("cv2.VideoCapture", return_value=mock_cap):
            await src.connect()
            await src.disconnect()
        mock_cap.release.assert_called_once()

    def test_repr(self) -> None:
        src = FileSource("video.mp4", source_id="v")
        r = repr(src)
        assert "video.mp4" in r or "v" in r


# ------------------------------------------------------------------ #
# WebcamSource tests
# ------------------------------------------------------------------ #

class TestWebcamSource:
    """Tests for WebcamSource using a mocked VideoCapture."""

    def _make_mock_cap(
        self,
        is_opened: bool = True,
        fps: float = 30.0,
        read_success: bool = True,
    ) -> MagicMock:
        cap = MagicMock()
        cap.isOpened.return_value = is_opened
        cap.get.return_value = fps
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cap.read.return_value = (read_success, frame)
        return cap

    def test_default_source_id(self) -> None:
        src = WebcamSource(device_index=0)
        assert src.source_id == "webcam_0"

    def test_custom_source_id(self) -> None:
        src = WebcamSource(device_index=1, source_id="front_cam")
        assert src.source_id == "front_cam"

    @pytest.mark.asyncio
    async def test_connect_succeeds(self) -> None:
        src = WebcamSource(device_index=0, source_id="wc")
        mock_cap = self._make_mock_cap()
        with patch("cv2.VideoCapture", return_value=mock_cap):
            await src.connect()
        assert src._cap is not None

    @pytest.mark.asyncio
    async def test_connect_fails_if_not_opened(self) -> None:
        src = WebcamSource(device_index=99, source_id="wc")
        mock_cap = self._make_mock_cap(is_opened=False)
        with patch("cv2.VideoCapture", return_value=mock_cap):
            with pytest.raises(RuntimeError, match="Failed to open webcam"):
                await src.connect()

    @pytest.mark.asyncio
    async def test_read_frame_returns_ndarray(self) -> None:
        src = WebcamSource(device_index=0, source_id="wc")
        mock_cap = self._make_mock_cap()
        with patch("cv2.VideoCapture", return_value=mock_cap):
            await src.connect()
            frame = await src.read_frame()
        assert frame is not None
        assert isinstance(frame, np.ndarray)

    @pytest.mark.asyncio
    async def test_read_frame_returns_none_on_failure(self) -> None:
        src = WebcamSource(device_index=0, source_id="wc")
        mock_cap = self._make_mock_cap(read_success=False)
        with patch("cv2.VideoCapture", return_value=mock_cap):
            await src.connect()
            frame = await src.read_frame()
        assert frame is None

    def test_repr(self) -> None:
        src = WebcamSource(device_index=2, source_id="cam")
        assert "cam" in repr(src)
        assert "2" in repr(src)
