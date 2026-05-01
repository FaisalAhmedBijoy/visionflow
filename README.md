# VisionFlow: Real-Time AI Video Stream Processing Framework

An event-driven, production-ready Python framework for real-time video stream processing with AI models.

## 🎯 Features

- **Multi-Source Ingestion**: RTSP, WebRTC, local files, USB cameras
- **AI Processing**: YOLO object detection, OCR text recognition, extensible model support
- **Event-Driven Architecture**: Async event system with handlers and generators
- **Multiple Outputs**: REST API, WebSocket, Kafka, logging
- **Production Ready**: Type hints, async/await, comprehensive error handling
- **Modular Design**: Clean separation of concerns, easy to extend

## 📦 Installation

```bash
pip install visionflow
```

### With Optional Dependencies

```bash
# For YOLO object detection
pip install visionflow[yolo]

# For OCR text recognition
pip install visionflow[ocr]

# For Kafka integration
pip install visionflow[kafka]

# For development and testing
pip install visionflow[dev]
```

## 🚀 Quick Start

### Basic Example

```python
from visionflow import StreamPipeline
from visionflow.ingestion import FileSource
from visionflow.processing.yolo import YOLOWorker
from visionflow.processing.pool import WorkerPool
from visionflow.outputs.log import LogOutput

# Create pipeline
pipeline = StreamPipeline()

# Add video source
source = FileSource("video.mp4", source_id="camera_1")
pipeline.add_source(source)

# Add YOLO detector
workers = [YOLOWorker("detector", "yolov8n.pt")]
pipeline.worker_pool = WorkerPool(workers)

# Add logging output
pipeline.add_output(LogOutput())

# Register event handler
@pipeline.on_event("person_detected")
async def on_person(event):
    print(f"Person detected: {event.data}")

# Run pipeline
await pipeline.run()
```

### Using Configuration File

```bash
visionflow init config.yaml
visionflow run config.yaml
```

Example `config.yaml`:

```yaml
name: "My Vision Pipeline"

sources:
  - id: "camera_1"
    type: "rtsp"
    url: "rtsp://camera.local/stream"
    fps: 30

  - id: "file_1"
    type: "file"
    url: "video.mp4"
    fps: 30

workers:
  - id: "detector"
    type: "yolo"
    model: "yolov8n.pt"
    enabled: true

  - id: "ocr"
    type: "ocr"
    enabled: false

outputs:
  - id: "logger"
    type: "log"
    enabled: true
    config:
      level: "INFO"

log_level: "INFO"
debug: false
```

## 🏗️ Architecture

### Core Components

#### 1. StreamPipeline
Main orchestrator that manages the entire pipeline lifecycle.

```python
pipeline = StreamPipeline(
    sources=[...],
    workers=[...],
    outputs=[...]
)
```

#### 2. Event System
- **Event**: Core event class with type, timestamp, source_id, and data
- **EventEngine**: Manages event handlers and emission
- **EventGenerator**: Converts inference results to structured events

```python
@pipeline.on_event("vehicle_detected")
async def handler(event):
    print(event.to_dict())
```

#### 3. Ingestion Layer
Base class `BaseSource` with implementations:
- **RTSPSource**: RTSP stream via OpenCV
- **FileSource**: Local video files
- **WebRTCSource**: (Coming soon) LiveKit WebRTC

#### 4. Processing Layer
Base class `BaseWorker` with implementations:
- **YOLOWorker**: YOLO object detection
- **OCRWorker**: Tesseract OCR
- **WorkerPool**: Async parallel processing

#### 5. Output Layer
Base class `BaseOutput` with implementations:
- **LogOutput**: Python logging
- **WebSocketOutput**: WebSocket broadcast
- **RestAPIOutput**: FastAPI-based REST API
- **KafkaOutput**: Kafka topic publishing
- **OutputDispatcher**: Routes events to multiple outputs

## 📚 API Reference

### Event Class

```python
from visionflow import Event

event = Event(
    event_type="vehicle_detected",
    source_id="camera_1",
    data={
        "class": "car",
        "confidence": 0.95,
        "box": [x1, y1, x2, y2]
    },
    metadata={"frame_id": 123}
)

# Convert to dict
event_dict = event.to_dict()
```

### Pipeline API

```python
pipeline = StreamPipeline()

# Add sources
pipeline.add_source(RTSPSource("rtsp://...", "camera_1"))
pipeline.add_source(FileSource("video.mp4"))

# Add outputs
pipeline.add_output(LogOutput())
pipeline.add_output(WebSocketOutput())

# Register handlers
@pipeline.on_event("event_type")
async def handler(event):
    pass

@pipeline.once_event("event_type")
async def one_time_handler(event):
    pass

# Run pipeline
await pipeline.run()

# Or start/stop separately
await pipeline.start()
await pipeline.stop()
```

### Workers

```python
# YOLO Detection
yolo_worker = YOLOWorker("detector", "yolov8m.pt")

# OCR Recognition
ocr_worker = OCRWorker("ocr", engine="tesseract")

# Worker Pool
pool = WorkerPool([yolo_worker, ocr_worker])
await pool.start()
results = await pool.process_frame(frame)
```

## 🔧 Configuration

Configuration is managed via YAML files using Pydantic models:

```python
from visionflow.config import load_config, save_config, PipelineConfig

# Load from file
config = load_config("config.yaml")

# Save to file
save_config(config, "new_config.yaml")

# Create programmatically
config = PipelineConfig(
    name="My Pipeline",
    sources=[...],
    workers=[...],
    outputs=[...],
    log_level="INFO"
)
```

## 🧪 Testing

Run tests with pytest:

```bash
pytest tests/
pytest tests/ -v  # Verbose
pytest tests/ --cov=visionflow  # With coverage
```

## 📁 Project Structure

```
visionflow/
├── core/              # Main pipeline orchestrator
├── events/            # Event system (Event, Engine, Generator)
├── ingestion/         # Video source implementations
├── processing/        # AI worker implementations
├── outputs/           # Output handlers (API, WebSocket, Kafka, etc.)
├── config/            # Configuration management
├── cli/               # Command-line interface
├── utils/             # Utility functions
└── __init__.py        # Package exports

tests/
├── test_events.py     # Event system tests
├── test_pipeline.py   # Pipeline tests
└── ...

docs/
├── architecture.md    # Architecture documentation
└── examples/          # Example implementations
```

## 🔌 Extending VisionFlow

### Custom Source

```python
from visionflow.ingestion.base import BaseSource

class CustomSource(BaseSource):
    async def connect(self):
        # Connect to your source
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
from visionflow.processing.base import BaseWorker

class CustomWorker(BaseWorker):
    async def initialize(self):
        # Load model
        pass
    
    async def cleanup(self):
        # Unload model
        pass
    
    async def process_frame(self, frame):
        # Run inference
        return {
            "results": [...],
            "metadata": {...}
        }
```

### Custom Output

```python
from visionflow.outputs.base import BaseOutput

class CustomOutput(BaseOutput):
    async def start(self):
        # Initialize connection
        self.is_running = True
    
    async def stop(self):
        # Clean up
        self.is_running = False
    
    async def send_event(self, event):
        # Send event to destination
        pass
```

## 📝 License

Apache License 2.0

## 🤝 Contributing

Contributions are welcome! See CONTRIBUTING.md for guidelines.

## 📚 Documentation

- [Architecture Guide](docs/architecture.md)
- [API Reference](docs/api.md)
- [Examples](docs/examples/)
