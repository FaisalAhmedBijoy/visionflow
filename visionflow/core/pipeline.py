"""
Core pipeline orchestrator.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, List, Optional

from visionflow.events.engine import EventEngine
from visionflow.events.generator import EventGenerator
from visionflow.ingestion.base import BaseSource
from visionflow.outputs.dispatcher import OutputDispatcher
from visionflow.processing.pool import WorkerPool

if TYPE_CHECKING:
    from visionflow.events.event import Event

logger = logging.getLogger(__name__)


class StreamPipeline:
    """
    Main orchestrator for the entire video processing pipeline.

    Manages:
    - Video source ingestion
    - Frame processing (AI models)
    - Event generation
    - Event distribution to outputs
    """

    def __init__(
        self,
        sources: List[BaseSource] | None = None,
        workers: List[Any] | None = None,
        outputs: List[Any] | None = None,
    ) -> None:
        """
        Initialize the pipeline.

        Args:
            sources: List of video sources
            workers: List of processing workers
            outputs: List of output handlers
        """
        self.sources = sources or []
        self.workers = workers
        self.outputs_list = outputs or []

        # Core components
        self.event_engine = EventEngine()
        self.event_generator = EventGenerator()
        self.worker_pool: Optional[WorkerPool] = None
        if workers:
            self.worker_pool = WorkerPool(workers)
        self.output_dispatcher = OutputDispatcher(self.outputs_list)

        self.is_running = False
        self._tasks: List[asyncio.Task[Any]] = []
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def on_event(self, event_type: str) -> Callable[[Callable[[Event], Awaitable[None]]], Callable[[Event], Awaitable[None]]]:
        """
        Decorator to register an event handler.

        Usage:
            @pipeline.on_event("vehicle_detected")
            async def handler(event):
                print(event)

        Args:
            event_type: Type of event to listen for

        Returns:
            Decorator function
        """

        def decorator(
            handler: Callable[[Event], Awaitable[None]],
        ) -> Callable[[Event], Awaitable[None]]:
            self.event_engine.on(event_type, handler)
            return handler

        return decorator

    def once_event(self, event_type: str) -> Callable[[Callable[[Event], Awaitable[None]]], Callable[[Event], Awaitable[None]]]:
        """
        Decorator to register a one-time event handler.

        Args:
            event_type: Type of event to listen for

        Returns:
            Decorator function
        """

        def decorator(
            handler: Callable[[Event], Awaitable[None]],
        ) -> Callable[[Event], Awaitable[None]]:
            self.event_engine.once(event_type, handler)
            return handler

        return decorator

    def add_source(self, source: BaseSource) -> None:
        """
        Add a video source to the pipeline.

        Args:
            source: Source instance
        """
        self.sources.append(source)
        self._logger.debug(f"Source {source.source_id} added")

    def add_output(self, output: Any) -> None:
        """
        Add an output handler to the pipeline.

        Args:
            output: Output instance
        """
        self.output_dispatcher.add_output(output)
        self._logger.debug(f"Output {output.output_id} added")

    async def start(self) -> None:
        """Start the pipeline."""
        if self.is_running:
            self._logger.warning("Pipeline already running")
            return

        try:
            self._logger.info("Starting pipeline...")

            # Start sources
            if self.sources:
                await asyncio.gather(*[source.start() for source in self.sources])
                self._logger.info(f"{len(self.sources)} source(s) started")

            # Start workers
            if self.worker_pool is not None:
                await self.worker_pool.start()

            # Start outputs
            await self.output_dispatcher.start()

            self.is_running = True
            self._logger.info("Pipeline started successfully")

        except Exception as e:
            self._logger.error(f"Error starting pipeline: {e}", exc_info=True)
            raise

    async def stop(self) -> None:
        """Stop the pipeline."""
        if not self.is_running:
            return

        try:
            self._logger.info("Stopping pipeline...")

            # Cancel all running tasks
            for task in self._tasks:
                if not task.done():
                    task.cancel()

            # Stop sources
            if self.sources:
                await asyncio.gather(*[source.stop() for source in self.sources])

            # Stop workers
            if self.worker_pool is not None:
                await self.worker_pool.stop()

            # Stop outputs
            await self.output_dispatcher.stop()

            self.is_running = False
            self._logger.info("Pipeline stopped")

        except Exception as e:
            self._logger.error(f"Error stopping pipeline: {e}", exc_info=True)
            raise

    async def process_frame(self, frame: Any, source_id: str) -> None:
        """
        Process a single frame through the pipeline.

        Args:
            frame: Input frame (numpy array)
            source_id: ID of source that provided frame
        """
        try:
            # Process with workers
            if self.worker_pool is None:
                return

            worker_results = await self.worker_pool.process_frame(frame)

            # Generate events from results
            for worker_id, results in worker_results.items():
                if "error" in results:
                    self._logger.error(f"Worker {worker_id} error: {results['error']}")
                    continue

                # Generate events based on worker type
                events = self.event_generator.generate(worker_id, results, source_id)

                # Emit each event
                for event in events:
                    await self.event_engine.emit(event)
                    await self.output_dispatcher.dispatch(event)

        except Exception as e:
            self._logger.error(f"Error processing frame: {e}", exc_info=True)

    async def _run_source(self, source: BaseSource) -> None:
        """
        Run ingestion loop for a single source.

        Args:
            source: Source to ingest from
        """
        self._logger.info(f"Starting ingestion loop for source: {source.source_id}")

        try:
            while self.is_running:
                frame = await source.read_frame()
                if frame is None:
                    self._logger.warning(f"Source {source.source_id} returned None, stopping")
                    break

                # Process frame
                await self.process_frame(frame, source.source_id)

        except asyncio.CancelledError:
            self._logger.debug(f"Source {source.source_id} ingestion cancelled")
        except Exception as e:
            self._logger.error(
                f"Error in ingestion loop for {source.source_id}: {e}", exc_info=True
            )

    async def run(self) -> None:
        """
        Run the pipeline (blocking).

        Starts all sources and processes frames until stopped.
        """
        await self.start()

        try:
            # Create tasks for each source
            self._tasks = [asyncio.create_task(self._run_source(source)) for source in self.sources]

            if self._tasks:
                # Wait for all tasks (will block until cancelled)
                await asyncio.gather(*self._tasks)
            else:
                # No sources, just keep running
                while self.is_running:
                    await asyncio.sleep(1)

        except KeyboardInterrupt:
            self._logger.info("Pipeline interrupted by user")
        except Exception as e:
            self._logger.error(f"Error in pipeline run: {e}", exc_info=True)
            raise
        finally:
            await self.stop()
