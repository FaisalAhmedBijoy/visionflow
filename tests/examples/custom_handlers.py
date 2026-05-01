"""
Example: Custom event handlers and filtering.
"""

import asyncio
from collections import defaultdict
from datetime import datetime, timedelta

from visionflow import StreamPipeline, Event
from visionflow.ingestion import FileSource
from visionflow.outputs.log import LogOutput
from visionflow.processing.pool import WorkerPool
from visionflow.processing.yolo import YOLOWorker


class DetectionTracker:
    """Track detections over time."""

    def __init__(self, window_seconds: int = 60) -> None:
        """Initialize tracker."""
        self.window = timedelta(seconds=window_seconds)
        self.detections: dict[str, list[datetime]] = defaultdict(list)

    def add(self, event_type: str) -> None:
        """Record a detection."""
        now = datetime.utcnow()
        self.detections[event_type].append(now)
        # Clean old entries
        cutoff = now - self.window
        self.detections[event_type] = [
            t for t in self.detections[event_type] if t > cutoff
        ]

    def count(self, event_type: str) -> int:
        """Get count in window."""
        return len(self.detections[event_type])


async def main() -> None:
    """Run pipeline with custom handlers."""
    # Create tracker
    tracker = DetectionTracker(window_seconds=60)

    # Create pipeline
    pipeline = StreamPipeline()

    # Add source
    pipeline.add_source(FileSource("video.mp4", source_id="camera_1", fps=15))

    # Add detector
    pipeline.worker_pool = WorkerPool([YOLOWorker("detector", "yolov8n.pt")])
    pipeline.add_output(LogOutput())

    # Custom handler: Track and report
    @pipeline.on_event("person_detected")
    async def on_person(event: Event) -> None:
        tracker.add("person")
        confidence = event.data.get("confidence", 0)

        if confidence > 0.9:
            print(f"✨ High-confidence person detection: {confidence:.2f}")

        count = tracker.count("person")
        if count % 10 == 0:
            print(f"📊 {count} people detected in last 60s")

    @pipeline.on_event("car_detected")
    async def on_car(event: Event) -> None:
        tracker.add("car")
        confidence = event.data.get("confidence", 0)

        if confidence > 0.95:
            print(f"🚗 High-confidence vehicle: {confidence:.2f}")

    # One-time handler: First detection
    @pipeline.once_event("person_detected")
    async def first_person(event: Event) -> None:
        print("🎬 Pipeline is working - first person detected!")

    # Run pipeline
    print("Starting custom handler pipeline...")
    await pipeline.run()
    print(f"\nFinal counts: {dict(tracker.detections)}")


if __name__ == "__main__":
    asyncio.run(main())
