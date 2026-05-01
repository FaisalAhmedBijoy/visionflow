# VisionFlow Quick Reference

## Installation

```bash
# Basic installation
pip install visionflow

# With AI models
pip install visionflow[yolo,ocr,kafka]

# Development mode
pip install -e ".[dev]"
```

## CLI Commands

```bash
# Initialize new configuration
visionflow init config.yaml

# Run pipeline from config
visionflow run config.yaml --debug

# Show version
visionflow version
```

## Basic Usage

### Simple Pipeline

```python
import asyncio
from visionflow import StreamPipeline
from visionflow.ingestion import FileSource
from visionflow.processing.yolo import YOLOWorker
from visionflow.processing.pool import WorkerPool
from visionflow.outputs.log import LogOutput

async def main():
    pipeline = StreamPipeline()
    
    # Add components
    pipeline.add_source(FileSource("video.mp4"))
    pipeline.worker_pool = WorkerPool([YOLOWorker("detector", "yolov8n.pt")])
    pipeline.add_output(LogOutput())
    
    # Register handlers
    @pipeline.on_event("person_detected")
    async def handler(event):
        print(f"Person: {event.data['confidence']:.2f}")
    
    # Run
    await pipeline.run()

asyncio.run(main())
```

### Configuration File

```yaml
name: "My Pipeline"

sources:
  - id: "camera"
    type: "rtsp"
    url: "rtsp://camera.local/stream"
    fps: 30

workers:
  - id: "detector"
    type: "yolo"
    model: "yolov8n.pt"
    enabled: true

outputs:
  - id: "logger"
    type: "log"
    enabled: true

log_level: "INFO"
```

## Core Classes

### Event
```python
from visionflow import Event

event = Event(
    event_type="person_detected",
    source_id="camera_1",
    data={"confidence": 0.95, "box": [x, y, w, h]},
    metadata={"frame_id": 123}
)

# Convert to dict
event_dict = event.to_dict()
```

### StreamPipeline
```python
pipeline = StreamPipeline()

# Add components
pipeline.add_source(source)
pipeline.add_output(output)

# Register handlers
@pipeline.on_event("event_type")
async def handler(event):
    pass

# Lifecycle
await pipeline.start()
await pipeline.stop()
await pipeline.run()  # Blocking
```

### Sources
```python
from visionflow.ingestion import RTSPSource, FileSource

rtsp = RTSPSource("rtsp://camera/stream", "camera_1")
file = FileSource("video.mp4", "video_1", fps=30)
```

### Workers
```python
from visionflow.processing import YOLOWorker, OCRWorker, WorkerPool

yolo = YOLOWorker("detector", "yolov8m.pt")
ocr = OCRWorker("ocr")

pool = WorkerPool([yolo, ocr])
await pool.start()
results = await pool.process_frame(frame)
```

### Outputs
```python
from visionflow.outputs import (
    LogOutput, WebSocketOutput, 
    RestAPIOutput, KafkaOutput
)

log_out = LogOutput(level="INFO")
api_out = RestAPIOutput(host="0.0.0.0", port=8000)
ws_out = WebSocketOutput()
kafka_out = KafkaOutput(brokers=["localhost:9092"], topic="events")
```

## Custom Implementation

### Custom Source
```python
from visionflow.ingestion import BaseSource
import numpy as np

class CustomSource(BaseSource):
    async def connect(self):
        # Initialize connection
        pass
    
    async def disconnect(self):
        # Clean up
        pass
    
    async def read_frame(self):
        # Return numpy array (BGR) or None
        return frame
```

### Custom Worker
```python
from visionflow.processing import BaseWorker

class CustomWorker(BaseWorker):
    async def initialize(self):
        # Load model
        self.model = load_my_model()
    
    async def cleanup(self):
        # Cleanup
        pass
    
    async def process_frame(self, frame):
        # Run inference
        results = self.model(frame)
        return {
            "detections": results,
            "metadata": {...}
        }
```

### Custom Output
```python
from visionflow.outputs import BaseOutput

class CustomOutput(BaseOutput):
    async def start(self):
        # Initialize
        self.is_running = True
    
    async def stop(self):
        # Cleanup
        self.is_running = False
    
    async def send_event(self, event):
        # Process event
        print(f"Event: {event.event_type}")
```

## Development Commands

```bash
# Format code
make format

# Run linters
make lint

# Type checking
make type-check

# Run tests
make test

# Run all checks
make check

# Clean cache
make clean
```

## Configuration Options

### Source Types
- `rtsp`: RTSP stream
- `file`: Local video file
- `websrc`: WebRTC (future)

### Worker Types
- `yolo`: YOLO detection
- `ocr`: OCR recognition
- Custom: Implement BaseWorker

### Output Types
- `log`: Python logging
- `websocket`: WebSocket broadcast
- `rest_api`: FastAPI REST endpoint
- `kafka`: Apache Kafka
- Custom: Implement BaseOutput

## API Endpoints (RestAPIOutput)

```
GET /health              - Health check
GET /events              - Get last N events (limit=100)
GET /events/{event_id}   - Get specific event
```

## Event Types

Common event types from YOLO:
- `person_detected`
- `car_detected`
- `truck_detected`
- `bicycle_detected`
- (others based on YOLO classes)

From OCR:
- `text_recognized`

## Logging

```python
import logging
from visionflow.utils import setup_logging

setup_logging(level="DEBUG")

logger = logging.getLogger("visionflow.core.pipeline")
logger.debug("Debug message")
```

## Async Patterns

```python
# Register multiple handlers
@pipeline.on_event("detection")
async def handler1(event):
    pass

@pipeline.on_event("detection")
async def handler2(event):
    pass

# One-time handler
@pipeline.once_event("first_detection")
async def first_handler(event):
    pass

# Manual event emission (for testing)
from visionflow.events import Event
event = Event(...)
await pipeline.event_engine.emit(event)
```

## Testing

```python
import pytest
from visionflow.events import Event, EventEngine

@pytest.mark.asyncio
async def test_event_handler():
    engine = EventEngine()
    received = []
    
    async def handler(event):
        received.append(event)
    
    engine.on("test", handler)
    event = Event(event_type="test", source_id="test", data={})
    await engine.emit(event)
    
    assert len(received) == 1
```

## Resources

- **GitHub**: https://github.com/yourusername/visionflow
- **Documentation**: See README.md and docs/ folder
- **Examples**: See docs/examples/ folder
- **Contributing**: See CONTRIBUTING.md

## Performance Tips

1. Use smaller YOLO models (yolov8n) for real-time
2. Reduce FPS if processing can't keep up
3. Use WorkerPool for parallel processing
4. Filter events before output dispatch
5. Use logging level INFO in production

## Troubleshooting

**Module not found errors:**
```bash
pip install -e ".[yolo,ocr,kafka]"
```

**Type checking errors:**
```bash
pip install types-<package-name>
```

**Async/await errors:**
- Use `asyncio.run()` at entry point
- Mark async functions with `async def`
- Use `await` when calling async functions

**Import errors:**
- Ensure package is installed in editable mode
- Check PYTHONPATH

## License

Apache License 2.0
