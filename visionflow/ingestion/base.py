"""
Base source class for video stream ingestion.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class BaseSource(ABC):
    """
    Abstract base class for video stream sources.

    Implementations: RTSP, WebRTC, File, USB camera, etc.
    """

    def __init__(self, source_id: str, fps: int = 30) -> None:
        """
        Initialize the source.

        Args:
            source_id: Unique identifier for this source
            fps: Frames per second to capture
        """
        self.source_id = source_id
        self.fps = fps
        self.is_running = False
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def connect(self) -> None:
        """Connect to the source (open stream, file, etc.)."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the source."""
        pass

    @abstractmethod
    async def read_frame(self) -> Optional[np.ndarray]:
        """
        Read the next frame from the source.

        Returns:
            Frame as numpy array (BGR format) or None if stream ended
        """
        pass

    async def start(self) -> None:
        """Start the source."""
        if self.is_running:
            self._logger.warning(f"Source {self.source_id} already running")
            return

        try:
            await self.connect()
            self.is_running = True
            self._logger.info(f"Source {self.source_id} started")
        except Exception as e:
            self._logger.error(f"Error starting source {self.source_id}: {e}", exc_info=True)
            raise

    async def stop(self) -> None:
        """Stop the source."""
        if not self.is_running:
            return

        try:
            await self.disconnect()
            self.is_running = False
            self._logger.info(f"Source {self.source_id} stopped")
        except Exception as e:
            self._logger.error(f"Error stopping source {self.source_id}: {e}", exc_info=True)
            raise
