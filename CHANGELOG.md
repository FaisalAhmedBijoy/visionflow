# Changelog

All notable changes to VisionFlow are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
VisionFlow uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.0] — 2026-05-10

### Added

#### New Sources
- **`WebcamSource`** — USB/built-in camera ingestion via `cv2.VideoCapture(device_index)`.
  Supports resolution and FPS configuration. Available as `visionflow.ingestion.WebcamSource`.

#### New Outputs
- **`FileOutput`** — Append events to a rotating JSONL file. Supports configurable
  size-based rotation (`max_bytes`). Available as `visionflow.outputs.FileOutput`.
- **`MQTTOutput`** — Publish events to an MQTT broker with per-event-type sub-topics,
  QoS control, and optional authentication. Requires `pip install visionflow[mqtt]`.

#### New Processing
- **`EventMiddleware`** — Plugin-style async middleware chain. Middleware functions
  can transform or drop events before they reach output handlers.
  Use `pipeline.middleware.use(fn)` or the `@middleware.use` decorator.
- **`ConfidenceFilter`** — Pre-built middleware that drops detection/OCR events
  below a minimum confidence threshold. Optionally scoped to specific event types.

#### New Utilities
- **`PipelineMetrics`** — Real-time performance monitoring:
  - Per-source FPS (rolling window)
  - Aggregate pipeline FPS
  - Events per second
  - Per-worker mean and rolling latency
  - JSON-serializable `snapshot()` method
  - Accessible via `pipeline.metrics`

#### Pipeline Enhancements
- **Async context manager** — `async with StreamPipeline() as pipeline:` ensures
  resources are always cleaned up, even on exceptions.
- **`pipeline.health_check()`** — Returns structured JSON-compatible dict:
  pipeline status, uptime, per-source/worker/output running state, metrics snapshot.
- **Fluent API** — `add_source()` and `add_output()` now return `self` for chaining:
  `pipeline.add_source(s1).add_source(s2).add_output(log)`
- **`name` parameter** — `StreamPipeline(name="My Pipeline")` for log identification.
- **Middleware integration** — Events pass through `pipeline.middleware` before
  being dispatched to outputs.
- **Metrics integration** — Frames, events, and worker latencies are recorded
  automatically on every `process_frame()` call.

#### Event Engine Enhancements
- **Wildcard handlers** — `@pipeline.on_event("*")` now correctly receives every
  event emitted by the pipeline.
- **Per-handler exception isolation** — One handler crashing no longer silences
  other handlers. Each exception is logged individually.
- **`handler_count` property** — Total registered persistent handlers.

#### CLI Enhancements
- **`visionflow validate <config>`** — Validates a YAML config file without
  starting the pipeline. Exits with code 1 on errors.
- **`visionflow info`** — Prints Python version, platform, and installed
  dependency status (opencv, ultralytics, pytesseract, kafka, paho, etc.).
- **`visionflow init --template`** — Three starter templates: `basic`, `yolo`,
  `multi`. Example: `visionflow init config.yaml --template yolo`.
- **`--log-file`** flag on `visionflow run` — Duplicate logs to a file.
- **REST API, WebSocket, Kafka, MQTT, File** output types now handled correctly
  in `visionflow run`. Previously, only `log` was wired up.
- **`webcam` source type** now supported in YAML config.

#### REST API Output Enhancements (`RestAPIOutput`)
- **`GET /events/filter?event_type=<type>`** — Filter buffered events by type.
- **`GET /stats`** — Aggregate counts per event type and buffer occupancy.
- **`GET /events/{id}`** — Returns HTTP 404 (was incorrectly 200) when not found.
- **Paginated `/events`** — `?limit=` and `?offset=` query parameters.
- **CORS middleware** — Cross-origin requests now allowed.
- **`max_events` parameter** — Configurable event buffer size (default 1000).
- Internal buffer changed from `list` to `collections.deque` for O(1) eviction.

#### RTSP Source Enhancements (`RTSPSource`)
- **Automatic reconnection** — Exponential back-off retry on stream failure.
  Configurable via `max_retries` and `retry_delay` parameters.

#### Test Suite
- `tests/conftest.py` — Shared pytest fixtures (events, engine, pipeline, mocks).
- `tests/test_sources.py` — `BaseSource`, `FileSource`, `WebcamSource` tests.
- `tests/test_workers.py` — `BaseWorker`, `WorkerPool`, `EventMiddleware`,
  `ConfidenceFilter` tests.
- `tests/test_outputs.py` — `LogOutput`, `FileOutput`, `OutputDispatcher` tests.
- `tests/test_config.py` — Config loading, validation, round-trip, error cases.
- `tests/test_metrics.py` — `PipelineMetrics` and `WorkerMetrics` tests.

### Fixed

- **`pyproject.toml`** — `[tool.setuptools]` now uses `packages.find` to correctly
  include all subpackages. Previously, only the top-level `visionflow` package was
  installed, leaving `visionflow.core`, `visionflow.events`, etc. missing.
- **`YOLOWorker`** — Fixed broken inheritance: removed redundant `__init__` field
  redefinitions; now correctly calls `super().__init__()`.
- **`OCRWorker`** — Fixed broken inheritance (same as YOLOWorker). Fixed
  `confidence` always returning `0.0` — now computes mean word confidence from
  Tesseract's `conf` column. Added `words` and `word_confidences` to output dict.
- **`EventEngine.emit()`** — Handler exceptions now caught per-handler with
  individual logging instead of silencing all remaining handlers.
- **`RestAPIOutput.get_event()`** — Returns HTTP 404 (was HTTP 200) when the
  event ID is not found.
- **`RTSPSource.read_frame()`** — Return type corrected from `Optional[object]`
  to `Optional[np.ndarray]`.
- **`PipelineConfig`** — Migrated from deprecated Pydantic v2 inner `Config`
  class to `model_config = SettingsConfigDict(...)`.
- **`cli/main.py`** — `rest_api`, `websocket`, `kafka` output types were silently
  skipped. All output types are now wired up correctly.

### Changed

- **Version bump** `0.1.0` → `0.2.0`.
- `pytest` moved from `dependencies` to `[project.optional-dependencies.dev]`.
  It is a development tool, not a runtime dependency.
- `click` added as a core dependency (was an implicit transitive requirement).
- `mqtt` added as a new optional extra: `pip install visionflow[mqtt]`.
- `all` extra added: `pip install visionflow[all]` installs YOLO, OCR, Kafka, MQTT.
- `pyproject.toml` classifiers updated: `Development Status :: 4 - Beta`.
- `[project.urls]` section added with Homepage, Repository, Bug Tracker, Changelog.
- All `__init__.py` module docstrings improved.
- Log format changed to include bracketed level: `%(asctime)s [%(levelname)s] …`.

### Deprecated

- Nothing deprecated in this release.

### Removed

- Nothing removed in this release.

---

## [0.1.0] — 2026-04-01

### Added

- Initial release.
- `StreamPipeline` — core pipeline orchestrator.
- `EventEngine`, `EventGenerator`, `Event` — event system.
- `BaseSource`, `RTSPSource`, `FileSource` — video ingestion.
- `BaseWorker`, `YOLOWorker`, `OCRWorker`, `WorkerPool` — AI processing.
- `BaseOutput`, `LogOutput`, `WebSocketOutput`, `RestAPIOutput`, `KafkaOutput` — outputs.
- `PipelineConfig` with YAML loading via `load_config()`.
- `visionflow run` and `visionflow init` CLI commands.
- `tests/test_events.py` and `tests/test_pipeline.py`.

---

[0.2.0]: https://github.com/FaisalAhmedBijoy/visionflow/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/FaisalAhmedBijoy/visionflow/releases/tag/v0.1.0
