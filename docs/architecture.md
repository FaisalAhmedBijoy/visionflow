# VisionFlow Architecture

## Overview

VisionFlow is an event-driven, production-ready Python framework for real-time AI video stream processing. Built on clean architecture principles with strict separation of concerns, each layer is independently testable and replaceable.

**Version**: 0.1.0  
**Status**: Production-Ready  
**Python**: 3.10+

## Layered Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       User Application                          │
├─────────────────────────────────────────────────────────────────┤
│                  StreamPipeline (Core Orchestrator)              │
├─────────────────┬──────────────────┬──────────────────┐         │
│  Ingestion      │   Processing     │   Outputs        │         │
│  ┌───────────┐  │  ┌────────────┐  │  ┌────────────┐ │         │
│  │ RTSP      │  │  │ YOLO       │  │  │ REST API   │ │         │
│  │ File      │  │  │ OCR        │  │  │ WebSocket  │ │         │
│  │ (Custom)  │  │  │ Pool       │  │  │ Kafka      │ │         │
│  └───────────┘  │  │ (Custom)   │  │  │ Logging    │ │         │
│                 │  └────────────┘  │  │ (Custom)   │ │         │
│                 │                  │  └────────────┘ │         │
└─────────────────┴──────────────────┴──────────────────┘         │
├─────────────────────────────────────────────────────────────────┤
│                   Event System (Async Pub/Sub)                  │
├─────────────────────────────────────────────────────────────────┤
│              Configuration System (YAML + Pydantic)              │
├─────────────────────────────────────────────────────────────────┤
│           CLI & Utilities (Click + Helper Functions)             │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Core Module - StreamPipeline

**File**: `visionflow/core/pipeline.py` (271 LOC)

The main orchestrator that coordinates all components in the framework.

**Key Class**: `StreamPipeline`

**Responsibilities:**
- Initialize and manage all video sources
- Register and manage AI workers (YOLO, OCR, custom models)
- Register event handlers and listeners
- Coordinate frame ingestion, processing, and output distribution
- Manage complete lifecycle (start/stop/cleanup)
- Handle graceful shutdown on errors

**Design Patterns:** Facade + Factory + Orchestrator

**Usage Example:**
```python
from visionflow.core import StreamPipeline
from visionflow.ingestion import FileSource
from visionflow.processing.yolo import YOLOWorker
from visionflow.outputs.log import LogOutput

pipeline = StreamPipeline()
pipeline.add_source(FileSource("video.mp4"))
pipeline.add_worker(YOLOWorker())
pipeline.add_output(LogOutput())

@pipeline.on_event("detection")
async def handle_detection(event):
    print(f"Detected: {event.data}")

await pipeline.run()
```

### 2. Events Module - Async Pub/Sub System

**Files**: `visionflow/events/` (280+ LOC total)

Three core classes that implement an async event-driven architecture:

#### Event (`event.py`, 45 LOC)
- **Type**: Immutable dataclass
- **Purpose**: Represents a single event in the system
- **Fields**: 
  - `event_type`: Type of event (detection, ocr_result, custom)
  - `source_id`: Which source generated it
  - `timestamp`: When the event occurred
  - `data`: Event payload (detections, text, etc.)
  - `metadata`: Additional context
  - `event_id`: Unique identifier
- **Features**: Fully serializable to JSON/dict

#### EventEngine (`engine.py`, 120 LOC)
- **Type**: Async event bus/message broker
- **Purpose**: Coordinates event publishing and subscription
- **Methods**:
  - `on(event_type, handler)`: Register event listener
  - `once(event_type, handler)`: One-time listener
  - `off(event_type, handler)`: Unregister listener
  - `emit(event)`: Broadcast event to all registered handlers
  - `clear()`: Remove all listeners
- **Features**: Async handlers with error isolation

#### EventGenerator (`generator.py`, 110 LOC)
- **Type**: Factory for converting results to events
- **Purpose**: Bridge between inference results and event system
- **Pre-built Generators**:
  - `default_yolo_generator()`: YOLO detection → Event
  - `default_ocr_generator()`: OCR text → Event
- **Extension**: `register_generator()` for custom generators
- **Customization**: Create domain-specific event types

**Design Pattern**: Observer + Factory + Pub/Sub

### 3. Ingestion Module - Video Source Abstraction

**Files**: `visionflow/ingestion/` (250+ LOC total)

Abstract interface and implementations for video/media sources.

#### BaseSource (`base.py`, 83 LOC)
- **Purpose**: Abstract interface for all video sources
- **Key Methods**:
  - `async connect()`: Initialize source connection
  - `async read_frame()`: Get next frame (returns numpy array or None)
  - `async disconnect()`: Cleanup and close connection
  - `get_info()`: Source metadata (resolution, FPS, etc.)

#### FileSource (`file.py`, 84 LOC)
- **Purpose**: Local video file playback
- **Supported Formats**: MP4, AVI, MOV, MKV, etc.
- **Features**:
  - Non-blocking async frame reading
  - Frame rate control/synchronization
  - Total frame count tracking
  - Graceful EOF handling
- **Uses**: OpenCV (cv2) VideoCapture

#### RTSPSource (`rtsp.py`, 104 LOC)
- **Purpose**: RTSP/RTMP stream ingestion
- **Features**:
  - Real-time streaming support
  - Connection retry logic
  - Frame drop detection
  - Network error handling
- **Uses**: OpenCV (cv2) VideoCapture with RTSP URIs

**Design Pattern**: Template Method + Strategy

**Extension Example:**
```python
class WebCamSource(BaseSource):
    async def connect(self):
        self.cap = cv2.VideoCapture(0)  # USB camera
    
    async def read_frame(self):
        ret, frame = self.cap.read()
        return frame if ret else None
```

### 4. Processing Module - AI Worker Framework

**Files**: `visionflow/processing/` (350+ LOC total)

Abstract interface and implementations for AI/ML model execution.

#### BaseWorker (`base.py`, 75 LOC)
- **Purpose**: Abstract interface for all processing workers
- **Key Methods**:
  - `async initialize()`: Load model/initialize resources
  - `async process_frame(frame)`: Run inference on frame
  - `async cleanup()`: Release resources
- **Lifecycle**: Initialize → process_frame(many) → cleanup

#### YOLOWorker (`yolo.py`, 120 LOC)
- **Purpose**: Object detection using YOLO v8
- **Models Supported**: nano, small, medium, large, xlarge
- **Outputs**:
  - Bounding boxes with coordinates
  - Class labels and confidence scores
  - Multiple detections per frame
- **Uses**: Ultralytics YOLO library
- **Performance**: Configurable confidence threshold

#### OCRWorker (`ocr.py`, 120 LOC)
- **Purpose**: Optical Character Recognition (text extraction)
- **Features**:
  - Text detection and extraction from frames
  - Language configuration
  - Confidence scoring
- **Uses**: Tesseract OCR engine
- **Output**: Extracted text with bounding regions

#### WorkerPool (`pool.py`, 120 LOC)
- **Purpose**: Concurrent parallel processing
- **Features**:
  - Execute multiple workers simultaneously
  - Error isolation per worker
  - Results aggregation
  - Dynamic worker management
- **Pattern**: Process each frame through all workers in parallel
- **Example**: Run YOLO + OCR + custom model on same frame concurrently

**Design Pattern**: Template Method + Object Pool + Composite

**Extension Example:**
```python
class CustomWorker(BaseWorker):
    async def initialize(self):
        self.model = load_my_model()
    
    async def process_frame(self, frame):
        results = self.model.predict(frame)
        return results
```

### 5. Outputs Module - Event Distribution System

**Files**: `visionflow/outputs/` (450+ LOC total)

Abstract interface and implementations for distributing events to external systems.

#### BaseOutput (`base.py`, 45 LOC)
- **Purpose**: Abstract interface for all output handlers
- **Key Methods**:
  - `async start()`: Initialize and start output
  - `async send_event(event)`: Process and send event
  - `async stop()`: Cleanup and shutdown
- **Lifecycle**: start() → send_event(many) → stop()

#### LogOutput (`log.py`, 45 LOC)
- **Purpose**: Python logging integration
- **Outputs Events To**: Python logging system
- **Use Case**: Development, debugging, simple deployments
- **Format**: Structured log entries with event details

#### WebSocketOutput (`websocket.py`, 80 LOC)
- **Purpose**: Real-time event streaming via WebSocket
- **Features**:
  - Broadcasting to multiple clients
  - JSON serialization
  - Connection lifecycle management
- **Use Case**: Dashboard, real-time monitoring, live updates
- **Clients**: Web browsers, real-time dashboards

#### RestAPIOutput (`api.py`, 100 LOC)
- **Purpose**: FastAPI-based REST API endpoints
- **Endpoints**:
  - `GET /health` - Health check
  - `GET /status` - Pipeline status
  - `GET /stats` - Event statistics
  - `POST /events` - Webhook receiver
  - `GET /docs` - Swagger documentation
- **Use Case**: Integration with other services, webhooks
- **Features**: Event history storage, statistics tracking

#### KafkaOutput (`kafka.py`, 110 LOC)
- **Purpose**: Apache Kafka topic publishing
- **Features**:
  - Publish events to Kafka topics
  - Partitioning support
  - Error handling and retries
- **Use Case**: Enterprise systems, data pipelines, streaming analytics
- **Configuration**: Topic names, broker addresses, serialization

#### OutputDispatcher (`dispatcher.py`, 100 LOC)
- **Purpose**: Route events to multiple outputs simultaneously
- **Features**:
  - Manage multiple output handlers
  - Error isolation per output
  - Concurrent dispatch
- **Pattern**: Send same event to REST API, WebSocket, Kafka, and Logging

**Design Pattern**: Strategy + Composite + Adapter

**Extension Example:**
```python
class CustomOutput(BaseOutput):
    async def start(self):
        self.connection = connect_to_service()
        self.is_running = True
    
    async def send_event(self, event):
        await self.connection.send(event.to_dict())
```

### 6. Configuration Module - YAML + Pydantic

**File**: `visionflow/config/config.py` (120 LOC)

Two-tier configuration approach combining user-friendly YAML with type-safe Pydantic models.

#### YAML Configuration Format
```yaml
pipeline:
  sources:
    - type: file
      path: video.mp4
      fps: 30
  workers:
    - type: yolo
      model: yolov8n
      confidence: 0.5
  outputs:
    - type: log
    - type: websocket
      port: 8000
```

#### Pydantic Models
- **PipelineConfig**: Top-level pipeline settings
- **SourceConfig**: Source specification with polymorphism (file, rtsp, custom)
- **WorkerConfig**: Worker specification with polymorphism (yolo, ocr, custom)
- **OutputConfig**: Output specification with polymorphism (log, websocket, api, kafka)

#### Features
- Type validation automatically
- Default values and optional fields
- Extensible for custom components
- YAML loading/saving convenience methods
- Environment variable support via Pydantic

**Design Pattern**: Data Transfer Object + Builder + Factory

**Example Usage:**
```python
from visionflow.config import PipelineConfig

config = PipelineConfig.from_yaml("config.yaml")
pipeline = StreamPipeline(config=config)
```

### 7. CLI Module - Command-Line Interface

**File**: `visionflow/cli/main.py` (200+ LOC)

Command-line interface for running pipelines and managing configurations.

#### Commands

**`visionflow init`**
- Initialize a new pipeline configuration file
- Interactive prompts for sources, workers, outputs
- Generates YAML config file

**`visionflow run <config.yaml>`**
- Execute a pipeline from configuration file
- Async execution with graceful shutdown
- Real-time logging output

**`visionflow version`**
- Display current VisionFlow version

#### Features
- Built with Click framework
- Clear help documentation
- Error handling and validation
- Integration with configuration system

**Design Pattern**: Command

**Example Usage:**
```bash
visionflow init --output my_pipeline.yaml
visionflow run my_pipeline.yaml
visionflow version
```

### 8. Utils Module - Helper Utilities

**File**: `visionflow/utils/` (60+ LOC)

Common utilities and helpers used across modules.

#### Features
- Logging configuration helpers
- Dictionary merging utilities
- Common constants
- Type helpers

## Data Flow Architecture

Complete flow from video input to external system output:

```
┌─────────────────────┐
│   Video Sources     │
│  • File             │
│  • RTSP Stream      │
│  • Custom Source    │
└──────────┬──────────┘
           │ Frame (numpy.ndarray)
           ▼
┌─────────────────────┐
│  Frame Distribution │
│  (StreamPipeline)   │
└──────────┬──────────┘
           │
    ┌──────┴──────┐
    ▼             ▼
┌──────────┐  ┌──────────┐
│ YOLOWorker   OCRWorker│ (Parallel)
└──────┬───┘  └────┬────┘
       │            │
   Detections   Text
       │            │
       └──────┬─────┘
              ▼
     ┌─────────────────┐
     │ EventGenerator  │
     │ (Results→Event) │
     └────────┬────────┘
              │ Event Object
              ▼
     ┌─────────────────┐
     │ EventEngine     │
     │ (Pub/Sub Hub)   │
     └────────┬────────┘
              │
    ┌─────────┼─────────────────┐
    ▼         ▼         ▼        ▼
 ┌─────┐ ┌────────┐ ┌────────┐ ┌────────┐
 │Log  │ │WebSocket│ │ REST   │ │ Kafka │
 │     │ │         │ │ API    │ │        │
 └─────┘ └────────┘ └────────┘ └────────┘
    │         │         │        │
    │         │         │        │
    └────────────┬──────────────┘
                 ▼
         ┌─────────────────┐
         │ External Systems│
         │  • Dashboards   │
         │  • Webhooks     │
         │  • Databases    │
         │  • Analytics    │
         └─────────────────┘
```

## Async/Await Design

VisionFlow leverages Python's `asyncio` throughout the entire framework for non-blocking, concurrent operation:

### Benefits
- **Non-blocking I/O**: Video reading, network operations don't block execution
- **Concurrent Processing**: Multiple workers process frames in parallel
- **Concurrent Event Handling**: Multiple handlers process events simultaneously
- **Efficient Resource Usage**: Single thread handles many concurrent operations

### Key Patterns
- **asyncio.gather()**: Run multiple async operations in parallel
- **async for**: Iterate through async iterators (frame streams)
- **async context managers**: Proper resource lifecycle management

### Thread Safety
- All components are designed for single-threaded async use
- Thread-safe communication via event queues
- No race conditions or deadlocks by design

## Error Handling & Resilience

Robust error handling at each layer ensures system stability:

### Error Isolation
- **Source Errors**: Logged, source disconnected, pipeline can retry
- **Worker Errors**: Caught per-worker, other workers continue processing
- **Output Errors**: Caught per-output, other outputs still function
- **Handler Errors**: Caught per-handler, other handlers still execute

### Logging
- Structured logging throughout with context
- Configurable log levels
- Error stack traces for debugging

### Graceful Shutdown
- Cleanup routines at each layer
- Resource release (file handles, connections, models)
- Wait for pending operations to complete

### Retry Logic
- Configurable connection retries for sources
- Backoff strategies for network operations
- Configurable failure thresholds

## Extension Points

### Custom Sources

Inherit from `BaseSource`:
```python
class CustomSource(BaseSource):
    async def connect(self):
        # Initialize connection
        pass
    
    async def read_frame(self):
        # Return numpy array or None
        return frame
```

### Custom Workers

Inherit from `BaseWorker`:
```python
class CustomWorker(BaseWorker):
    async def initialize(self):
        # Load model
        pass
    
    async def process_frame(self, frame):
        # Run inference
        return results
```

### Custom Outputs

Inherit from `BaseOutput`:
```python
class CustomOutput(BaseOutput):
    async def start(self):
        # Initialize
        self.is_running = True
    
    async def send_event(self, event):
        # Process event
        pass
```

### Custom Event Generators

Register with `EventGenerator`:
```python
def custom_generator(data, source_id):
    return [Event(...) for item in data]

event_gen.register_generator("custom", custom_generator)
```

## Type Safety

VisionFlow uses type hints throughout for:
- Static type checking with mypy
- IDE autocompletion
- Better documentation
- Easier debugging

## Testing Strategy

- **Unit Tests**: Individual component testing
- **Integration Tests**: Component interaction testing
- **Mock Objects**: Replacing external dependencies

Structure:
```
tests/
├── test_events.py       # Event system tests
├── test_pipeline.py     # Pipeline integration tests
├── fixtures/            # Test fixtures and mocks
└── conftest.py          # Pytest configuration
```

## Performance Considerations

1. **Frame Rate Control**: Sources respect configured FPS
2. **Worker Pool**: Parallel processing for multiple models
3. **Event Batching**: Can aggregate events before distribution
4. **Memory Management**: Old events are cleared from REST API buffer
5. **Async I/O**: Non-blocking throughout for efficiency

## Deployment

### Standalone
```python
python -m visionflow run config.yaml
```

### As Library
```python
from visionflow import StreamPipeline
pipeline = StreamPipeline(...)
await pipeline.run()
```

### Container
```dockerfile
FROM python:3.10
RUN pip install visionflow[yolo,ocr,kafka]
COPY config.yaml .
CMD ["visionflow", "run", "config.yaml"]
```
