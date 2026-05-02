# VisionFlow

<div align="center">

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Checked with mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)
[![Type Hints: 100%](https://img.shields.io/badge/Type%20Hints-100%25-brightgreen)](https://docs.python.org/3/library/typing.html)

**Real-time AI video stream processing framework with event-driven architecture**

[Features](#features) • [Quick Start](#quick-start) • [Documentation](#documentation) • [Contributing](#contributing)

</div>

---

## Overview

VisionFlow is a production-ready Python framework for building scalable, event-driven real-time video AI applications. It provides a clean abstraction layer for video ingestion, AI model inference, and multi-channel event distribution with full async/await support.

Perfect for building:
- **Video surveillance systems** with object detection and tracking
- **Live stream analytics** pipelines
- **Computer vision applications** requiring real-time processing
- **IoT video processing** solutions
- **Enterprise video analysis** platforms

## Features

### Core Capabilities
- **Multi-Source Video Ingestion** - RTSP streams, local files, custom sources
- **Parallel AI Processing** - Concurrent YOLO detection, OCR, and custom models
- **Event-Driven Architecture** - Async pub/sub system with handler registration
- **Multi-Channel Output** - REST API, WebSocket, Kafka, logging, custom outputs
- **Type-Safe & Async** - 100% type hints, full asyncio support throughout
- **Production-Grade** - Comprehensive error handling, structured logging, extensive testing

### Built-In Capabilities
- ✅ YOLO v8 object detection (nano to xlarge)
- ✅ Tesseract OCR text recognition
- ✅ FastAPI REST API with Swagger documentation
- ✅ Real-time WebSocket broadcast
- ✅ Apache Kafka message publishing
- ✅ YAML + Pydantic configuration management
- ✅ CLI for pipeline execution
- ✅ Worker pool for parallel inference

## Quick Start

### Installation

```bash
# Core installation
pip install visionflow

# With YOLO object detection support
pip install visionflow[yolo]

# With OCR text recognition support
pip install visionflow[ocr]

# With Apache Kafka integration
pip install visionflow[kafka]

# All optional features
pip install visionflow[yolo,ocr,kafka]

# Development setup
pip install visionflow[dev]
```

### Basic Usage

```python
import asyncio
from visionflow import StreamPipeline
from visionflow.ingestion import FileSource
from visionflow.processing.yolo import YOLOWorker
from visionflow.processing.pool import WorkerPool
from visionflow.outputs.log import LogOutput

async def main():
    # Create pipeline
    pipeline = StreamPipeline()
    
    # Add video source
    pipeline.add_source(FileSource("video.mp4", source_id="camera_1"))
    
    # Add YOLO detector
    pipeline.worker_pool = WorkerPool([YOLOWorker("detector", "yolov8n.pt")])
    
    # Add logging output
    pipeline.add_output(LogOutput())
    
    # Register event handler
    @pipeline.on_event("person_detected")
    async def on_person(event):
        print(f"Person detected: {event.data}")
    
    # Run pipeline
    await pipeline.run()

if __name__ == "__main__":
    asyncio.run(main())
```

### Using Configuration File

Create a `config.yaml`:

```yaml
name: "Vision Pipeline"

sources:
  - id: "rtsp_camera"
    type: "rtsp"
    url: "rtsp://camera.local/stream"
    fps: 30
  
  - id: "video_file"
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
  
  - id: "rest_api"
    type: "rest_api"
    host: "0.0.0.0"
    port: 8000
    enabled: true

log_level: "INFO"
debug: false
```

Run the pipeline:

```bash
visionflow run config.yaml
```

## Architecture

VisionFlow follows a layered, event-driven architecture designed for extensibility and testability.

### System Architecture

```
┌─────────────────────────────────────────────────┐
│           User Application                      │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│      StreamPipeline (Core Orchestrator)         │
├──────────┬──────────────┬──────────┬────────────┤
│Ingestion │ Processing   │ Events   │ Outputs    │
│ • RTSP   │ • YOLO       │ • Bus    │ • REST API │
│ • File   │ • OCR        │ • Event  │ • WebSocket│
│ • Custom │ • Pool       │ • Handler│ • Kafka    │
└──────────┴──────────────┴──────────┴────────────┘
                  │
         ┌────────▼────────┐
         │  External       │
         │  Systems        │
         └─────────────────┘
```

### Core Components

| Component | Purpose | Implementations |
|-----------|---------|-----------------|
| **Ingestion** | Video source abstraction | RTSP, File, Custom |
| **Processing** | AI model execution | YOLO, OCR, Custom models |
| **Events** | Async pub/sub system | Event, EventEngine, EventGenerator |
| **Outputs** | Event distribution | REST API, WebSocket, Kafka, Logging |
| **Configuration** | Settings management | YAML + Pydantic |
| **CLI** | Command-line interface | visionflow run/init |

For detailed architecture documentation, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## API Reference

### Event System

```python
from visionflow import Event, StreamPipeline

# Events are immutable data containers
event = Event(
    event_type="person_detected",
    source_id="camera_1",
    data={"class": "person", "confidence": 0.95},
    metadata={"frame_id": 123}
)

# Register event handlers with decorators
@pipeline.on_event("person_detected")
async def handle_detection(event):
    print(f"Event: {event.event_type}")
    print(f"Data: {event.data}")

# Or register manually
async def my_handler(event):
    pass

pipeline.event_engine.on("person_detected", my_handler)
```

### Pipeline API

```python
from visionflow import StreamPipeline
from visionflow.ingestion import RTSPSource, FileSource
from visionflow.processing.yolo import YOLOWorker
from visionflow.processing.pool import WorkerPool
from visionflow.outputs import RestAPIOutput, WebSocketOutput

# Create pipeline
pipeline = StreamPipeline()

# Add sources (multiple sources supported)
pipeline.add_source(RTSPSource("rtsp://camera/stream", "cam1"))
pipeline.add_source(FileSource("video.mp4", "file1"))

# Configure workers
pipeline.worker_pool = WorkerPool([
    YOLOWorker("detector", "yolov8n.pt")
])

# Add outputs
pipeline.add_output(RestAPIOutput(host="0.0.0.0", port=8000))
pipeline.add_output(WebSocketOutput())

# Register handlers
@pipeline.on_event("detection")
async def handle_detection(event):
    # Custom logic
    pass

# Run pipeline
await pipeline.run()
```

### Workers

```python
from visionflow.processing.yolo import YOLOWorker
from visionflow.processing.ocr import OCRWorker
from visionflow.processing.pool import WorkerPool

# Create workers
yolo = YOLOWorker("detector", model="yolov8m.pt")
ocr = OCRWorker("ocr", engine="tesseract")

# Use in pool for parallel processing
pool = WorkerPool([yolo, ocr])

# Process frames
await pool.initialize()
results = await pool.process_frame(frame)
await pool.cleanup()
```

For complete API documentation, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Examples

VisionFlow includes complete example implementations:

- [basic_detection.py](tests/examples/basic_detection.py) - YOLO detection with event handling
- [multi_source_api.py](tests/examples/multi_source_api.py) - Multiple sources with REST API
- [custom_handlers.py](tests/examples/custom_handlers.py) - Custom event filtering and tracking

Run examples:

```bash
python tests/examples/basic_detection.py
python tests/examples/multi_source_api.py
```

## Extensibility

VisionFlow is designed to be easily extended with custom sources, workers, and outputs.

### Custom Source

Implement a custom video source by inheriting from `BaseSource`:

```python
from visionflow.ingestion.base import BaseSource

class WebcamSource(BaseSource):
    """Custom webcam source using OpenCV."""
    
    async def connect(self):
        """Initialize camera connection."""
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            raise RuntimeError("Failed to open camera")
    
    async def disconnect(self):
        """Close camera connection."""
        if self.cap:
            self.cap.release()
    
    async def read_frame(self):
        """Read and return next frame."""
        ret, frame = self.cap.read()
        return frame if ret else None
```

### Custom Worker

Implement a custom AI model by inheriting from `BaseWorker`:

```python
from visionflow.processing.base import BaseWorker

class CustomModelWorker(BaseWorker):
    """Custom ML model worker."""
    
    async def initialize(self):
        """Load model on startup."""
        self.model = load_custom_model("model.pt")
    
    async def cleanup(self):
        """Cleanup on shutdown."""
        if hasattr(self, 'model'):
            del self.model
    
    async def process_frame(self, frame):
        """Run inference on frame."""
        results = self.model.predict(frame)
        return {
            "predictions": results,
            "worker_id": self.worker_id
        }
```

### Custom Output

Implement a custom output handler by inheriting from `BaseOutput`:

```python
from visionflow.outputs.base import BaseOutput

class DatabaseOutput(BaseOutput):
    """Output events to database."""
    
    async def start(self):
        """Initialize database connection."""
        self.db = connect_to_database()
        self.is_running = True
    
    async def stop(self):
        """Close database connection."""
        await self.db.close()
        self.is_running = False
    
    async def send_event(self, event):
        """Write event to database."""
        await self.db.insert("events", event.to_dict())
```

## Testing

VisionFlow includes comprehensive test coverage for all core components.

### Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=visionflow --cov-report=html

# Run specific test file
pytest tests/test_events.py -v

# Run with detailed output
pytest tests/ -v -s --tb=short
```

### Test Structure

- `tests/test_events.py` - Event system and pub/sub tests
- `tests/test_pipeline.py` - Pipeline integration tests  
- `tests/test_yolo.py` - YOLO worker tests
- `tests/debug_file_source.py` - Video source debugging
- `tests/examples/` - Working examples and demonstrations

## Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/yourusername/visionflow.git
cd visionflow

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev,yolo,ocr,kafka]"
```

### Code Quality

We maintain high code quality standards:

```bash
# Format code with black
black visionflow/ tests/

# Sort imports with isort
isort visionflow/ tests/

# Lint with flake8
flake8 visionflow/ tests/ --max-line-length=100

# Type checking with mypy
mypy visionflow/ --strict

# Run all checks
make check
```

### Make Commands

```bash
make test          # Run tests
make check         # Run linting, type checking, formatting
make format        # Format code with black and isort
make clean         # Clean build artifacts
make help          # Show all available commands
```

## Documentation

- **[Architecture Guide](docs/ARCHITECTURE.md)** - Detailed design and components
- **[Architecture Diagrams](docs/ARCHITECTURE_DIAGRAM.md)** - System diagrams and data flows
- **[Project Index](docs/INDEX.md)** - Complete file and API reference
- **[Quick Start](QUICKSTART.md)** - Quick reference guide
- **[Contributing](CONTRIBUTING.md)** - Contribution guidelines

## Project Structure

```
visionflow/                 # Main package
├── core/                   # Pipeline orchestrator
├── events/                 # Event system (Event, EventEngine, EventGenerator)
├── ingestion/              # Video sources (BaseSource, RTSP, File)
├── processing/             # AI workers (BaseWorker, YOLO, OCR, Pool)
├── outputs/                # Output handlers (REST API, WebSocket, Kafka, Logging)
├── config/                 # Configuration management (YAML + Pydantic)
├── cli/                    # Command-line interface
├── utils/                  # Utility functions and helpers
├── __init__.py             # Package exports
└── py.typed                # PEP 561 type marker

tests/                      # Test suite
├── test_events.py          # Event system tests
├── test_pipeline.py        # Pipeline integration tests
├── test_yolo.py            # YOLO worker tests
├── debug_file_source.py    # Source debugging
└── examples/               # Example implementations

docs/                       # Documentation
├── ARCHITECTURE.md         # Architecture guide
├── ARCHITECTURE_DIAGRAM.md # System diagrams
├── INDEX.md                # Complete reference
├── PROJECT_SUMMARY.md      # Project overview
└── CODE_CORRECTIONS.md     # Quality metrics
```

## Requirements

- **Python**: 3.10 or higher
- **Dependencies**: See [pyproject.toml](pyproject.toml) for complete list

### Core Dependencies
- `opencv-python` - Video processing
- `fastapi` & `uvicorn` - REST API
- `pydantic` - Configuration validation
- `numpy` - Array operations
- `aiofiles` - Async file I/O

### Optional Dependencies
- `ultralytics` - YOLO models
- `pytesseract` & `pillow` - OCR support
- `kafka-python` - Kafka integration

## Performance

VisionFlow is designed for high performance:

- **Async throughout**: Non-blocking I/O for responsiveness
- **Parallel processing**: Concurrent worker execution
- **Efficient memory usage**: Smart frame and event handling
- **Production-ready**: Tested at scale with real video streams

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Code of conduct
- Development setup
- Pull request process
- Code standards
- Testing requirements

## License

This project is licensed under the Apache License 2.0 - see [LICENSE](LICENSE) file for details.

## Support

- 📖 **Documentation**: See [docs/](docs/) directory
- 💬 **Issues**: GitHub Issues for bug reports and features
- 📧 **Email**: For direct support inquiries
- 🤝 **Contributing**: See [CONTRIBUTING.md](CONTRIBUTING.md)

## Citation

If you use VisionFlow in your research or application, please cite:

```bibtex
@software{visionflow2026,
  title={VisionFlow: Real-time AI Video Stream Processing Framework},
  author={VisionFlow Contributors},
  year={2026},
  url={https://github.com/yourusername/visionflow}
}
```

## Acknowledgments

VisionFlow is built on top of excellent open-source projects:
- [Ultralytics YOLO](https://github.com/ultralytics/ultralytics) for object detection
- [FastAPI](https://fastapi.tiangolo.com/) for REST API
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract) for text recognition
- [Pydantic](https://docs.pydantic.dev/) for configuration management

---

<div align="center">

Made with ❤️ by VisionFlow contributors

[⬆ Back to top](#visionflow)

</div>
