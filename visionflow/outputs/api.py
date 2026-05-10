"""
REST API output handler using FastAPI.
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from typing import TYPE_CHECKING, Any, Deque, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from uvicorn import Config, Server

from visionflow.outputs.base import BaseOutput

if TYPE_CHECKING:
    from visionflow.events.event import Event

logger = logging.getLogger(__name__)


class RestAPIOutput(BaseOutput):
    """
    REST API output handler using FastAPI.

    Exposes an HTTP server with endpoints for querying events, health checks,
    and basic pipeline statistics.

    Endpoints:
        - ``GET /health``           — Liveness probe
        - ``GET /events``           — Paginated list of recent events
        - ``GET /events/{id}``      — Fetch a specific event by UUID
        - ``GET /events/filter``    — Filter events by type
        - ``GET /stats``            — Aggregate event statistics

    Example::

        output = RestAPIOutput(host="0.0.0.0", port=8000, max_events=500)
        pipeline.add_output(output)

    Args:
        output_id: Unique identifier for this output handler
        host: Bind address (default ``"0.0.0.0"``)
        port: TCP port (default ``8000``)
        max_events: Maximum number of events to retain in memory (default ``1000``)
    """

    def __init__(
        self,
        output_id: str = "rest_api_output",
        host: str = "0.0.0.0",
        port: int = 8000,
        max_events: int = 1000,
    ) -> None:
        super().__init__(output_id)
        self.host = host
        self.port = port
        self.max_events = max_events

        self.app = FastAPI(
            title="VisionFlow API",
            description="Real-time AI video stream event API",
            version="0.2.0",
        )
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["GET"],
            allow_headers=["*"],
        )

        self._server: Optional[Server] = None
        self._server_task: Optional[asyncio.Task[Any]] = None
        # Use a deque for O(1) eviction of oldest events
        self._events: Deque["Event"] = deque(maxlen=max_events)
        self._event_counts: Dict[str, int] = {}

        self._setup_routes()

    def _setup_routes(self) -> None:
        """Register all FastAPI route handlers."""

        @self.app.get("/health", tags=["System"])
        async def health() -> Dict[str, str]:
            """Liveness probe — returns ``{"status": "ok"}``."""
            return {"status": "ok", "output_id": self.output_id}

        @self.app.get("/stats", tags=["System"])
        async def stats() -> Dict[str, Any]:
            """Aggregate event statistics."""
            return {
                "total_events": sum(self._event_counts.values()),
                "buffered_events": len(self._events),
                "max_buffer": self.max_events,
                "event_type_counts": dict(self._event_counts),
            }

        @self.app.get("/events", tags=["Events"])
        async def get_events(
            limit: int = Query(default=100, ge=1, le=1000),
            offset: int = Query(default=0, ge=0),
        ) -> Dict[str, Any]:
            """
            Retrieve recent events (newest-first).

            Args:
                limit: Maximum number of events to return (1–1000)
                offset: Number of events to skip from the newest
            """
            event_list = list(self._events)
            event_list.reverse()  # newest first
            page = event_list[offset: offset + limit]
            return {
                "events": [e.to_dict() for e in page],
                "count": len(page),
                "total_buffered": len(self._events),
                "offset": offset,
                "limit": limit,
            }

        @self.app.get("/events/filter", tags=["Events"])
        async def filter_events(
            event_type: str = Query(..., description="Event type to filter by"),
            limit: int = Query(default=100, ge=1, le=1000),
        ) -> Dict[str, Any]:
            """Filter buffered events by event type."""
            matched = [
                e.to_dict()
                for e in self._events
                if e.event_type == event_type
            ]
            matched.reverse()
            page = matched[:limit]
            return {"events": page, "count": len(page), "event_type": event_type}

        @self.app.get("/events/{event_id}", tags=["Events"])
        async def get_event(event_id: str) -> Dict[str, Any]:
            """Retrieve a specific event by its UUID."""
            for event in self._events:
                if str(event.event_id) == event_id:
                    return event.to_dict()
            raise HTTPException(status_code=404, detail=f"Event '{event_id}' not found")

    async def start(self) -> None:
        """Start the REST API server as a background asyncio task."""
        if self.is_running:
            return

        try:
            config = Config(
                app=self.app,
                host=self.host,
                port=self.port,
                log_level="warning",
            )
            self._server = Server(config)
            self._server_task = asyncio.create_task(self._server.serve())
            self.is_running = True
            self._logger.info(f"REST API server started on http://{self.host}:{self.port}")
        except Exception as e:
            self._logger.error(f"Error starting REST API server: {e}", exc_info=True)
            raise

    async def stop(self) -> None:
        """Gracefully shut down the REST API server."""
        if self._server is not None:
            self._server.should_exit = True
            if self._server_task is not None:
                try:
                    await asyncio.wait_for(self._server_task, timeout=5.0)
                except asyncio.TimeoutError:
                    self._logger.warning("REST API server shutdown timed out; forcing exit")

        self.is_running = False
        self._logger.info("REST API server stopped")

    async def send_event(self, event: "Event") -> None:
        """
        Store an event in the circular in-memory buffer.

        Args:
            event: Incoming pipeline event
        """
        if not self.is_running:
            return

        self._events.append(event)
        self._event_counts[event.event_type] = (
            self._event_counts.get(event.event_type, 0) + 1
        )

    def __repr__(self) -> str:
        return (
            f"RestAPIOutput(output_id={self.output_id!r}, "
            f"host={self.host!r}, port={self.port}, "
            f"is_running={self.is_running})"
        )
