"""
YOLO object detection worker.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from visionflow.processing.base import BaseWorker

logger = logging.getLogger(__name__)


class YOLOWorker(BaseWorker):
    """
    YOLO object detection worker.

    Supports YOLOv8+ models from Ultralytics. Provides per-frame object detection
    with class names, confidence scores, and bounding boxes.

    Example::

        worker = YOLOWorker("detector", model_name="yolov8n.pt")
        await worker.start()
        results = await worker.process_frame(frame)
        await worker.stop()
    """

    def __init__(self, worker_id: str, model_name: str = "yolov8n.pt") -> None:
        """
        Initialize YOLO worker.

        Args:
            worker_id: Unique identifier for this worker
            model_name: Model filename or path (e.g., 'yolov8n.pt', 'yolov8m.pt')
        """
        super().__init__(worker_id=worker_id, model_name=model_name)
        self._model: Optional[Any] = None

    async def initialize(self) -> None:
        """Load YOLO model into memory."""
        try:
            from ultralytics import YOLO

            self._model = YOLO(self.model_name)
            self._logger.info(f"YOLO model loaded: {self.model_name}")
        except ImportError:
            raise ImportError(
                "ultralytics is required for YOLO support. "
                "Install with: pip install visionflow[yolo]"
            )
        except Exception as e:
            self._logger.error(f"Error loading YOLO model '{self.model_name}': {e}", exc_info=True)
            raise

    async def cleanup(self) -> None:
        """Unload model and free memory."""
        self._model = None
        self._logger.info(f"YOLO model unloaded: {self.model_name}")

    async def process_frame(self, frame: Any) -> Dict[str, Any]:
        """
        Run YOLO inference on a single frame.

        Args:
            frame: Input frame as numpy array (BGR format)

        Returns:
            Dictionary containing:
                - classes (list[str]): Detected class names
                - confidences (list[float]): Confidence scores in [0, 1]
                - boxes (list[list[float]]): Bounding boxes as [x1, y1, x2, y2]
                - count (int): Total number of detections

        Raises:
            RuntimeError: If model has not been initialized via start()
        """
        if self._model is None:
            raise RuntimeError(
                f"Worker '{self.worker_id}' is not initialized. Call start() first."
            )

        try:
            results = self._model(frame, verbose=False)
            detections: Dict[str, Any] = {
                "classes": [],
                "confidences": [],
                "boxes": [],
                "count": 0,
            }

            if results and len(results) > 0:
                result = results[0]
                if result.boxes is not None:
                    for box, conf, cls in zip(
                        result.boxes.xyxy, result.boxes.conf, result.boxes.cls
                    ):
                        class_name = self._model.names[int(cls)]
                        detections["classes"].append(class_name)
                        detections["confidences"].append(float(conf))
                        detections["boxes"].append(box.tolist())

                detections["count"] = len(detections["classes"])

            return detections

        except Exception as e:
            self._logger.error(f"Error during YOLO inference: {e}", exc_info=True)
            raise

    def __repr__(self) -> str:
        return (
            f"YOLOWorker(worker_id={self.worker_id!r}, "
            f"model_name={self.model_name!r}, "
            f"is_running={self.is_running})"
        )
