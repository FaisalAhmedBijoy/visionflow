"""
RTSP source implementation using OpenCV.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

try:
    import cv2
except ImportError:
    raise ImportError("opencv-python is required. Install with: pip install opencv-python")

from visionflow.ingestion.base import BaseSource

logger = logging.getLogger(__name__)


class RTSPSource(BaseSource):
    """
    RTSP stream source using OpenCV.

    Supports standard RTSP protocol (rtsp://, rtsps://).
    """

    def __init__(self, rtsp_url: str, source_id: str | None = None, fps: int = 30) -> None:
        """
        Initialize RTSP source.

        Args:
            rtsp_url: RTSP URL (e.g., rtsp://camera.local/stream)
            source_id: Unique identifier, defaults to rtsp_url
            fps: Frames per second
        """
        self.rtsp_url = rtsp_url
        super().__init__(source_id or rtsp_url, fps)
        self._cap: Optional[cv2.VideoCapture] = None
        self._frame_delay = 1.0 / fps

    async def connect(self) -> None:
        """Connect to RTSP stream."""
        self._cap = cv2.VideoCapture(self.rtsp_url)

        if not self._cap.isOpened():
            raise RuntimeError(f"Failed to open RTSP stream: {self.rtsp_url}")

        # Set buffer size to reduce latency
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self._logger.info(f"Connected to RTSP stream: {self.rtsp_url}")

    async def disconnect(self) -> None:
        """Disconnect from RTSP stream."""
        if self._cap is not None:
            self._cap.release()
            self._cap = None
            self._logger.info("RTSP stream disconnected")

    async def read_frame(self) -> Optional[object]:
        """
        Read next frame from RTSP stream.

        Returns:
            Frame as numpy array (BGR) or None if stream ended
        """
        if self._cap is None or not self._cap.isOpened():
            return None

        ret, frame = self._cap.read()

        if not ret:
            self._logger.warning("RTSP stream ended or read error")
            return None

        # Non-blocking read with frame rate control
        await asyncio.sleep(self._frame_delay)

        return frame
