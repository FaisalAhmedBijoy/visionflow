# VisionFlow Architecture

## Overview

VisionFlow is built on clean architecture principles with strict separation of concerns. Each layer is independently testable and replaceable.

## Layered Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     User Application                     │
├─────────────────────────────────────────────────────────┤
│                  StreamPipeline (Orchestrator)           │
├──────────────────┬──────────────────┬──────────────────┤
│  Ingestion       │   Processing     │   Output         │
│  ┌────────────┐  │  ┌──────────────┐ │  ┌────────────┐ │
│  │ RTSP       │  │  │ YOLO Worker  │ │  │ REST API   │ │
│  │ File       │  │  │ OCR Worker   │ │  │ WebSocket  │ │
│  │ WebRTC     │  │  │ Worker Pool  │ │  │ Kafka      │ │
│  │ (Custom)   │  │  │ (Custom)     │ │  │ Logging    │ │
│  └────────────┘  │  └──────────────┘ │  │ (Custom)   │ │
│                  │                    │  └────────────┘ │
└──────────────────┴──────────────────┴──────────────────┘
├─────────────────────────────────────────────────────────┤
│  Events System (Event, EventEngine, EventGenerator)     │
├─────────────────────────────────────────────────────────┤
│  Configuration (YAML/Pydantic)                          │
├─────────────────────────────────────────────────────────┤
│  CLI & Utilities                                        │
└─────────────────────────────────────────────────────────┘
```

## Core Components

### 1. StreamPipeline (Orchestrator)

The main coordinator that brings all components together.

**Responsibilities:**
- Initialize and manage all sources, workers, and outputs
- Register event handlers
- Coordinate frame ingestion, processing, and distribution
- Manage lifecycle (start/stop)

**Design Pattern:** Facade + Factory

```python
pipeline = StreamPipeline()
pipeline.add_source(RTSPSource(...))
pipeline.add_output(LogOutput())

@pipeline.on_event("detection")
async def handler(event):
    ...

await pipeline.run()
```

### 2. Event System

Three main classes working together:

#### Event
- Immutable data structure
- Contains: type, source_id, timestamp, data, metadata, event_id
- Serializable to dict/JSON

#### EventEngine  
- Async event bus with handler registration
- Supports regular and one-time listeners
- Emits events to all registered handlers

#### EventGenerator
- Converts inference results (YOLO output, OCR text) into Event objects
- Customizable via registration pattern
- Pre-built generators for YOLO and OCR

**Design Pattern:** Observer + Factory

### 3. Ingestion Layer

Base class: `BaseSource`

Implementations:
- **RTSPSource**: OpenCV-based RTSP streaming
- **FileSource**: Local video file playback
- **WebRTCSource**: (Future) LiveKit WebRTC

**Key Features:**
- Non-blocking async frame reading
- Frame rate control
- Graceful error handling
- Connection lifecycle management

**Design Pattern:** Template Method + Strategy

### 4. Processing Layer

Base class: `BaseWorker`

Implementations:
- **YOLOWorker**: Ultralytics YOLO v8
- **OCRWorker**: Tesseract-based OCR
- **WorkerPool**: Async parallel execution

**WorkerPool Features:**
- Concurrent processing with asyncio
- Error isolation per worker
- Results aggregation
- Dynamic worker management

**Design Pattern:** Template Method + Object Pool

### 5. Output Layer

Base class: `BaseOutput`

Implementations:
- **LogOutput**: Python logging
- **WebSocketOutput**: Real-time WebSocket broadcast
- **RestAPIOutput**: FastAPI endpoints
- **KafkaOutput**: Kafka topic publishing
- **OutputDispatcher**: Routes to multiple outputs

**Design Pattern:** Strategy + Composite

### 6. Configuration System

**Two-tier approach:**
1. **YAML Configuration Files**: User-friendly format
2. **Pydantic Models**: Type-safe parsing and validation

**Models:**
- `PipelineConfig`: Top-level configuration
- `SourceConfig`: Source specification
- `WorkerConfig`: Worker specification  
- `OutputConfig`: Output specification

**Design Pattern:** Builder + Data Transfer Object

### 7. CLI

**Commands:**
- `visionflow init`: Initialize new config
- `visionflow run`: Execute pipeline from config
- `visionflow version`: Show version

**Design Pattern:** Command

## Data Flow

```
Video Frames
     ↓
[Ingestion Sources]
     ↓
Frame Queue
     ↓
[Worker Pool] (Parallel Processing)
     ↓
Results (Detections, OCR, etc.)
     ↓
[Event Generator] (Convert to Events)
     ↓
[Event Engine] (Fan-out to handlers)
     ↓
Application Handlers + Output Dispatch
     ↓
[Output Handlers] (REST API, WebSocket, Kafka, Log)
     ↓
External Systems
```

## Async Design

VisionFlow uses Python's `asyncio` throughout for:
- Non-blocking I/O (video reading, network)
- Concurrent frame processing (worker pool)
- Concurrent event handler execution
- Concurrent output distribution

**Key Pattern:** Gather multiple async operations with `asyncio.gather()`

## Error Handling Strategy

1. **Source Errors**: Logged and source is stopped
2. **Worker Errors**: Caught and reported, doesn't stop pipeline
3. **Output Errors**: Caught and logged, doesn't affect other outputs
4. **Handler Errors**: Caught and logged, doesn't stop other handlers

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
