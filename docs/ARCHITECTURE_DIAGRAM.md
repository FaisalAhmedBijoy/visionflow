# VisionFlow System Architecture Diagrams

## 1. High-Level Component Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     User Application Layer                        │
│  • Event handlers registration via decorators                    │
│  • Pipeline configuration and execution                          │
│  • Custom business logic for detections/results                  │
└──────────────────────────┬─────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│            StreamPipeline (Core Orchestrator)                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Responsibilities:                                        │   │
│  │ • Source lifecycle management (connect/disconnect)      │   │
│  │ • Worker initialization and execution                   │   │
│  │ • Output dispatcher coordination                        │   │
│  │ • Event handler registration and execution              │   │
│  │ • Main frame processing loop                            │   │
│  │ • Graceful shutdown on errors                           │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────┬──────────────┬──────────────┬──────────────┬──────────┘
           │              │              │              │
    ┌──────▼────────┬──────▼────────┬──────▼────────┬──────▼────────┐
    │              │              │              │              │
    ▼              ▼              ▼              ▼              ▼
┌────────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ Ingestion  │ │Processing│ │  Events  │ │Outputs   │ │Config &  │
│ Layer      │ │ Layer    │ │ System   │ │ Layer    │ │ CLI      │
└────────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘
```
## 2. Ingestion Layer Detail

```
BaseSource (Abstract Interface)
│
├─ initialize()       OpenCV/File I/O
├─ read_frame()       Async frame reading
└─ cleanup()          Resource cleanup

Concrete Implementations:
│
├─ RTSPSource
│  ├─ OpenCV video capture from RTSP URIs
│  ├─ Handles network streams
│  └─ Connection retry and error handling
│
├─ FileSource
│  ├─ OpenCV video capture from files
│  ├─ Local MP4, AVI, MOV, MKV support
│  └─ Frame-by-frame or streaming
│
└─ Custom Sources
   └─ Inherit from BaseSource for any media source
```

## 3. Processing Layer Detail

```
BaseWorker (Abstract Interface)
│
├─ initialize()       Load model/resources
├─ process_frame()    Run inference
└─ cleanup()          Release resources

Concrete Implementations:
│
├─ YOLOWorker
│  ├─ Ultralytics YOLO v8 object detection
│  ├─ Detects objects with bounding boxes
│  └─ Configurable model sizes (nano→xlarge)
│
├─ OCRWorker
│  ├─ Tesseract text recognition
│  ├─ Extracts text from frame regions
│  └─ Multi-language support
│
└─ Custom Workers
   └─ Inherit from BaseWorker for any ML model

WorkerPool Orchestration:
│
├─ Manages multiple workers
├─ Parallel frame processing
├─ Error isolation per worker
└─ Result aggregation
```

## 4. Event System Detail

```
Event (Immutable Dataclass)
├─ event_type      Type of event (detection, ocr_result, custom)
├─ source_id       Which source generated it
├─ timestamp       When event occurred
├─ data           Event payload
├─ metadata       Additional context
└─ event_id       Unique identifier

            ↓

EventGenerator (Factory)
├─ default_yolo_generator()      Convert detections → Event
├─ default_ocr_generator()       Convert text → Event
└─ register_generator()          Custom event types

            ↓

EventEngine (Async Pub/Sub Bus)
├─ on(event_type, handler)      Register listener
├─ once(event_type, handler)    One-time listener
├─ emit(event)                  Broadcast to handlers
└─ clear()                       Cleanup

            ↓

Handlers (Async Callbacks)
├─ Application handlers (@on_event decorator)
└─ Output dispatcher (multi-output routing)
```

## 5. Output Layer Detail

```
BaseOutput (Abstract Interface)
│
├─ start()          Initialize output
├─ send_event()     Process event
└─ stop()           Cleanup

Concrete Implementations:
│
├─ LogOutput
│  └─ Python logging framework
│
├─ WebSocketOutput
│  ├─ Real-time WebSocket broadcast
│  └─ Multiple client support
│
├─ RestAPIOutput
│  ├─ FastAPI server with endpoints
│  ├─ Event history storage
│  └─ Swagger documentation
│
├─ KafkaOutput
│  ├─ Apache Kafka topic publishing
│  └─ Enterprise streaming
│
└─ Custom Outputs
   └─ Inherit from BaseOutput

OutputDispatcher (Router):
├─ Manages multiple outputs
├─ Concurrent event dispatch
├─ Error isolation per output
└─ Dynamic add/remove of outputs
```

## 6. Complete Data Flow

```
┌─────────────────────────────────────┐
│  Video/Media Input                  │
│  • File (MP4, AVI, MOV)             │
│  • RTSP Stream (IP cameras)         │
│  • Custom Source                    │
└──────────────┬──────────────────────┘
               │ raw frame (numpy array, BGR)
               ▼
┌──────────────────────────────────────┐
│  StreamPipeline                      │
│  ├─ Coordinates all components      │
│  └─ Main event loop                 │
└──────────────┬──────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  Source.read_frame()                │
│  (Async frame acquisition)           │
└──────────────┬──────────────────────┘
               │ frame (H×W×3)
               ▼
┌──────────────────────────────────────┐
│  WorkerPool.process_frame()          │
│  (Parallel processing)               │
│  ├─ YOLOWorker → detections         │
│  ├─ OCRWorker → text                 │
│  └─ Custom → custom results          │
└──────────────┬──────────────────────┘
               │ {"yolo": [...], "ocr": [...]}
               ▼
┌──────────────────────────────────────┐
│  EventGenerator.generate_events()    │
│  (Convert results to events)         │
└──────────────┬──────────────────────┘
               │ [Event(...), Event(...), ...]
               ▼
┌──────────────────────────────────────┐
│  EventEngine.emit()                  │
│  (Async pub/sub broadcast)           │
└──────────┬──────────────────────┬────┘
           │                      │
    ┌──────▼──────────┐    ┌─────▼──────────────┐
    │ App Handlers    │    │ OutputDispatcher   │
    │                 │    │                    │
    │ @on_event       │    ├─ LogOutput        │
    │ • Custom logic  │    ├─ WebSocketOutput  │
    │ • Stats track   │    ├─ RestAPIOutput    │
    │ • Filtering     │    ├─ KafkaOutput      │
    └──────┬──────────┘    └─────┬──────────────┘
           │                      │
           │        ┌─────────────┼─────────────┐
           │        │             │             │
           ▼        ▼             ▼             ▼
      Application  Console   WebSocket      REST API
      Logic        Logs      Clients        Endpoints
                                │             │
                                └─────┬───────┘
                                      ▼
                            External Systems
                            • Dashboards
                            • Analytics
                            • Webhooks
                            • Databases
```

## 7. Module Dependencies

```
Dependency Graph (bottom → top):

events/
├── event.py                    (no dependencies)
├── engine.py → event.py
└── generator.py → event.py

ingestion/
├── base.py                     (no dependencies)
├── file.py → base.py
└── rtsp.py → base.py

processing/
├── base.py                     (no dependencies)
├── yolo.py → base.py
├── ocr.py → base.py
└── pool.py → base.py

outputs/
├── base.py                     (no dependencies)
├── log.py → base.py, event.py
├── websocket.py → base.py, event.py
├── api.py → base.py, event.py
├── kafka.py → base.py, event.py
└── dispatcher.py → base.py, event.py

config/
└── config.py                   (pydantic only)

core/
└── pipeline.py → events/*, ingestion/*, processing/*, outputs/*, config/

cli/
└── main.py → core/*, ingestion/*, processing/*, outputs/*, config/

Key Points:
✓ No circular dependencies
✓ Base classes have no dependencies
✓ Clear layering from bottom to top
✓ Easy to test in isolation
```

## 8. Async Execution Model

```
await pipeline.run()
│
├─ await _initialize()
│  ├─ await gather(source.connect() for each source)
│  ├─ await worker_pool.initialize()
│  └─ await output_dispatcher.start()
│
├─ for each source:
│  └─ create_task(_source_loop(source))
│
└─ while pipeline.is_running:
   │
   ├─ source.read_frame() → frame (or None at EOF)
   │
   ├─ worker_pool.process_frame(frame)
   │  │
   │  └─ gather(worker.process_frame(frame) for each worker)
   │     │
   │     ├─ YOLOWorker: detections
   │     ├─ OCRWorker: text
   │     └─ Custom: any results
   │
   ├─ event_generator.generate_events(results)
   │  │
   │  └─ [Event(...), Event(...), ...]
   │
   └─ for each event:
      │
      ├─ event_engine.emit(event)
      │  │
      │  └─ gather(handler(event) for each registered handler)
      │     │
      │     ├─ @on_event("detection") handlers
      │     ├─ @on_event("ocr_result") handlers
      │     └─ Output dispatcher
      │
      └─ output_dispatcher.dispatch(event)
         │
         └─ gather(output.send_event(event) for each output)
            │
            ├─ log.send_event()
            ├─ websocket.send_event()
            ├─ api.send_event()
            ├─ kafka.send_event()
            └─ custom.send_event()
```

## 9. Error Isolation Strategy

```
Pipeline Execution
│
├─ [Source Loop]
│  ├─ If source.read_frame() fails
│  │  └─ Log error, continue (frame = None, triggers EOF)
│  │
│  └─ If source connection lost
│     └─ Retry connection, log status
│
├─ [Worker Processing]
│  ├─ If worker.process_frame() raises exception
│  │  └─ Catch in try/except → Log → Continue
│  │     (Other workers still process)
│  │
│  └─ If worker.initialize() fails
│     └─ Mark worker as unavailable → Skip
│
├─ [Event Handling]
│  ├─ If handler(event) raises exception
│  │  └─ Catch → Log → Continue
│  │     (Other handlers still execute)
│  │
│  └─ If event_generator fails
│     └─ Log error → Skip event generation
│
├─ [Output Dispatch]
│  ├─ If output.send_event() raises exception
│  │  └─ Catch → Log → Continue
│  │     (Other outputs still process)
│  │
│  └─ If output.start() fails
│     └─ Mark as unavailable → Skip
│
└─ [Pipeline Shutdown]
   ├─ Graceful: Cancel tasks, cleanup resources
   └─ Ungraceful: Log error, forced cleanup
```

This visual diagram provides complete understanding of VisionFlow's architecture!
