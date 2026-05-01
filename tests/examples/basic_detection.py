"""
Example: Basic video file processing with YOLO detection.
"""

import asyncio

from visionflow import StreamPipeline
from visionflow.ingestion import FileSource
from visionflow.outputs.log import LogOutput
from visionflow.processing.pool import WorkerPool
from visionflow.processing.yolo import YOLOWorker


async def main() -> None:
    """Run basic YOLO detection on video file."""
    # Create pipeline
    pipeline = StreamPipeline()

    # Add video source
    source = FileSource("data/car-detection.mp4", source_id="video_1", fps=10)
    pipeline.add_source(source)

    # Add YOLO detector
    yolo_worker = YOLOWorker("detector", "yolov8n.pt")
    pipeline.worker_pool = WorkerPool([yolo_worker])

    # Add logging output
    pipeline.add_output(LogOutput(level="INFO"))

    # Register event handler for detections
    @pipeline.on_event("person_detected")
    async def on_person(event) -> None:
        print(f"🚨 Person detected!")
        print(f"   Confidence: {event.data['confidence']:.2f}")
        print(f"   Location: {event.data['box']}")

    @pipeline.on_event("car_detected")
    async def on_car(event) -> None:
        print(f"🚗 Vehicle detected!")
        print(f"   Confidence: {event.data['confidence']:.2f}")

    # Run pipeline
    print("Starting video processing...")
    await pipeline.run()
    print("Pipeline finished!")


if __name__ == "__main__":
    asyncio.run(main())
