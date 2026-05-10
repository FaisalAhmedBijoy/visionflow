"""
RTSP stream source using OpenCV.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

import numpy as np

try:
    import cv2
except ImportError:
    raise ImportError(
        "opencv-python is required. Install with: pip install opencv-python"
    )

from visionflow.ingestion.base import BaseSource

logger = logging.getLogger(__name__)


class RTSPSource(BaseSource):
    """
    RTSP video stream source using OpenCV.

    Supports standard RTSP protocol URLs (``rtsp://``, ``rtsps://``).
    Automatically retries connection on stream failure up to
    ``max_retries`` times with exponential back-off.

    Example::

        source = RTSPSource(
            rtsp_url="rtsp://camera.local/stream",
            source_id="cam_entrance",
            fps=25,
            max_retries=5,
        )
        await source.start()
        frame = await source.read_frame()
        await source.stop()

    Args:
        rtsp_url: Full RTSP URL, e.g. ``rtsp://user:pass@host/stream``
        source_id: Unique identifier (defaults to the URL)
        fps: Target frames per second
        max_retries: Max reconnection attempts before giving up (0 = unlimited)
        retry_delay: Initial seconds to wait before first retry (doubles each attempt)
    """

    def __init__(
        self,
        rtsp_url: str,
        source_id: Optional[str] = None,
        fps: int = 30,
        max_retries: int = 5,
        retry_delay: float = 1.0,
    ) -> None:
        self.rtsp_url = rtsp_url
        super().__init__(source_id or rtsp_url, fps)
        self._cap: Optional[cv2.VideoCapture] = None
        self._frame_delay = 1.0 / max(fps, 1)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._retry_count = 0

    async def connect(self) -> None:
        """Open RTSP stream and configure OpenCV capture."""
        self._cap = cv2.VideoCapture(self.rtsp_url)

        if not self._cap.isOpened():
            raise RuntimeError(f"Failed to open RTSP stream: {self.rtsp_url}")

        # Minimize buffer latency for real-time processing
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self._retry_count = 0
        self._logger.info(f"Connected to RTSP stream: {self.rtsp_url}")

    async def disconnect(self) -> None:
        """Release the OpenCV capture device."""
        if self._cap is not None:
            self._cap.release()
            self._cap = None
            self._logger.info(f"RTSP stream disconnected: {self.rtsp_url}")

    async def read_frame(self) -> Optional[np.ndarray]:
        """
        Read the next frame from the RTSP stream.

        Automatically attempts reconnection if the stream drops, up to
        ``max_retries`` times. Returns ``None`` if the stream cannot be
        recovered.

        Returns:
            Frame as a numpy array in BGR format, or ``None`` if exhausted.
        """
        if self._cap is None or not self._cap.isOpened():
            return await self._attempt_reconnect()

        ret, frame = self._cap.read()

        if not ret:
            self._logger.warning(
                f"Failed to read frame from RTSP stream: {self.rtsp_url}"
            )
            return await self._attempt_reconnect()

        # Frame-rate throttle
        await asyncio.sleep(self._frame_delay)
        return frame

    async def _attempt_reconnect(self) -> Optional[np.ndarray]:
        """
        Attempt to reconnect to the RTSP stream with exponential back-off.

        Returns:
            First recovered frame, or ``None`` if max_retries is exhausted.
        """
        while self.max_retries == 0 or self._retry_count < self.max_retries:
            self._retry_count += 1
            delay = self.retry_delay * (2 ** (self._retry_count - 1))
            self._logger.warning(
                f"RTSP reconnect attempt {self._retry_count}"
                f"{'/' + str(self.max_retries) if self.max_retries else ''} "
                f"in {delay:.1f}s …"
            )
            await asyncio.sleep(delay)

            try:
                if self._cap is not None:
                    self._cap.release()
                self._cap = cv2.VideoCapture(self.rtsp_url)
                if self._cap.isOpened():
                    self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    self._retry_count = 0
                    self._logger.info(f"RTSP stream reconnected: {self.rtsp_url}")
                    ret, frame = self._cap.read()
                    if ret:
                        return frame
            except Exception as e:
                self._logger.error(f"RTSP reconnect error: {e}")

        self._logger.error(
            f"RTSP stream exhausted {self.max_retries} reconnection attempts: {self.rtsp_url}"
        )
        return None

    def __repr__(self) -> str:
        return (
            f"RTSPSource(source_id={self.source_id!r}, "
            f"rtsp_url={self.rtsp_url!r}, "
            f"fps={self.fps}, is_running={self.is_running})"
        )
