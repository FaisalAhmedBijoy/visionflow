"""
Ingestion module — video stream sources.

Sources are responsible for reading frames from a video input and yielding
them to the processing pipeline.
"""

from visionflow.ingestion.base import BaseSource
from visionflow.ingestion.file import FileSource
from visionflow.ingestion.rtsp import RTSPSource
from visionflow.ingestion.webcam import WebcamSource

__all__ = ["BaseSource", "FileSource", "RTSPSource", "WebcamSource"]
