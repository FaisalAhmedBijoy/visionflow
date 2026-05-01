"""
Example: Multiple sources with REST API output.
"""

import asyncio

from visionflow import StreamPipeline
from visionflow.ingestion import FileSource, RTSPSource
from visionflow.outputs.api import RestAPIOutput
from visionflow.outputs.log import LogOutput
from visionflow.processing.pool import WorkerPool
from visionflow.processing.yolo import YOLOWorker


async def main() -> None:
    """Run multi-source pipeline with REST API."""
    # Create pipeline
    pipeline = StreamPipeline()

    # Add multiple video sources
    pipeline.add_source(
        FileSource("parking_lot.mp4", source_id="parking_camera", fps=5)
    )
    pipeline.add_source(
        RTSPSource("rtsp://traffic.camera/stream", source_id="traffic_camera", fps=10)
    )

    # Add YOLO detector
    yolo_worker = YOLOWorker("detector", "yolov8m.pt")
    pipeline.worker_pool = WorkerPool([yolo_worker])

    # Add outputs
    pipeline.add_output(LogOutput())
    pipeline.add_output(RestAPIOutput(host="0.0.0.0", port=8000))

    # Register handlers
    detection_count = {"total": 0}

    @pipeline.on_event("person_detected")
    async def on_person(event) -> None:
        detection_count["total"] += 1
        print(f"[{event.source_id}] Person #{detection_count['total']}")

    # Run pipeline
    print("Multi-source pipeline started...")
    print("API running on http://0.0.0.0:8000")
    print("  GET /health - Health check")
    print("  GET /events - Get recent events")
    print("  GET /events/{event_id} - Get specific event")
    
    await pipeline.run()


if __name__ == "__main__":
    asyncio.run(main())
