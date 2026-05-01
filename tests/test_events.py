"""
Tests for VisionFlow event system.
"""

import asyncio
from datetime import datetime

import pytest

from visionflow.events.engine import EventEngine
from visionflow.events.event import Event
from visionflow.events.generator import EventGenerator


class TestEvent:
    """Tests for Event class."""

    def test_event_creation(self) -> None:
        """Test creating an event."""
        event = Event(
            event_type="test_event",
            source_id="source_1",
            data={"key": "value"},
        )

        assert event.event_type == "test_event"
        assert event.source_id == "source_1"
        assert event.data == {"key": "value"}
        assert event.timestamp is not None

    def test_event_to_dict(self) -> None:
        """Test converting event to dict."""
        event = Event(
            event_type="test_event",
            source_id="source_1",
            data={"key": "value"},
        )

        event_dict = event.to_dict()
        assert event_dict["event_type"] == "test_event"
        assert event_dict["source_id"] == "source_1"
        assert event_dict["data"] == {"key": "value"}
        assert "event_id" in event_dict
        assert "timestamp" in event_dict


class TestEventEngine:
    """Tests for EventEngine."""

    @pytest.mark.asyncio
    async def test_event_handler_registration(self) -> None:
        """Test registering event handlers."""
        engine = EventEngine()
        called = []

        async def handler(event: Event) -> None:
            called.append(event)

        engine.on("test_event", handler)
        assert "test_event" in engine._handlers
        assert handler in engine._handlers["test_event"]

    @pytest.mark.asyncio
    async def test_event_emission(self) -> None:
        """Test emitting events."""
        engine = EventEngine()
        received_events = []

        async def handler(event: Event) -> None:
            received_events.append(event)

        engine.on("test_event", handler)

        event = Event(
            event_type="test_event",
            source_id="source_1",
            data={"key": "value"},
        )
        await engine.emit(event)

        assert len(received_events) == 1
        assert received_events[0].event_type == "test_event"

    @pytest.mark.asyncio
    async def test_once_handler(self) -> None:
        """Test one-time handlers."""
        engine = EventEngine()
        call_count = 0

        async def handler(event: Event) -> None:
            nonlocal call_count
            call_count += 1

        engine.once("test_event", handler)

        event = Event(
            event_type="test_event",
            source_id="source_1",
            data={},
        )

        await engine.emit(event)
        await engine.emit(event)

        # Handler should only be called once
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_event_handler_removal(self) -> None:
        """Test removing event handlers."""
        engine = EventEngine()

        async def handler1(event: Event) -> None:
            pass

        async def handler2(event: Event) -> None:
            pass

        engine.on("test_event", handler1)
        engine.on("test_event", handler2)
        assert len(engine._handlers["test_event"]) == 2

        engine.off("test_event", handler1)
        assert len(engine._handlers["test_event"]) == 1
        assert handler2 in engine._handlers["test_event"]

    @pytest.mark.asyncio
    async def test_clear_handlers(self) -> None:
        """Test clearing handlers."""
        engine = EventEngine()

        async def handler(event: Event) -> None:
            pass

        engine.on("event1", handler)
        engine.on("event2", handler)

        engine.clear("event1")
        assert "event1" not in engine._handlers
        assert "event2" in engine._handlers

        engine.clear()
        assert len(engine._handlers) == 0


class TestEventGenerator:
    """Tests for EventGenerator."""

    def test_default_generation(self) -> None:
        """Test default event generation."""
        generator = EventGenerator()

        events = generator.generate(
            "custom_event",
            {"data": "value"},
            "source_1",
        )

        assert len(events) == 1
        assert events[0].event_type == "custom_event"
        assert events[0].source_id == "source_1"

    def test_yolo_generator(self) -> None:
        """Test YOLO event generator."""
        detections = {
            "classes": ["car", "person"],
            "confidences": [0.95, 0.87],
            "boxes": [[10, 20, 50, 80], [100, 100, 150, 200]],
        }

        events = EventGenerator.default_yolo_generator(detections, "camera_1")

        assert len(events) == 2
        assert events[0].event_type == "car_detected"
        assert events[0].data["confidence"] == 0.95
        assert events[1].event_type == "person_detected"
        assert events[1].data["confidence"] == 0.87

    def test_ocr_generator(self) -> None:
        """Test OCR event generator."""
        ocr_result = {
            "text": "Hello World",
            "confidence": 0.92,
            "boxes": [[10, 20, 50, 30]],
        }

        events = EventGenerator.default_ocr_generator(ocr_result, "camera_1")

        assert len(events) == 1
        assert events[0].event_type == "text_recognized"
        assert events[0].data["text"] == "Hello World"
        assert events[0].data["confidence"] == 0.92

    def test_custom_generator(self) -> None:
        """Test registering custom generator."""
        generator = EventGenerator()

        def custom_gen(data: dict[str, object], source_id: str) -> list[Event]:
            # Generate one event per item
            return [
                Event(event_type="item_detected", source_id=source_id, data={"item": item})
                for item in data.get("items", [])
            ]

        generator.register_generator("custom", custom_gen)

        events = generator.generate("custom", {"items": ["a", "b", "c"]}, "source_1")

        assert len(events) == 3
        assert all(e.event_type == "item_detected" for e in events)
