"""
Base worker class for frame processing.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    import numpy as np

logger = logging.getLogger(__name__)


class BaseWorker(ABC):
    """
    Abstract base class for frame processing workers.

    Implementations: YOLO, OCR, custom ML models, etc.
    """

    def __init__(self, worker_id: str, model_name: str) -> None:
        """
        Initialize the worker.

        Args:
            worker_id: Unique identifier for this worker
            model_name: Name of the model being used
        """
        self.worker_id = worker_id
        self.model_name = model_name
        self.is_running = False
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize and load the model."""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up resources (unload model, etc.)."""
        pass

    @abstractmethod
    async def process_frame(self, frame: Any) -> Dict[str, Any]:
        """
        Process a frame with the model.

        Args:
            frame: Input frame (numpy array)

        Returns:
            Dictionary with inference results
        """
        pass

    async def start(self) -> None:
        """Start the worker."""
        if self.is_running:
            self._logger.warning(f"Worker {self.worker_id} already running")
            return

        try:
            await self.initialize()
            self.is_running = True
            self._logger.info(f"Worker {self.worker_id} started (model: {self.model_name})")
        except Exception as e:
            self._logger.error(f"Error starting worker {self.worker_id}: {e}", exc_info=True)
            raise

    async def stop(self) -> None:
        """Stop the worker."""
        if not self.is_running:
            return

        try:
            await self.cleanup()
            self.is_running = False
            self._logger.info(f"Worker {self.worker_id} stopped")
        except Exception as e:
            self._logger.error(f"Error stopping worker {self.worker_id}: {e}", exc_info=True)
            raise
