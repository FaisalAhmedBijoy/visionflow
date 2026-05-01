"""
Logging output handler.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from visionflow.outputs.base import BaseOutput

if TYPE_CHECKING:
    from visionflow.events.event import Event


class LogOutput(BaseOutput):
    """
    Logging output handler.

    Outputs events to Python logging system.
    """

    def __init__(self, output_id: str = "log_output", level: str = "INFO") -> None:
        """
        Initialize logging output.

        Args:
            output_id: Unique identifier
            level: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        super().__init__(output_id)
        self.level = getattr(logging, level.upper(), logging.INFO)

    async def start(self) -> None:
        """Start the logging output."""
        self.is_running = True
        self._logger.info("Log output started")

    async def stop(self) -> None:
        """Stop the logging output."""
        self.is_running = False
        self._logger.info("Log output stopped")

    async def send_event(self, event: Event) -> None:
        """
        Log an event.

        Args:
            event: Event to log
        """
        if not self.is_running:
            return

        log_message = json.dumps(event.to_dict(), indent=2, default=str)
        self._logger.log(self.level, f"Event: {log_message}")
