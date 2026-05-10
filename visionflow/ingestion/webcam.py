"""
USB/built-in webcam source using OpenCV.
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


class WebcamSource(BaseSource):
    """
    USB or built-in webcam source using OpenCV.

    Captures frames from a local camera device. Supports any camera accessible
    via ``cv2.VideoCapture(device_index)``.

    Example::

        # Default camera (index 0)
        source = WebcamSource(device_index=0, source_id="webcam_main", fps=30)

        # Specific resolution
        source = WebcamSource(
            device_index=0,
            source_id="webcam_hd",
            fps=30,
            width=1920,
            height=1080,
        )

        await source.start()
        frame = await source.read_frame()
        await source.stop()

    Args:
        device_index: OpenCV device index (default 0 = first camera)
        source_id: Unique identifier (defaults to ``"webcam_{device_index}"``)
        fps: Target capture frame rate
        width: Requested frame width in pixels (0 = use device default)
        height: Requested frame height in pixels (0 = use device default)
    """

    def __init__(
        self,
        device_index: int = 0,
        source_id: Optional[str] = None,
        fps: int = 30,
        width: int = 0,
        height: int = 0,
    ) -> None:
        self.device_index = device_index
        self.width = width
        self.height = height
        super().__init__(source_id or f"webcam_{device_index}", fps)
        self._cap: Optional[cv2.VideoCapture] = None
        self._frame_delay = 1.0 / max(fps, 1)

    async def connect(self) -> None:
        """Open the webcam device."""
        self._cap = cv2.VideoCapture(self.device_index)

        if not self._cap.isOpened():
            raise RuntimeError(
                f"Failed to open webcam device {self.device_index}. "
                "Make sure the camera is connected and not in use by another process."
            )

        # Apply resolution if requested
        if self.width > 0:
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        if self.height > 0:
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

        # Apply requested FPS
        self._cap.set(cv2.CAP_PROP_FPS, self.fps)

        # Read back actual values
        actual_w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self._cap.get(cv2.CAP_PROP_FPS)
        if actual_fps > 0:
            self.fps = int(actual_fps)
            self._frame_delay = 1.0 / self.fps

        self._logger.info(
            f"Webcam opened: device={self.device_index}, "
            f"resolution={actual_w}x{actual_h}, fps={self.fps}"
        )

    async def disconnect(self) -> None:
        """Release the webcam device."""
        if self._cap is not None:
            self._cap.release()
            self._cap = None
            self._logger.info(f"Webcam {self.device_index} released")

    async def read_frame(self) -> Optional[np.ndarray]:
        """
        Capture the next frame from the webcam.

        Returns:
            Frame as a numpy array in BGR format, or ``None`` if capture failed.
        """
        if self._cap is None or not self._cap.isOpened():
            self._logger.warning("Webcam is not open")
            return None

        ret, frame = self._cap.read()
        if not ret:
            self._logger.warning(f"Failed to capture frame from webcam {self.device_index}")
            return None

        await asyncio.sleep(self._frame_delay)
        return frame

    def __repr__(self) -> str:
        return (
            f"WebcamSource(source_id={self.source_id!r}, "
            f"device_index={self.device_index}, "
            f"fps={self.fps}, is_running={self.is_running})"
        )
