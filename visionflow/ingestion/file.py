"""
File-based video source using OpenCV.
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


class FileSource(BaseSource):
    """
    File-based video source using OpenCV.

    Supports MP4, AVI, MOV and other video formats.
    """

    def __init__(self, file_path: str, source_id: str | None = None, fps: int = 30) -> None:
        """
        Initialize file source.

        Args:
            file_path: Path to video file
            source_id: Unique identifier, defaults to file_path
            fps: Frames per second
        """
        self.file_path = file_path
        super().__init__(source_id or file_path, fps)
        self._cap: Optional[cv2.VideoCapture] = None
        self._frame_delay = 1.0 / fps

    async def connect(self) -> None:
        """Open video file."""
        self._cap = cv2.VideoCapture(self.file_path)

        if not self._cap.isOpened():
            raise RuntimeError(f"Failed to open video file: {self.file_path}")

        # Get actual FPS from file if available
        actual_fps = self._cap.get(cv2.CAP_PROP_FPS)
        if actual_fps > 0:
            self.fps = int(actual_fps)
            self._frame_delay = 1.0 / self.fps

        self._logger.info(f"Opened video file: {self.file_path} ({self.fps} FPS)")

    async def disconnect(self) -> None:
        """Close video file."""
        if self._cap is not None:
            self._cap.release()
            self._cap = None
            self._logger.info("Video file closed")

    async def read_frame(self) -> Optional[object]:
        """
        Read next frame from file.

        Returns:
            Frame as numpy array (BGR) or None if file ended
        """
        if self._cap is None or not self._cap.isOpened():
            self._logger.debug("VideoCapture not initialized or closed")
            return None

        ret, frame = self._cap.read()

        if not ret:
            self._logger.debug("End of video file reached or failed to read frame")
            return None

        # Control playback speed (sleep after reading, not before)
        await asyncio.sleep(self._frame_delay)

        return frame
