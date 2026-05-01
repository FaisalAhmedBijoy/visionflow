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


class EventEngine:
    """
    Event engine that manages event handlers and emits events.

    Supports async handlers and one-time listeners.
    """

    def __init__(self) -> None:
        """Initialize the event engine."""
        self._handlers: Dict[str, List[Callable[[Any], Awaitable[None]]]] = {}
        self._once_handlers: Dict[str, Set[Callable[[Any], Awaitable[None]]]] = {}

    def on(self, event_type: str, handler: Callable[[Any], Awaitable[None]]) -> None:
        """
        Register an event handler for a specific event type.

        Args:
            event_type: Type of event to listen for
            handler: Async function that handles the event
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug(f"Handler registered for event type: {event_type}")

    def once(self, event_type: str, handler: Callable[[Any], Awaitable[None]]) -> None:
        """
        Register a one-time event handler.

        Args:
            event_type: Type of event to listen for
            handler: Async function that handles the event (called once)
        """
        if event_type not in self._once_handlers:
            self._once_handlers[event_type] = set()
        self._once_handlers[event_type].add(handler)
        logger.debug(f"One-time handler registered for event type: {event_type}")

    def off(self, event_type: str, handler: Callable[[Any], Awaitable[None]]) -> None:
        """
        Unregister an event handler.

        Args:
            event_type: Type of event
            handler: Handler to remove
        """
        if event_type in self._handlers:
            self._handlers[event_type] = [
                h for h in self._handlers[event_type] if h != handler
            ]

    async def emit(self, event: Event) -> None:
        """
        Emit an event to all registered handlers.

        Args:
            event: Event to emit
        """
        event_type = event.event_type
        logger.debug(f"Emitting event: {event_type}")

        # Gather all handlers
        handlers: List[Callable[[Any], Awaitable[None]]] = []

        # Regular handlers
        if event_type in self._handlers:
            handlers.extend(self._handlers[event_type])

        # Once handlers
        if event_type in self._once_handlers:
            handlers.extend(self._once_handlers[event_type])

        # Call all handlers concurrently
        if handlers:
            try:
                await asyncio.gather(*[handler(event) for handler in handlers])
            except Exception as e:
                logger.error(f"Error in event handler: {e}", exc_info=True)

        # Remove once handlers
        if event_type in self._once_handlers:
            self._once_handlers[event_type].clear()

    def clear(self, event_type: str | None = None) -> None:
        """
        Clear handlers for an event type or all events.

        Args:
            event_type: Specific event type to clear, or None to clear all
        """
        if event_type is None:
            self._handlers.clear()
            self._once_handlers.clear()
            logger.debug("All handlers cleared")
        else:
            self._handlers.pop(event_type, None)
            self._once_handlers.pop(event_type, None)
            logger.debug(f"Handlers cleared for event type: {event_type}")
