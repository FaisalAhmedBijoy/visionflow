"""
VisionFlow: Event-driven, real-time AI video stream processing framework.

A production-ready Python package for ingesting video streams,
processing frames using AI models, and distributing events via
multiple output channels.

Quick start::

    from visionflow import StreamPipeline, Event
    from visionflow.ingestion import FileSource, RTSPSource
    from visionflow.processing.yolo import YOLOWorker
    from visionflow.processing.pool import WorkerPool
    from visionflow.outputs.log import LogOutput

    async def main():
        async with StreamPipeline(name="My Pipeline") as pipeline:
            pipeline.add_source(FileSource("video.mp4"))
            pipeline.worker_pool = WorkerPool([YOLOWorker("det")])
            pipeline.add_output(LogOutput())

            @pipeline.on_event("person_detected")
            async def handler(event):
                print(event)

            await pipeline.run()
"""

__version__ = "0.2.0"
__author__ = "VisionFlow Contributors"
__license__ = "Apache-2.0"

from visionflow.core.pipeline import StreamPipeline
from visionflow.events.event import Event
from visionflow.events.engine import EventEngine
from visionflow.events.generator import EventGenerator
from visionflow.processing.middleware import ConfidenceFilter, EventMiddleware
from visionflow.utils.metrics import PipelineMetrics

__all__ = [
    # Core
    "StreamPipeline",
    # Events
    "Event",
    "EventEngine",
    "EventGenerator",
    # Processing
    "ConfidenceFilter",
    "EventMiddleware",
    # Metrics
    "PipelineMetrics",
    # Version
    "__version__",
]
