"""
Example: Basic video file processing with YOLO detection.
"""

import asyncio
import logging
import os
from pathlib import Path

from visionflow import StreamPipeline
from visionflow.ingestion import FileSource
from visionflow.outputs.log import LogOutput
from visionflow.processing.pool import WorkerPool
from visionflow.processing.yolo import YOLOWorker

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


async def main() -> None:
    """Run basic YOLO detection on video file."""
    # Print current working directory and check video file
    cwd = os.getcwd()
    print(f"📁 Current working directory: {cwd}")
    
    video_path = "data/car-detection.mp4"
    if Path(video_path).exists():
        print(f"✅ Video file found: {video_path}")
    else:
        print(f"❌ Video file NOT found: {video_path}")
        print(f"   Checking if file exists in absolute path...")
        abs_path = Path(cwd) / video_path
        if abs_path.exists():
            print(f"   ✅ Found at: {abs_path}")
            video_path = str(abs_path)
        else:
            print(f"   ❌ File not found. Please check the path.")
            return
    
    # Create pipeline
    pipeline = StreamPipeline()

    # Add video source
    source = FileSource(video_path, source_id="video_1", fps=10)
    pipeline.add_source(source)

    # Add YOLO detector
    yolo_worker = YOLOWorker("detector", "models/yolov8n.pt")
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
