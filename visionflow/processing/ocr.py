"""
OCR text recognition worker.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from visionflow.processing.base import BaseWorker

logger = logging.getLogger(__name__)


class OCRWorker(BaseWorker):
    """
    OCR (Optical Character Recognition) worker.

    Uses Tesseract or similar OCR engine.
    """

    def __init__(self, worker_id: str, engine: str = "tesseract") -> None:
        """
        Initialize OCR worker.

        Args:
            worker_id: Unique identifier
            engine: OCR engine ('tesseract' or others)
        """
        self.worker_id = worker_id
        self.engine = engine
        self.is_running = False
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def initialize(self) -> None:
        """Initialize OCR engine."""
        if self.engine == "tesseract":
            try:
                import pytesseract
                from PIL import Image

                self._pytesseract = pytesseract
                self._image = Image
                self._logger.info("Tesseract OCR initialized")
            except ImportError:
                raise ImportError(
                    "pytesseract and pillow are required. "
                    "Install with: pip install pytesseract pillow"
                )
        else:
            raise ValueError(f"Unsupported OCR engine: {self.engine}")

    async def cleanup(self) -> None:
        """Clean up OCR engine."""
        self._logger.info("OCR engine cleaned up")

    async def process_frame(self, frame: Any) -> Dict[str, Any]:
        """
        Extract text from frame using OCR.

        Args:
            frame: Input frame (numpy array)

        Returns:
            OCR results with detected text
        """
        if self.engine == "tesseract":
            try:
                # Convert BGR to RGB for PIL
                import cv2

                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_image = self._image.fromarray(rgb_frame)

                # Run OCR
                text = self._pytesseract.image_to_string(pil_image)
                data = self._pytesseract.image_to_data(pil_image, output_type="dict")

                return {
                    "text": text,
                    "confidence": 0.0,  # Tesseract doesn't provide confidence
                    "boxes": [
                        [x, y, x + w, y + h]
                        for x, y, w, h in zip(
                            data["left"], data["top"], data["width"], data["height"]
                        )
                    ],
                }
            except Exception as e:
                self._logger.error(f"Error during OCR: {e}", exc_info=True)
                raise
        else:
            raise ValueError(f"Unsupported OCR engine: {self.engine}")

    async def start(self) -> None:
        """Start the worker."""
        if self.is_running:
            return
        await self.initialize()
        self.is_running = True

    async def stop(self) -> None:
        """Stop the worker."""
        if not self.is_running:
            return
        await self.cleanup()
        self.is_running = False
