"""
Shared pytest fixtures for VisionFlow tests.
"""

from __future__ import annotations

import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from visionflow.core.pipeline import StreamPipeline
from visionflow.events.engine import EventEngine
from visionflow.events.event import Event
from visionflow.outputs.log import LogOutput
from visionflow.processing.middleware import ConfidenceFilter, EventMiddleware
from visionflow.utils.metrics import PipelineMetrics


@pytest.fixture
def sample_event() -> Event:
    """A minimal valid Event for use in tests."""
    return Event(
        event_type="person_detected",
        source_id="test_camera",
        data={"class": "person", "confidence": 0.92, "box": [10, 20, 50, 80]},
        metadata={"frame_id": 42},
    )


@pytest.fixture
def low_confidence_event() -> Event:
    """An event with confidence below typical thresholds."""
    return Event(
        event_type="object_detected",
        source_id="test_camera",
        data={"class": "unknown", "confidence": 0.1},
    )


@pytest.fixture
def event_engine() -> EventEngine:
    """A fresh EventEngine instance."""
    return EventEngine()


@pytest.fixture
def pipeline() -> StreamPipeline:
    """A fresh StreamPipeline instance with no sources or outputs."""
    return StreamPipeline(name="test_pipeline")


@pytest.fixture
def log_output() -> LogOutput:
    """A LogOutput instance."""
    return LogOutput(output_id="test_log")


@pytest.fixture
def middleware() -> EventMiddleware:
    """A fresh EventMiddleware chain."""
    return EventMiddleware()


@pytest.fixture
def confidence_filter() -> ConfidenceFilter:
    """A ConfidenceFilter with 50% threshold."""
    return ConfidenceFilter(min_confidence=0.5)


@pytest.fixture
def metrics() -> PipelineMetrics:
    """A fresh PipelineMetrics instance."""
    m = PipelineMetrics()
    m.start()
    return m


@pytest.fixture
def black_frame() -> np.ndarray:
    """A 480x640 black BGR frame for use in processing tests."""
    return np.zeros((480, 640, 3), dtype=np.uint8)


@pytest.fixture
def mock_yolo_worker() -> MagicMock:
    """A mock YOLOWorker that returns synthetic detections."""
    worker = MagicMock()
    worker.worker_id = "mock_yolo"
    worker.model_name = "yolov8n.pt"
    worker.is_running = True
    worker.start = AsyncMock()
    worker.stop = AsyncMock()
    worker.process_frame = AsyncMock(
        return_value={
            "classes": ["person", "car"],
            "confidences": [0.92, 0.85],
            "boxes": [[10, 20, 50, 80], [100, 100, 200, 200]],
            "count": 2,
        }
    )
    return worker
