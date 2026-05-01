# VisionFlow System Diagram

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         User Application Layer                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  Pipeline = StreamPipeline()                                       │ │
│  │  @pipeline.on_event("detection")                                   │ │
│  │  async def handler(event): ...                                     │ │
│  │  await pipeline.run()                                              │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     StreamPipeline (Orchestrator)                       │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Manages:                                                        │   │
│  │ • Sources lifecycle           • Workers initialization         │   │
│  │ • Outputs coordination        • Event handling registration    │   │
│  │ • Frame processing loop       • Error handling                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
        │               │               │               │
        ▼               ▼               ▼               ▼
    ┌────────┐    ┌─────────┐    ┌────────┐    ┌──────────┐
    │Ingestion│   │Processing│   │Events  │    │Outputs  │
    │ Layer  │    │ Layer    │    │System  │    │ Layer   │
    └────────┘    └─────────┘    └────────┘    └──────────┘

### Ingestion Layer

    RTSPSource              FileSource           (Custom)
    │                       │                    │
    └───BaseSource──────────┴────────────────────┘
            │
            ├── connect()        ◄── OpenCV / File I/O
            ├── read_frame()     ◄── Async Frame Reading
            └── disconnect()     ◄── Cleanup

    Features:
    • Non-blocking I/O
    • Frame rate control
    • Error handling
    • Extensible architecture

### Processing Layer

    YOLOWorker              OCRWorker            (Custom)
    │                       │                    │
    └───BaseWorker──────────┴────────────────────┘
            │
            ├── initialize()     ◄── Model Loading
            ├── process_frame()  ◄── Inference
            └── cleanup()        ◄── Cleanup

    Grouped into:
    
    WorkerPool
    ├── Concurrent execution
    ├── Error isolation
    ├── Results aggregation
    └── Dynamic management

### Event System

    ┌──────────────┐
    │   Event      │  (Immutable dataclass)
    ├──────────────┤
    │ • event_type │
    │ • source_id  │
    │ • timestamp  │
    │ • data       │
    │ • event_id   │
    └──────────────┘
          │
          ├─ EventGenerator ──┐
          │   (Results→Events)│
          │                   ├─ default_yolo_generator()
          │                   ├─ default_ocr_generator()
          │                   └─ custom generators
          │
          ▼
    ┌──────────────────┐
    │  EventEngine     │  (Async Event Bus)
    ├──────────────────┤
    │ • on()           │
    │ • once()         │
    │ • off()          │
    │ • emit()         │
    │ • clear()        │
    └──────────────────┘
          │
          ▼
    Registered Handlers (async callbacks)
          │
          ├─ Application handlers
          └─ Output dispatcher

### Output Layer

    LogOutput           WebSocketOutput      RestAPIOutput
    │                   │                    │
    ├── Logging         ├── Broadcast        ├── FastAPI Server
    │   system          │   to clients       │   REST endpoints
    │                   │                    │   Event storage
    │
    KafkaOutput        (Custom)
    │                  │
    ├── Kafka topics   └─ Custom implementation
    │   Pub/Sub
    │
    All inherit from:
    └─ BaseOutput (start, stop, send_event)
            │
            ▼
    OutputDispatcher
    ├── Manages lifecycle
    ├── Routes events
    ├── Error handling
    └── Dynamic add/remove

## Data Flow Diagram

```
┌─────────────────┐
│  Video Source   │
│                 │
│ RTSP/File/etc   │
└────────┬────────┘
         │
         │ Frame (numpy array)
         ▼
┌──────────────────────────┐
│   StreamPipeline         │
│   ├─ Ingestion Loop      │
│   └─ async read_frame()  │
└──────────┬───────────────┘
           │
           │ Raw Frame
           ▼
┌──────────────────────────┐
│   WorkerPool             │
│   ├─ YOLOWorker         │
│   │  └─ Inference       │
│   └─ OCRWorker          │
│      └─ Text Extract    │
└──────────┬───────────────┘
           │
           │ {"classes": [...], "confidence": [...]}
           │ {"text": "...", "boxes": [...]}
           ▼
┌──────────────────────────┐
│   EventGenerator         │
│   (Results → Events)     │
└──────────┬───────────────┘
           │
           │ [Event, Event, Event, ...]
           ▼
┌──────────────────────────┐
│   EventEngine            │
│   ├─ Emit events        │
│   └─ Invoke handlers    │
└──────────┬───────────────┘
           │
           ├─────────────────────────────────────┐
           │                                     │
           ▼                                     ▼
    ┌──────────────────┐            ┌──────────────────────┐
    │ App Handlers     │            │ OutputDispatcher    │
    │ (@on_event)      │            │                    │
    │ • Print          │            ├─ LogOutput         │
    │ • Track stats    │            ├─ WebSocketOutput   │
    │ • Custom logic   │            ├─ RestAPIOutput     │
    └──────────────────┘            ├─ KafkaOutput       │
                                    └─ (Custom)          │
                                    │                    │
                                    └────────────────────┘
                                           │
                                           ├─ Logs
                                           ├─ WebSocket Clients
                                           ├─ REST Consumers
                                           ├─ Kafka Topics
                                           └─ Custom Systems
```

## Module Dependencies

```
visionflow/
│
├── __init__.py
│   └── Exports: StreamPipeline, Event, EventGenerator
│
├── core/
│   └── pipeline.py ────────┬─ imports from:
│                           ├─ events.engine
│                           ├─ events.generator
│                           ├─ ingestion.base
│                           ├─ processing.pool
│                           └─ outputs.dispatcher
│
├── events/
│   ├── event.py ──────── standalone
│   ├── engine.py ──────┬─ imports:
│   │                   └─ event.py
│   └── generator.py ───┬─ imports:
│                       └─ event.py
│
├── ingestion/
│   ├── base.py ──────── standalone
│   ├── rtsp.py ────────┬─ imports:
│   │                   └─ base.py
│   └── file.py ────────┬─ imports:
│                       └─ base.py
│
├── processing/
│   ├── base.py ──────── standalone
│   ├── yolo.py ────────┬─ imports:
│   │                   └─ base.py
│   ├── ocr.py ─────────┬─ imports:
│   │                   └─ base.py
│   └── pool.py ────────┬─ imports:
│                       └─ base.py
│
├── outputs/
│   ├── base.py ──────────── standalone
│   ├── log.py ────────┬─── imports:
│   │                  ├─── base.py
│   │                  └─── events.event
│   ├── websocket.py ──┬─── imports:
│   │                  ├─── base.py
│   │                  └─── events.event
│   ├── api.py ────────┬─── imports:
│   │                  ├─── base.py
│   │                  └─── events.event
│   ├── kafka.py ──────┬─── imports:
│   │                  ├─── base.py
│   │                  └─── events.event
│   └── dispatcher.py ─┬─── imports:
│                      ├─── base.py
│                      └─── events.event
│
├── config/
│   └── config.py ────────── standalone (pydantic models)
│
├── cli/
│   └── main.py ───────────┬─ imports:
│                          ├─ core.pipeline
│                          ├─ ingestion.*
│                          ├─ processing.*
│                          ├─ outputs.*
│                          └─ config.config
│
└── utils/
    └── __init__.py ──────── standalone utilities
```

## Async Execution Model

```
StreamPipeline.run()
│
├─ await pipeline.start()
│  ├─ await asyncio.gather(source.start() for source in sources)
│  ├─ await worker_pool.start()
│  └─ await output_dispatcher.start()
│
├─ for source in sources:
│  └─ create_task(_run_source(source))
│     │
│     └─ while pipeline.is_running:
│        ├─ frame = await source.read_frame()
│        └─ await process_frame(frame, source_id)
│           │
│           ├─ worker_results = await worker_pool.process_frame(frame)
│           │  │
│           │  └─ await asyncio.gather(
│           │       worker.process_frame() for worker in workers
│           │     )
│           │
│           ├─ for worker_id, results in worker_results.items():
│           │  ├─ events = event_generator.generate(...)
│           │  │
│           │  └─ for event in events:
│           │     ├─ await event_engine.emit(event)
│           │     │  │
│           │     │  └─ await asyncio.gather(
│           │     │       handler(event) for handler in handlers
│           │     │     )
│           │     │
│           │     └─ await output_dispatcher.dispatch(event)
│           │        │
│           │        └─ await asyncio.gather(
│           │             output.send_event(event) for output in outputs
│           │           )
│
└─ await pipeline.stop()
   ├─ cancel all tasks
   ├─ await source.stop()
   ├─ await worker_pool.stop()
   └─ await output_dispatcher.stop()
```

## Configuration Flow

```
User: visionflow run config.yaml
│
├─ load_config("config.yaml")
│  └─ Parse YAML → PipelineConfig (Pydantic)
│     └─ Validate types and structure
│
├─ Create StreamPipeline()
│
├─ For each SourceConfig:
│  └─ Create RTSPSource or FileSource
│     └─ pipeline.add_source()
│
├─ For each WorkerConfig:
│  └─ Create YOLOWorker or OCRWorker
│     └─ pipeline.worker_pool = WorkerPool(workers)
│
├─ For each OutputConfig:
│  └─ Create LogOutput, RestAPIOutput, etc.
│     └─ pipeline.add_output()
│
├─ Register event handlers
│
└─ await pipeline.run()
   └─ Full pipeline execution
```

## Error Handling Strategy

```
Pipeline Execution
│
├─ Source Error
│  └─ Log error → Stop source → Continue with other sources
│
├─ Worker Error (during inference)
│  └─ Log error → Skip event generation → Continue
│
├─ Event Handler Error
│  └─ Log error → Continue with other handlers
│
├─ Output Error
│  └─ Log error → Remove from dispatcher → Continue with others
│
└─ Pipeline Error
   └─ Log error → Cleanup and exit
```

This visual diagram provides complete understanding of VisionFlow's architecture!
