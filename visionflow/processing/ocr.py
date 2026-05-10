"""
OCR (Optical Character Recognition) worker.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from visionflow.processing.base import BaseWorker

logger = logging.getLogger(__name__)


class OCRWorker(BaseWorker):
    """
    OCR (Optical Character Recognition) worker.

    Extracts text from video frames using Tesseract or other OCR engines.
    Provides detected text, per-word confidence scores, and bounding boxes.

    Example::

        worker = OCRWorker("text_reader", engine="tesseract")
        await worker.start()
        results = await worker.process_frame(frame)
        await worker.stop()
    """

    def __init__(self, worker_id: str, engine: str = "tesseract") -> None:
        """
        Initialize OCR worker.

        Args:
            worker_id: Unique identifier for this worker
            engine: OCR engine to use. Currently supported: 'tesseract'
        """
        super().__init__(worker_id=worker_id, model_name=engine)
        self.engine = engine
        self._pytesseract: Optional[Any] = None
        self._image: Optional[Any] = None

    async def initialize(self) -> None:
        """Initialize the OCR engine and verify dependencies."""
        if self.engine == "tesseract":
            try:
                import pytesseract
                from PIL import Image

                self._pytesseract = pytesseract
                self._image = Image
                self._logger.info("Tesseract OCR initialized")
            except ImportError:
                raise ImportError(
                    "pytesseract and pillow are required for OCR support. "
                    "Install with: pip install visionflow[ocr]"
                )
        else:
            raise ValueError(
                f"Unsupported OCR engine: '{self.engine}'. Supported engines: ['tesseract']"
            )

    async def cleanup(self) -> None:
        """Release OCR engine resources."""
        self._pytesseract = None
        self._image = None
        self._logger.info("OCR engine cleaned up")

    async def process_frame(self, frame: Any) -> Dict[str, Any]:
        """
        Extract text from a frame using OCR.

        Args:
            frame: Input frame as numpy array (BGR format)

        Returns:
            Dictionary containing:
                - text (str): Full extracted text (newline-separated)
                - confidence (float): Mean word confidence in [0, 100]
                - boxes (list[list[int]]): Word bounding boxes as [x1, y1, x2, y2]
                - words (list[str]): Individual recognized words
                - word_confidences (list[float]): Per-word confidence scores

        Raises:
            RuntimeError: If worker has not been initialized via start()
        """
        if self._pytesseract is None or self._image is None:
            raise RuntimeError(
                f"Worker '{self.worker_id}' is not initialized. Call start() first."
            )

        if self.engine == "tesseract":
            try:
                import cv2

                # Convert BGR (OpenCV) → RGB (PIL)
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_image = self._image.fromarray(rgb_frame)

                # Full text extraction
                text: str = self._pytesseract.image_to_string(pil_image)

                # Per-word data with confidence scores
                data: Dict[str, List[Any]] = self._pytesseract.image_to_data(
                    pil_image, output_type="dict"
                )

                words: List[str] = []
                word_confidences: List[float] = []
                boxes: List[List[int]] = []

                for i, word_text in enumerate(data["text"]):
                    conf = data["conf"][i]
                    # Tesseract returns -1 for non-text regions
                    if conf >= 0 and str(word_text).strip():
                        x = int(data["left"][i])
                        y = int(data["top"][i])
                        w = int(data["width"][i])
                        h = int(data["height"][i])
                        words.append(str(word_text))
                        word_confidences.append(float(conf))
                        boxes.append([x, y, x + w, y + h])

                # Compute mean confidence across recognized words
                mean_confidence = (
                    sum(word_confidences) / len(word_confidences) if word_confidences else 0.0
                )

                return {
                    "text": text.strip(),
                    "confidence": round(mean_confidence, 2),
                    "boxes": boxes,
                    "words": words,
                    "word_confidences": word_confidences,
                }
            except Exception as e:
                self._logger.error(f"Error during OCR inference: {e}", exc_info=True)
                raise
        else:
            raise ValueError(f"Unsupported OCR engine: '{self.engine}'")

    def __repr__(self) -> str:
        return (
            f"OCRWorker(worker_id={self.worker_id!r}, "
            f"engine={self.engine!r}, "
            f"is_running={self.is_running})"
        )
