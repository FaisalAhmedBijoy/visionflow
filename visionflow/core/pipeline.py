"""
Core pipeline orchestrator for VisionFlow.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, List, Optional

from visionflow.events.engine import EventEngine
from visionflow.events.generator import EventGenerator
from visionflow.ingestion.base import BaseSource
from visionflow.outputs.dispatcher import OutputDispatcher
from visionflow.processing.middleware import EventMiddleware
from visionflow.processing.pool import WorkerPool
from visionflow.utils.metrics import PipelineMetrics

if TYPE_CHECKING:
    from visionflow.events.event import Event

logger = logging.getLogger(__name__)


class StreamPipeline:
    """
    Main orchestrator for a VisionFlow video AI pipeline.

    Manages the full lifecycle of:

    - **Ingestion** — reading frames from one or more video sources
    - **Processing** — running AI workers (YOLO, OCR, custom) on each frame
    - **Events** — generating and routing structured events from results
    - **Outputs** — dispatching events to REST API, WebSocket, Kafka, files, etc.

    Supports:

    - Async context manager (``async with``)
    - Built-in :class:`~visionflow.utils.metrics.PipelineMetrics`
    - :class:`~visionflow.processing.middleware.EventMiddleware` chain
    - Wildcard event handlers (``on_event("*")``)
    - ``health_check()`` for introspection

    Example::

        async with StreamPipeline() as pipeline:
            pipeline.add_source(FileSource("video.mp4"))
            pipeline.worker_pool = WorkerPool([YOLOWorker("det")])
            pipeline.add_output(LogOutput())

            @pipeline.on_event("person_detected")
            async def handler(event):
                print(event)

            await pipeline.run()

    Args:
        sources: Initial list of video sources
        workers: Initial list of processing workers
        outputs: Initial list of output handlers
        name: Human-readable pipeline name (used in logs and health checks)
    """

    def __init__(
        self,
        sources: Optional[List[BaseSource]] = None,
        workers: Optional[List[Any]] = None,
        outputs: Optional[List[Any]] = None,
        name: str = "VisionFlow Pipeline",
    ) -> None:
        self.name = name
        self.sources: List[BaseSource] = sources or []
        self.workers: Optional[List[Any]] = workers
        self.outputs_list: List[Any] = outputs or []

        # Core subsystems
        self.event_engine = EventEngine()
        self.event_generator = EventGenerator()
        self.worker_pool: Optional[WorkerPool] = WorkerPool(workers) if workers else None
        self.output_dispatcher = OutputDispatcher(self.outputs_list)
        self.middleware = EventMiddleware()
        self.metrics = PipelineMetrics()

        self.is_running: bool = False
        self._tasks: List[asyncio.Task[Any]] = []
        self._start_time: Optional[datetime] = None
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    # ------------------------------------------------------------------ #
    # Context Manager
    # ------------------------------------------------------------------ #

    async def __aenter__(self) -> "StreamPipeline":
        """Support ``async with StreamPipeline() as pipeline:``."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Ensure the pipeline is stopped when leaving the context."""
        if self.is_running:
            await self.stop()

    # ------------------------------------------------------------------ #
    # Event Handler Registration
    # ------------------------------------------------------------------ #

    def on_event(
        self, event_type: str
    ) -> Callable[[Callable[["Event"], Awaitable[None]]], Callable[["Event"], Awaitable[None]]]:
        """
        Decorator — register a persistent async event handler.

        Use ``"*"`` as ``event_type`` to receive every event.

        Example::

            @pipeline.on_event("vehicle_detected")
            async def handler(event):
                print(event.data)

        Args:
            event_type: Event type string, or ``"*"`` for all events
        """

        def decorator(
            handler: Callable[["Event"], Awaitable[None]],
        ) -> Callable[["Event"], Awaitable[None]]:
            self.event_engine.on(event_type, handler)
            return handler

        return decorator

    def once_event(
        self, event_type: str
    ) -> Callable[[Callable[["Event"], Awaitable[None]]], Callable[["Event"], Awaitable[None]]]:
        """
        Decorator — register a one-time event handler (auto-removed after first call).

        Args:
            event_type: Event type to listen for
        """

        def decorator(
            handler: Callable[["Event"], Awaitable[None]],
        ) -> Callable[["Event"], Awaitable[None]]:
            self.event_engine.once(event_type, handler)
            return handler

        return decorator

    # ------------------------------------------------------------------ #
    # Source / Output Management
    # ------------------------------------------------------------------ #

    def add_source(self, source: BaseSource) -> "StreamPipeline":
        """
        Add a video source to the pipeline.

        Returns self for fluent chaining::

            pipeline.add_source(src1).add_source(src2)
        """
        self.sources.append(source)
        self._logger.debug(f"Source added: {source.source_id!r}")
        return self

    def add_output(self, output: Any) -> "StreamPipeline":
        """
        Add an output handler to the pipeline.

        Returns self for fluent chaining.
        """
        self.output_dispatcher.add_output(output)
        self._logger.debug(f"Output added: {output.output_id!r}")
        return self

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    async def start(self) -> None:
        """Start all subsystems: sources, worker pool, and output handlers."""
        if self.is_running:
            self._logger.warning("Pipeline already running — ignoring start()")
            return

        self._logger.info(f"Starting pipeline: {self.name!r}")
        try:
            if self.sources:
                await asyncio.gather(*[source.start() for source in self.sources])
                self._logger.info(f"{len(self.sources)} source(s) started")

            if self.worker_pool is not None:
                await self.worker_pool.start()

            await self.output_dispatcher.start()

            self.is_running = True
            self._start_time = datetime.now(tz=timezone.utc)
            self.metrics.start()
            self._logger.info(f"Pipeline {self.name!r} started successfully")

        except Exception as e:
            self._logger.error(f"Error starting pipeline: {e}", exc_info=True)
            raise

    async def stop(self) -> None:
        """Gracefully stop all subsystems."""
        if not self.is_running:
            return

        self._logger.info(f"Stopping pipeline: {self.name!r}")
        try:
            for task in self._tasks:
                if not task.done():
                    task.cancel()

            if self._tasks:
                await asyncio.gather(*self._tasks, return_exceptions=True)

            if self.sources:
                await asyncio.gather(*[source.stop() for source in self.sources])

            if self.worker_pool is not None:
                await self.worker_pool.stop()

            await self.output_dispatcher.stop()

            self.is_running = False
            self._logger.info(f"Pipeline {self.name!r} stopped")

        except Exception as e:
            self._logger.error(f"Error stopping pipeline: {e}", exc_info=True)
            raise

    async def run(self) -> None:
        """
        Start the pipeline and block until all sources are exhausted or cancelled.

        Equivalent to::

            await pipeline.start()
            # ... processes all frames ...
            await pipeline.stop()
        """
        await self.start()

        try:
            self._tasks = [asyncio.create_task(self._run_source(source)) for source in self.sources]

            if self._tasks:
                await asyncio.gather(*self._tasks, return_exceptions=True)
            else:
                self._logger.info("No sources configured — pipeline is idle")
                while self.is_running:
                    await asyncio.sleep(1)

        except KeyboardInterrupt:
            self._logger.info("Pipeline interrupted by user")
        except Exception as e:
            self._logger.error(f"Error in pipeline run: {e}", exc_info=True)
            raise
        finally:
            await self.stop()

    # ------------------------------------------------------------------ #
    # Frame Processing
    # ------------------------------------------------------------------ #

    async def process_frame(self, frame: Any, source_id: str) -> None:
        """
        Process one frame through workers → event generation → middleware → outputs.

        Args:
            frame: Raw frame (numpy array in BGR format)
            source_id: ID of the source that produced this frame
        """
        if self.worker_pool is None:
            return

        self.metrics.record_frame(source_id)

        try:
            t0 = time.monotonic()
            worker_results = await self.worker_pool.process_frame(frame)
            latency_ms = (time.monotonic() - t0) * 1000

            for worker_id, results in worker_results.items():
                if "error" in results:
                    self._logger.error(f"Worker {worker_id!r} error: {results['error']}")
                    self.metrics.record_worker_error(worker_id)
                    continue

                self.metrics.record_worker_latency(worker_id, latency_ms)

                events = self.event_generator.generate(worker_id, results, source_id)

                for event in events:
                    # Pass through middleware chain first
                    filtered = await self.middleware.process(event)
                    if filtered is None:
                        continue

                    self.metrics.record_event(filtered.event_type)
                    await self.event_engine.emit(filtered)
                    await self.output_dispatcher.dispatch(filtered)

        except Exception as e:
            self._logger.error(f"Error processing frame from {source_id!r}: {e}", exc_info=True)

    async def _run_source(self, source: BaseSource) -> None:
        """Ingestion loop for a single source."""
        self._logger.info(f"Ingestion loop started for source: {source.source_id!r}")
        try:
            while self.is_running:
                frame = await source.read_frame()
                if frame is None:
                    self._logger.warning(
                        f"Source {source.source_id!r} returned None — stopping ingestion"
                    )
                    break
                await self.process_frame(frame, source.source_id)
        except asyncio.CancelledError:
            self._logger.debug(f"Ingestion task for {source.source_id!r} cancelled")
        except Exception as e:
            self._logger.error(
                f"Error in ingestion loop for {source.source_id!r}: {e}", exc_info=True
            )

    # ------------------------------------------------------------------ #
    # Introspection
    # ------------------------------------------------------------------ #

    def health_check(self) -> Dict[str, Any]:
        """
        Return a structured health/status snapshot of the pipeline.

        Returns:
            Dictionary with pipeline state, source/worker/output counts, uptime,
            and current metrics snapshot.
        """
        uptime: Optional[float] = None
        if self._start_time is not None:
            uptime = (datetime.now(tz=timezone.utc) - self._start_time).total_seconds()

        return {
            "name": self.name,
            "status": "running" if self.is_running else "stopped",
            "uptime_seconds": round(uptime, 1) if uptime is not None else None,
            "sources": [{"id": s.source_id, "running": s.is_running} for s in self.sources],
            "workers": (
                [{"id": w.worker_id, "running": w.is_running} for w in self.worker_pool.workers]
                if self.worker_pool
                else []
            ),
            "outputs": [
                {"id": o.output_id, "running": o.is_running} for o in self.output_dispatcher.outputs
            ],
            "middleware_steps": self.middleware.length,
            "metrics": self.metrics.snapshot(),
        }

    def __repr__(self) -> str:
        return (
            f"StreamPipeline(name={self.name!r}, "
            f"sources={len(self.sources)}, "
            f"is_running={self.is_running})"
        )
