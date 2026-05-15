"""
Event middleware and filtering support for VisionFlow pipelines.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Awaitable, Callable, List, Optional

if TYPE_CHECKING:
    from visionflow.events.event import Event

logger = logging.getLogger(__name__)

# Type alias for a middleware function
MiddlewareFn = Callable[["Event"], Awaitable[Optional["Event"]]]


class EventMiddleware:
    """
    Plugin-style middleware chain for transforming or filtering events.

    Middleware functions receive an event and return either:
    - A (possibly modified) event to continue the chain
    - ``None`` to drop the event (stop propagation)

    Middleware is applied in registration order before events reach outputs.

    Example::

        middleware = EventMiddleware()

        @middleware.use
        async def add_server_timestamp(event):
            from datetime import datetime
            event.metadata["processed_at"] = datetime.utcnow().isoformat()
            return event

        @middleware.use
        async def drop_low_confidence(event):
            conf = event.data.get("confidence", 1.0)
            return event if conf >= 0.5 else None   # drop if below 50%

        # Apply middleware to an event
        result = await middleware.process(event)
        if result is not None:
            await output.send_event(result)
    """

    def __init__(self) -> None:
        self._chain: List[MiddlewareFn] = []

    def use(self, fn: MiddlewareFn) -> MiddlewareFn:
        """
        Register a middleware function (also usable as a decorator).

        Args:
            fn: Async callable ``(Event) -> Optional[Event]``

        Returns:
            The same function (decorator pattern)
        """
        self._chain.append(fn)
        logger.debug(f"Middleware registered: {fn.__name__!r}")
        return fn

    async def process(self, event: "Event") -> Optional["Event"]:
        """
        Pass an event through the entire middleware chain.

        Args:
            event: Incoming event

        Returns:
            Transformed event, or ``None`` if dropped by a middleware function
        """
        current: Optional["Event"] = event
        for fn in self._chain:
            if current is None:
                return None
            try:
                current = await fn(current)
            except Exception as e:
                logger.error(f"Exception in middleware {fn.__name__!r}: {e}", exc_info=True)
                return None
        return current

    @property
    def length(self) -> int:
        """Number of registered middleware functions."""
        return len(self._chain)

    def clear(self) -> None:
        """Remove all registered middleware functions."""
        self._chain.clear()

    def __repr__(self) -> str:
        names = [f.__name__ for f in self._chain]
        return f"EventMiddleware(chain={names})"


class ConfidenceFilter:
    """
    Event middleware that drops detection events below a confidence threshold.

    Only events whose ``data["confidence"]`` field is **greater than or equal to**
    ``min_confidence`` pass through. Events without a ``confidence`` field are
    always passed through unchanged.

    Example::

        # Drop any YOLO/OCR event below 60% confidence
        filt = ConfidenceFilter(min_confidence=0.6)
        middleware = EventMiddleware()
        middleware.use(filt.apply)

    Args:
        min_confidence: Minimum required confidence in [0, 1] (or [0, 100] for OCR)
        event_types: Restrict filtering to these event types only.
                     If empty, the filter applies to all events.
    """

    def __init__(
        self,
        min_confidence: float = 0.5,
        event_types: Optional[List[str]] = None,
    ) -> None:
        self.min_confidence = min_confidence
        self.event_types: List[str] = event_types or []

    async def apply(self, event: "Event") -> Optional["Event"]:
        """
        Middleware function — drop the event if confidence is below threshold.

        Returns:
            The event unchanged if it passes, or ``None`` if it is filtered out.
        """
        # If event_types is set, only apply to matching types
        if self.event_types and event.event_type not in self.event_types:
            return event

        confidence: Any = event.data.get("confidence")
        if confidence is None:
            return event  # no confidence field — always pass

        if float(confidence) < self.min_confidence:
            logger.debug(
                f"Event {event.event_type!r} dropped: "
                f"confidence {confidence:.3f} < {self.min_confidence:.3f}"
            )
            return None

        return event

    def __repr__(self) -> str:
        return (
            f"ConfidenceFilter(min_confidence={self.min_confidence}, "
            f"event_types={self.event_types!r})"
        )
