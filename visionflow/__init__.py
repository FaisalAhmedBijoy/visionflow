"""
VisionFlow: Event-driven, real-time AI video stream processing framework.

A production-ready Python package for ingesting video streams,
processing frames using AI models, and distributing events via
multiple output channels.
"""

__version__ = "0.1.0"
__author__ = "VisionFlow Contributors"
__license__ = "Apache-2.0"

from visionflow.core.pipeline import StreamPipeline
from visionflow.events.event import Event
from visionflow.events.generator import EventGenerator

__all__ = [
    "StreamPipeline",
    "Event",
    "EventGenerator",
]
