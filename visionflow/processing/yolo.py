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

    Supports YOLOv8 models from Ultralytics.
    """

    def __init__(self, worker_id: str, model_name: str = "yolov8n.pt") -> None:
        """
        Initialize YOLO worker.

        Args:
            worker_id: Unique identifier
            model_name: Model name (e.g., 'yolov8n.pt', 'yolov8m.pt')
        """
        self.worker_id = worker_id
        self.model_name = model_name
        self.is_running = False
        self._model: Optional[Any] = None
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def initialize(self) -> None:
        """Load YOLO model."""
        try:
            from ultralytics import YOLO

            self._model = YOLO(self.model_name)
            self._logger.info(f"YOLO model loaded: {self.model_name}")
        except ImportError:
            raise ImportError(
                "ultralytics is required. Install with: pip install ultralytics"
            )
        except Exception as e:
            self._logger.error(f"Error loading YOLO model: {e}", exc_info=True)
            raise

    async def cleanup(self) -> None:
        """Clean up model."""
        self._model = None
        self._logger.info("YOLO model unloaded")

    async def process_frame(self, frame: Any) -> Dict[str, Any]:
        """
        Run inference on frame.

        Args:
            frame: Input frame (numpy array)

        Returns:
            Detection results
        """
        if self._model is None:
            raise RuntimeError("Model not initialized")

        try:
            # Run inference
            results = self._model(frame, verbose=False)

            if len(results) > 0:
                result = results[0]
                detections = {
                    "classes": [],
                    "confidences": [],
                    "boxes": [],
                }

                # Extract detections
                if result.boxes is not None:
                    for box, conf, cls in zip(
                        result.boxes.xyxy, result.boxes.conf, result.boxes.cls
                    ):
                        class_name = self._model.names[int(cls)]
                        detections["classes"].append(class_name)
                        detections["confidences"].append(float(conf))
                        detections["boxes"].append(box.tolist())

                return detections
            else:
                return {"classes": [], "confidences": [], "boxes": []}

        except Exception as e:
            self._logger.error(f"Error during inference: {e}", exc_info=True)
            raise

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
