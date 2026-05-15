"""
Event engine for managing event handlers and emitting events.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, List, Set

if TYPE_CHECKING:
    from visionflow.events.event import Event

logger = logging.getLogger(__name__)

# Special wildcard event type — handlers registered under this key receive ALL events
WILDCARD = "*"


class EventEngine:
    """
    Async event engine that manages handlers and emits events.

    Supports:
    - Persistent handlers (``on``)
    - One-time handlers (``once``)
    - Wildcard handlers (``on("*", handler)``) — called for every event
    - Safe concurrent dispatch: one handler's exception does not block others

    Example::

        engine = EventEngine()

        @engine.on("vehicle_detected")
        async def handle(event):
            print(event)

        await engine.emit(event)
    """

    def __init__(self) -> None:
        """Initialize the event engine."""
        self._handlers: Dict[str, List[Callable[[Any], Awaitable[None]]]] = {}
        self._once_handlers: Dict[str, Set[Callable[[Any], Awaitable[None]]]] = {}

    def on(self, event_type: str, handler: Callable[[Any], Awaitable[None]]) -> None:
        """
        Register a persistent event handler.

        Use ``"*"`` as ``event_type`` to receive every event regardless of type.

        Args:
            event_type: Event type to listen for, or ``"*"`` for all events
            handler: Async callable that accepts an :class:`~visionflow.events.event.Event`
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug(f"Handler registered for event type: {event_type!r}")

    def once(self, event_type: str, handler: Callable[[Any], Awaitable[None]]) -> None:
        """
        Register a one-time event handler (auto-removed after first call).

        Args:
            event_type: Event type to listen for
            handler: Async callable — called at most once
        """
        if event_type not in self._once_handlers:
            self._once_handlers[event_type] = set()
        self._once_handlers[event_type].add(handler)
        logger.debug(f"One-time handler registered for event type: {event_type!r}")

    def off(self, event_type: str, handler: Callable[[Any], Awaitable[None]]) -> None:
        """
        Unregister a persistent event handler.

        Args:
            event_type: Event type the handler was registered under
            handler: Handler to remove
        """
        if event_type in self._handlers:
            self._handlers[event_type] = [h for h in self._handlers[event_type] if h != handler]
            logger.debug(f"Handler removed for event type: {event_type!r}")

    async def emit(self, event: "Event") -> None:
        """
        Emit an event to all matching handlers concurrently.

        Handlers are invoked in three groups (all concurrently):
        1. Exact-match persistent handlers
        2. Exact-match one-time handlers (then removed)
        3. Wildcard (``"*"``) handlers

        Each handler's exception is caught individually so that one failing
        handler does not prevent others from running.

        Args:
            event: Event to dispatch
        """
        event_type = event.event_type
        logger.debug(f"Emitting event: {event_type!r}")

        # Collect all applicable handlers
        handlers: List[Callable[[Any], Awaitable[None]]] = []

        # Exact-match persistent handlers
        handlers.extend(self._handlers.get(event_type, []))

        # Exact-match one-time handlers
        once = self._once_handlers.get(event_type)
        if once:
            handlers.extend(once)

        # Wildcard handlers (skip if event_type is itself the wildcard)
        if event_type != WILDCARD:
            handlers.extend(self._handlers.get(WILDCARD, []))
            wildcard_once = self._once_handlers.get(WILDCARD)
            if wildcard_once:
                handlers.extend(wildcard_once)

        if not handlers:
            return

        # Dispatch concurrently — capture each result/exception individually
        results = await asyncio.gather(
            *[handler(event) for handler in handlers],
            return_exceptions=True,
        )

        for handler, result in zip(handlers, results):
            if isinstance(result, Exception):
                logger.error(
                    f"Exception in handler {handler!r} for event {event_type!r}: {result}",
                    exc_info=result,
                )

        # Remove one-time handlers AFTER dispatch
        if event_type in self._once_handlers:
            self._once_handlers[event_type].clear()
        if event_type != WILDCARD and WILDCARD in self._once_handlers:
            self._once_handlers[WILDCARD].clear()

    def clear(self, event_type: str | None = None) -> None:
        """
        Clear registered handlers.

        Args:
            event_type: Specific event type to clear, or ``None`` to clear all handlers
        """
        if event_type is None:
            self._handlers.clear()
            self._once_handlers.clear()
            logger.debug("All handlers cleared")
        else:
            self._handlers.pop(event_type, None)
            self._once_handlers.pop(event_type, None)
            logger.debug(f"Handlers cleared for event type: {event_type!r}")

    @property
    def handler_count(self) -> int:
        """Total number of registered persistent handlers across all event types."""
        return sum(len(h) for h in self._handlers.values())

    def __repr__(self) -> str:
        return (
            f"EventEngine(event_types={list(self._handlers.keys())}, "
            f"handler_count={self.handler_count})"
        )
