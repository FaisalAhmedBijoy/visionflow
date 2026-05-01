"""
Base output class for event distribution.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from visionflow.events.event import Event

logger = logging.getLogger(__name__)


class BaseOutput(ABC):
    """
    Abstract base class for event output handlers.

    Implementations: WebSocket, REST API, Kafka, logging, etc.
    """

    def __init__(self, output_id: str) -> None:
        """
        Initialize the output handler.

        Args:
            output_id: Unique identifier for this output
        """
        self.output_id = output_id
        self.is_running = False
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def start(self) -> None:
        """Start the output handler (e.g., start server, connect to Kafka)."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the output handler."""
        pass

    @abstractmethod
    async def send_event(self, event: Event) -> None:
        """
        Send an event to the output.

        Args:
            event: Event to send
        """
        pass
