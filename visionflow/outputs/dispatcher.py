"""
Output dispatcher for routing events to multiple outputs.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, List

from visionflow.outputs.base import BaseOutput

if TYPE_CHECKING:
    from visionflow.events.event import Event

logger = logging.getLogger(__name__)


class OutputDispatcher:
    """
    Dispatches events to multiple output handlers.

    Routes events to REST API, WebSocket, Kafka, logging, etc.
    """

    def __init__(self, outputs: List[BaseOutput] | None = None) -> None:
        """
        Initialize output dispatcher.

        Args:
            outputs: List of output handlers
        """
        self.outputs = outputs or []
        self.is_running = False
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def start(self) -> None:
        """Start all output handlers."""
        if self.is_running:
            self._logger.warning("Output dispatcher already running")
            return

        try:
            await asyncio.gather(*[output.start() for output in self.outputs])
            self.is_running = True
            self._logger.info(f"Output dispatcher started ({len(self.outputs)} outputs)")
        except Exception as e:
            self._logger.error(f"Error starting output dispatcher: {e}", exc_info=True)
            raise

    async def stop(self) -> None:
        """Stop all output handlers."""
        if not self.is_running:
            return

        try:
            await asyncio.gather(*[output.stop() for output in self.outputs])
            self.is_running = False
            self._logger.info("Output dispatcher stopped")
        except Exception as e:
            self._logger.error(f"Error stopping output dispatcher: {e}", exc_info=True)
            raise

    async def dispatch(self, event: Event) -> None:
        """
        Dispatch event to all output handlers.

        Args:
            event: Event to dispatch
        """
        if not self.is_running:
            return

        # Send to all outputs in parallel
        await asyncio.gather(
            *[output.send_event(event) for output in self.outputs], return_exceptions=True
        )

    def add_output(self, output: BaseOutput) -> None:
        """
        Add an output handler.

        Args:
            output: Output handler to add
        """
        self.outputs.append(output)
        self._logger.debug(f"Output {output.output_id} added")

    def remove_output(self, output_id: str) -> None:
        """
        Remove an output handler.

        Args:
            output_id: ID of output to remove
        """
        self.outputs = [o for o in self.outputs if o.output_id != output_id]
        self._logger.debug(f"Output {output_id} removed")
