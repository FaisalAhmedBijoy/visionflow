"""
Worker pool for parallel frame processing.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from visionflow.processing.base import BaseWorker

logger = logging.getLogger(__name__)


class WorkerPool:
    """
    Async worker pool for parallel frame processing.

    Manages multiple workers and distributes frames for processing.
    """

    def __init__(self, workers: List[BaseWorker]) -> None:
        """
        Initialize worker pool.

        Args:
            workers: List of worker instances
        """
        self.workers = workers
        self.is_running = False
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def start(self) -> None:
        """Start all workers."""
        if self.is_running:
            self._logger.warning("Worker pool already running")
            return

        try:
            await asyncio.gather(*[worker.start() for worker in self.workers])
            self.is_running = True
            self._logger.info(f"Worker pool started ({len(self.workers)} workers)")
        except Exception as e:
            self._logger.error(f"Error starting worker pool: {e}", exc_info=True)
            raise

    async def stop(self) -> None:
        """Stop all workers."""
        if not self.is_running:
            return

        try:
            await asyncio.gather(*[worker.stop() for worker in self.workers])
            self.is_running = False
            self._logger.info("Worker pool stopped")
        except Exception as e:
            self._logger.error(f"Error stopping worker pool: {e}", exc_info=True)
            raise

    async def process_frame(self, frame: Any) -> Dict[str, Dict[str, Any]]:
        """
        Process frame through all workers.

        Args:
            frame: Input frame (numpy array)

        Returns:
            Dictionary mapping worker_id to processing results
        """
        if not self.is_running:
            raise RuntimeError("Worker pool is not running")

        try:
            # Process frame with all workers in parallel
            results = await asyncio.gather(
                *[worker.process_frame(frame) for worker in self.workers],
                return_exceptions=True,
            )

            # Collect results by worker ID
            processed = {}
            for worker, result in zip(self.workers, results):
                if isinstance(result, Exception):
                    self._logger.error(
                        f"Worker {worker.worker_id} error: {result}", exc_info=result
                    )
                    processed[worker.worker_id] = {"error": str(result)}
                else:
                    processed[worker.worker_id] = result

            return processed

        except Exception as e:
            self._logger.error(f"Error processing frame in pool: {e}", exc_info=True)
            raise

    def add_worker(self, worker: BaseWorker) -> None:
        """
        Add a worker to the pool.

        Args:
            worker: Worker instance to add
        """
        self.workers.append(worker)
        self._logger.debug(f"Worker {worker.worker_id} added to pool")

    def remove_worker(self, worker_id: str) -> None:
        """
        Remove a worker from the pool.

        Args:
            worker_id: ID of worker to remove
        """
        self.workers = [w for w in self.workers if w.worker_id != worker_id]
        self._logger.debug(f"Worker {worker_id} removed from pool")
