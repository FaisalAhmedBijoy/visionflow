"""
WebSocket output handler.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any, Dict, Optional, Set

from visionflow.outputs.base import BaseOutput

if TYPE_CHECKING:
    from visionflow.events.event import Event


class WebSocketOutput(BaseOutput):
    """
    WebSocket output handler.

    Manages WebSocket connections and broadcasts events to connected clients.
    """

    def __init__(self, output_id: str = "websocket_output") -> None:
        """
        Initialize WebSocket output.

        Args:
            output_id: Unique identifier
        """
        super().__init__(output_id)
        self.clients: Set[Any] = set()
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Start the WebSocket output."""
        self.is_running = True
        self._logger.info("WebSocket output started")

    async def stop(self) -> None:
        """Stop the WebSocket output."""
        self.is_running = False
        # Close all connections
        async with self._lock:
            self.clients.clear()
        self._logger.info("WebSocket output stopped")

    async def send_event(self, event: Event) -> None:
        """
        Broadcast event to all connected WebSocket clients.

        Args:
            event: Event to broadcast
        """
        if not self.is_running or not self.clients:
            return

        message = json.dumps(event.to_dict(), default=str)

        async with self._lock:
            # Broadcast to all clients
            for client in self.clients.copy():
                try:
                    await client.send_text(message)
                except Exception as e:
                    self._logger.error(f"Error sending to client: {e}")
                    self.clients.discard(client)

    async def add_client(self, client: Any) -> None:
        """
        Add a WebSocket client connection.

        Args:
            client: WebSocket connection object
        """
        async with self._lock:
            self.clients.add(client)
        self._logger.debug(f"WebSocket client added ({len(self.clients)} total)")

    async def remove_client(self, client: Any) -> None:
        """
        Remove a WebSocket client connection.

        Args:
            client: WebSocket connection object
        """
        async with self._lock:
            self.clients.discard(client)
        self._logger.debug(f"WebSocket client removed ({len(self.clients)} total)")
