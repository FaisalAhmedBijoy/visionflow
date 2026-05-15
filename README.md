# VisionFlow

<div align="center">

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Type Hints](https://img.shields.io/badge/Type%20Hints-100%25-brightgreen)](#)

**Event-driven real-time AI video stream processing framework**

[Features](#features) • [Installation](#installation) • [Quick Start](#quick-start) • [Documentation](#documentation) • [Contributing](#contributing)

</div>

## Overview

VisionFlow is a production-ready Python framework for building scalable, event-driven real-time video AI applications. It provides a clean abstraction layer for video ingestion, AI model inference, and multi-channel event distribution with full async/await support.

### Use Cases
- Video surveillance with object detection and tracking
- Live stream analytics and monitoring
- Real-time computer vision applications
- IoT video processing at the edge
- Enterprise video analysis platforms

## Key Features

- **Multi-Source Ingestion** – RTSP streams, local files, and custom sources
- **Parallel AI Processing** – Concurrent YOLO detection, OCR, and custom models
- **Event-Driven Architecture** – Async pub/sub system with declarative handlers
- **Multi-Channel Output** – REST API, WebSocket, Kafka, file, and custom outputs
- **Fully Typed** – 100% type hints for IDE autocomplete and static analysis
- **Async-First** – Full asyncio support throughout the entire framework
- **Production-Ready** – Comprehensive error handling, structured logging, and extensive testing
- **Extensible** – Custom sources, workers, and outputs via simple inheritance
- **YAML Configuration** – Declarative pipeline configuration with Pydantic validation
## Installation

### From PyPI

```bash
# Core installation
pip install visionflow-ai

# With YOLO object detection
pip install visionflow-ai[yolo]

# With OCR text recognition
pip install visionflow-ai[ocr]

# With Apache Kafka integration
pip install visionflow-ai[kafka]

# All optional dependencies
pip install visionflow-ai[yolo,ocr,kafka]

# Development tools
pip install visionflow-ai[dev]
```

### From Source

```bash
git clone https://github.com/FaisalAhmedBijoy/visionflow.git
cd visionflow
pip install -e ".[dev,yolo,ocr,kafka]"
```

## Quick Start

### Basic Example

```python
import asyncio
from visionflow import StreamPipeline
from visionflow.ingestion import FileSource
from visionflow.processing.yolo import YOLOWorker
from visionflow.processing.pool import WorkerPool
from visionflow.outputs.log import LogOutput

async def main():
    pipeline = StreamPipeline()
    
    # Add video source
    pipeline.add_source(FileSource("video.mp4", source_id="main_camera"))
    
    # Configure AI workers
    pipeline.worker_pool = WorkerPool([
        YOLOWorker("detector", model="yolov8n.pt")
    ])
    
    # Add output handler
    pipeline.add_output(LogOutput())
    
    # Handle events
    @pipeline.on_event("detection")
    async def on_detection(event):
        print(f"Detected: {event.data}")
    
    await pipeline.run()
```

### Configuration-Driven Usage

Create `pipeline.yaml`:

```yaml
name: "Real-Time Video Analysis"

sources:
  - id: "main_camera"
    type: "rtsp"
    url: "rtsp://camera.local/stream"
    fps: 30
  
  - id: "backup_file"
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
    enabled: true

outputs:
  - id: "logger"
    type: "log"
    enabled: true
  
  - id: "api"
    type: "rest_api"
    host: "0.0.0.0"
    port: 8000
    enabled: true
  
  - id: "events_kafka"
    type: "kafka"
    broker: "localhost:9092"
    topic: "video_events"
    enabled: false

log_level: "INFO"
debug: false
```

Run with configuration:

```bash
visionflow run pipeline.yaml
```

## Architecture

VisionFlow follows a layered, event-driven architecture designed for scalability, extensibility, and testability.

### System Design

```
┌─────────────────────────────────────────────┐
│        User Application Layer               │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│      StreamPipeline (Orchestrator)          │
├──────────┬───────────┬──────────┬───────────┤
│Ingestion │Processing │  Events  │  Outputs  │
│ • RTSP   │  • YOLO   │  • Bus   │ • REST    │
│ • File   │  • OCR    │  • Emit  │ • WS      │
│ • Custom │  • Custom │  • Sub   │ • Kafka   │
└──────────┴───────────┴──────────┴───────────┘
                  │
         ┌────────▼────────┐
         │  External       │
         │  Systems        │
         └─────────────────┘
```

### Core Modules

| Module | Purpose | Implementations |
|--------|---------|-----------------|
| **Ingestion** | Video source abstraction | RTSP, File, Webcam, Custom |
| **Processing** | AI model execution | YOLO, OCR, Custom |
| **Events** | Async pub/sub messaging | Event, EventEngine, EventGenerator |
| **Outputs** | Event distribution | REST API, WebSocket, Kafka, File, Logging |
| **Config** | Settings management | YAML + Pydantic validation |
| **CLI** | Command-line interface | Configuration, execution, debugging |

## API Reference

### Stream Pipeline

```python
from visionflow import StreamPipeline
from visionflow.ingestion import RTSPSource, FileSource
from visionflow.processing.yolo import YOLOWorker
from visionflow.processing.pool import WorkerPool
from visionflow.outputs import RestAPIOutput, WebSocketOutput

# Initialize pipeline
pipeline = StreamPipeline(name="MyPipeline", debug=True)

# Add video sources (multiple supported)
pipeline.add_source(RTSPSource("rtsp://camera/stream", source_id="cam1"))
pipeline.add_source(FileSource("video.mp4", source_id="file1"))

# Configure worker pool for parallel inference
pipeline.worker_pool = WorkerPool([
    YOLOWorker("detector", model="yolov8m.pt")
])

# Add output handlers
pipeline.add_output(RestAPIOutput(host="0.0.0.0", port=8000))
pipeline.add_output(WebSocketOutput(port=8001))

# Register event handlers
@pipeline.on_event("detection")
async def handle_detection(event):
    """Process detection events."""
    print(f"Objects detected: {event.data}")

# Run the pipeline
await pipeline.run()
```

### Event System

```python
from visionflow import Event, StreamPipeline

# Events are immutable data containers
event = Event(
    event_type="person_detected",
    source_id="camera_1",
    data={"class": "person", "confidence": 0.95},
    metadata={"frame_id": 123, "timestamp": 1234567890}
)

# Register event handlers with decorators
@pipeline.on_event("person_detected")
async def on_person(event: Event) -> None:
    print(f"Event: {event.event_type}")
    print(f"Data: {event.data}")
    print(f"Source: {event.source_id}")
```

### Custom Components

Extend VisionFlow with custom implementations:

#### Custom Source

```python
from visionflow.ingestion.base import BaseSource

class CustomVideoSource(BaseSource):
    """Custom video source implementation."""
    
    async def connect(self) -> None:
        """Initialize connection."""
        # Setup code here
        pass
    
    async def disconnect(self) -> None:
        """Cleanup connection."""
        pass
    
    async def read_frame(self) -> Optional[Any]:
        """Read and return next frame."""
        # Return frame or None
        pass
```

#### Custom Worker

```python
from visionflow.processing.base import BaseWorker

class CustomAIWorker(BaseWorker):
    """Custom AI model worker."""
    
    async def initialize(self) -> None:
        """Load model on startup."""
        self.model = load_model("model.pt")
    
    async def cleanup(self) -> None:
        """Cleanup on shutdown."""
        if hasattr(self, 'model'):
            del self.model
    
    async def process_frame(self, frame: Any) -> Dict[str, Any]:
        """Run inference on frame."""
        results = self.model.predict(frame)
        return {"predictions": results, "worker_id": self.worker_id}
```

#### Custom Output

```python
from visionflow.outputs.base import BaseOutput
from visionflow.events import Event

class CustomOutput(BaseOutput):
    """Custom event output handler."""
    
    async def start(self) -> None:
        """Initialize output."""
        self.is_running = True
    
    async def stop(self) -> None:
        """Cleanup output."""
        self.is_running = False
    
    async def send_event(self, event: Event) -> None:
        """Process and send event."""
        if self.is_running:
            # Handle event
            pass
```

## Examples

Complete example implementations are available in the [tests/examples/](tests/examples/) directory:

- [basic_detection.py](tests/examples/basic_detection.py) – YOLO object detection with event handling
- [multi_source_api.py](tests/examples/multi_source_api.py) – Multiple video sources with REST API
- [custom_handlers.py](tests/examples/custom_handlers.py) – Event filtering and custom handlers

Run an example:

```bash
python tests/examples/basic_detection.py
```

## Testing

VisionFlow includes comprehensive test coverage across all core components.

### Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=visionflow --cov-report=html

# Run specific test file
pytest tests/test_events.py -v

# Run with detailed output and stop on first failure
pytest tests/ -vvs -x
```

### Test Structure

```
tests/
├── test_config.py      # Configuration validation
├── test_events.py      # Event system and pub/sub
├── test_pipeline.py    # Pipeline integration tests
├── test_sources.py     # Video source tests
├── test_workers.py     # AI worker tests
├── test_outputs.py     # Output handler tests
└── examples/           # Working example implementations
```

Current test coverage: **105+ tests** with high reliability.

## Development

### Setting Up Development Environment

```bash
# Clone repository
git clone https://github.com/FaisalAhmedBijoy/visionflow.git
cd visionflow

# Create virtual environment (Python 3.10+)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with all dependencies
pip install -e ".[dev,yolo,ocr,kafka]"
```

### Code Quality Standards

VisionFlow maintains strict code quality standards:

```bash
# Format code with Black
black visionflow/ tests/

# Sort imports with isort
isort visionflow/ tests/

# Lint with flake8
flake8 visionflow/ tests/ --max-line-length=100

# Type check with mypy
mypy visionflow/ --strict

# Run all quality checks
make check

# Run development setup
python setup_dev.py
```

### Make Targets

```bash
make test       # Run test suite
make check      # Run all linting and type checks
make format     # Format code with black and isort
make clean      # Remove build artifacts
make help       # Show all available commands
```

## Documentation

Complete documentation is available in the [docs/](docs/) directory:

- **[Architecture Guide](docs/ARCHITECTURE.md)** – Detailed design and component architecture
- **[Architecture Diagrams](docs/ARCHITECTURE_DIAGRAM.md)** – Visual system diagrams
- **[API Reference](docs/INDEX.md)** – Complete API documentation
- **[Quick Reference](QUICKSTART.md)** – Quick start examples
- **[Contributing Guide](CONTRIBUTING.md)** – Contribution guidelines
- **[Publishing Guide](docs/PUBLISHING.md)** – PyPI publishing instructions

## Project Structure

```
visionflow/                      # Main package
├── core/                        # Pipeline orchestrator and core logic
├── events/                      # Event system (Event, EventEngine, EventGenerator)
├── ingestion/                   # Video sources (BaseSource, RTSP, File, Webcam)
├── processing/                  # AI workers (BaseWorker, YOLO, OCR, WorkerPool)
├── outputs/                     # Output handlers (REST API, WebSocket, Kafka, File, Log)
├── config/                      # Configuration management (YAML + Pydantic)
├── cli/                         # Command-line interface
├── utils/                       # Utilities and helpers
└── py.typed                     # PEP 561 type marker for mypy

tests/                           # Comprehensive test suite
├── test_config.py               # Configuration tests
├── test_events.py               # Event system tests
├── test_pipeline.py             # Pipeline integration tests
├── test_sources.py              # Source/ingestion tests
├── test_workers.py              # Worker/processing tests
├── test_outputs.py              # Output handler tests
└── examples/                    # Example implementations

docs/                            # Documentation
├── ARCHITECTURE.md              # Architecture and design
├── ARCHITECTURE_DIAGRAM.md      # System diagrams
├── INDEX.md                     # API reference
├── PROJECT_SUMMARY.md           # Project overview
├── PUBLISHING.md                # Publishing guide
└── CODE_CORRECTIONS.md          # Quality metrics
```

## Requirements

- **Python:** 3.10 or higher
- **OS:** Linux, macOS, or Windows

### Core Dependencies

| Package | Purpose | Version |
|---------|---------|---------|
| opencv-python | Video processing | ≥4.8.0 |
| fastapi | REST API framework | ≥0.104.0 |
| pydantic | Configuration validation | ≥2.4.0 |
| numpy | Numerical operations | ≥1.24.0 |
| aiofiles | Async file I/O | ≥23.2.0 |

### Optional Dependencies

| Package | Purpose | Install |
|---------|---------|---------|
| ultralytics | YOLO models | `pip install visionflow-ai[yolo]` |
| pytesseract | OCR support | `pip install visionflow-ai[ocr]` |
| kafka-python | Kafka integration | `pip install visionflow-ai[kafka]` |
| paho-mqtt | MQTT integration | `pip install visionflow-ai[mqtt]` |

See [pyproject.toml](pyproject.toml) for complete dependency list.

## Performance

VisionFlow is optimized for production use:

- **Async I/O** – Non-blocking operations throughout
- **Parallel Processing** – Concurrent worker execution
- **Memory Efficient** – Smart frame and event buffering
- **Low Latency** – Optimized for real-time applications
- **Scalable** – Handles multiple streams simultaneously

## Contributing

We welcome contributions from the community! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:

- Code of conduct
- Development setup guide
- Pull request process
- Code style and standards
- Testing requirements
- Documentation guidelines

### Quick Contribution Steps

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes and add tests
4. Run quality checks: `make check`
5. Commit with clear messages: `git commit -m "Add my feature"`
6. Push to your fork: `git push origin feature/my-feature`
7. Open a pull request with description

## License

Licensed under the Apache License 2.0. See [LICENSE](LICENSE) file for full details.

```
Copyright 2024-2026 VisionFlow Contributors

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

## Support & Community

- **Documentation:** [docs/](docs/) directory
- **Bug Reports:** [GitHub Issues](https://github.com/FaisalAhmedBijoy/visionflow/issues)
- **Discussions:** [GitHub Discussions](https://github.com/FaisalAhmedBijoy/visionflow/discussions)
- **Contributing:** See [CONTRIBUTING.md](CONTRIBUTING.md)

## Acknowledgments

VisionFlow builds on excellent open-source projects:

- [Ultralytics YOLO](https://github.com/ultralytics/ultralytics) – Object detection models
- [FastAPI](https://fastapi.tiangolo.com/) – Web framework
- [Pydantic](https://docs.pydantic.dev/) – Data validation
- [OpenCV](https://opencv.org/) – Computer vision library
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract) – Text recognition

## Citation

If you use VisionFlow in your research or project, please cite:

```bibtex
@software{visionflow2024,
  author = {Faisal Ahmed},
  title = {VisionFlow: Event-driven Real-time AI Video Processing},
  year = {2026},
  url = {https://github.com/FaisalAhmedBijoy/visionflow}
}
```

