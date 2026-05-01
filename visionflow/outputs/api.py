"""
REST API output handler using FastAPI.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI
from uvicorn import Server, Config

from visionflow.outputs.base import BaseOutput

if TYPE_CHECKING:
    from visionflow.events.event import Event


class RestAPIOutput(BaseOutput):
    """
    REST API output handler using FastAPI.

    Provides HTTP endpoints for event queries and WebSocket for event streaming.
    """

    def __init__(
        self, output_id: str = "rest_api_output", host: str = "0.0.0.0", port: int = 8000
    ) -> None:
        """
        Initialize REST API output.

        Args:
            output_id: Unique identifier
            host: Host to bind to
            port: Port to listen on
        """
        super().__init__(output_id)
        self.host = host
        self.port = port
        self.app = FastAPI(title="VisionFlow API")
        self._server: Any = None
        self._server_task: Any = None
        self._events: list[Event] = []
        self._setup_routes()

    def _setup_routes(self) -> None:
        """Setup FastAPI routes."""

        @self.app.get("/health")
        async def health() -> dict[str, str]:
            """Health check endpoint."""
            return {"status": "ok"}

        @self.app.get("/events")
        async def get_events(limit: int = 100) -> dict[str, Any]:
            """Get recent events."""
            events = [e.to_dict() for e in self._events[-limit:]]
            return {"events": events, "count": len(events)}

        @self.app.get("/events/{event_id}")
        async def get_event(event_id: str) -> dict[str, Any]:
            """Get specific event by ID."""
            for event in self._events:
                if str(event.event_id) == event_id:
                    return event.to_dict()
            return {"error": "Event not found"}

    async def start(self) -> None:
        """Start the REST API server."""
        try:
            config = Config(app=self.app, host=self.host, port=self.port, log_level="warning")
            self._server = Server(config)

            # Run server in background task
            self._server_task = asyncio.create_task(self._server.serve())

            self.is_running = True
            self._logger.info(f"REST API server started on {self.host}:{self.port}")
        except Exception as e:
            self._logger.error(f"Error starting REST API server: {e}", exc_info=True)
            raise

    async def stop(self) -> None:
        """Stop the REST API server."""
        if self._server is not None:
            self._server.should_exit = True
            if self._server_task is not None:
                try:
                    await asyncio.wait_for(self._server_task, timeout=5.0)
                except asyncio.TimeoutError:
                    self._logger.warning("Server shutdown timeout")

        self.is_running = False
        self._logger.info("REST API server stopped")

    async def send_event(self, event: Event) -> None:
        """
        Store event and make it available via API.

        Args:
            event: Event to store
        """
        if not self.is_running:
            return

        # Keep last 1000 events in memory
        self._events.append(event)
        if len(self._events) > 1000:
            self._events.pop(0)
