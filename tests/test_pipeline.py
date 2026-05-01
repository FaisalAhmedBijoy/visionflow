"""
Integration tests for VisionFlow pipeline.
"""

import asyncio

import pytest

from visionflow.core.pipeline import StreamPipeline
from visionflow.events.event import Event
from visionflow.outputs.log import LogOutput
from visionflow.processing.pool import WorkerPool


class TestStreamPipeline:
    """Tests for StreamPipeline."""

    def test_pipeline_creation(self) -> None:
        """Test creating a pipeline."""
        pipeline = StreamPipeline()

        assert pipeline.is_running is False
        assert len(pipeline.sources) == 0
        assert pipeline.event_engine is not None
        assert pipeline.output_dispatcher is not None

    @pytest.mark.asyncio
    async def test_event_handler_decorator(self) -> None:
        """Test event handler decorator."""
        pipeline = StreamPipeline()
        received_events = []

        @pipeline.on_event("test_event")
        async def handler(event: Event) -> None:
            received_events.append(event)

        # Manually emit event
        event = Event(event_type="test_event", source_id="test", data={})
        await pipeline.event_engine.emit(event)

        assert len(received_events) == 1

    @pytest.mark.asyncio
    async def test_once_event_decorator(self) -> None:
        """Test one-time event handler decorator."""
        pipeline = StreamPipeline()
        call_count = 0

        @pipeline.once_event("test_event")
        async def handler(event: Event) -> None:
            nonlocal call_count
            call_count += 1

        event = Event(event_type="test_event", source_id="test", data={})
        await pipeline.event_engine.emit(event)
        await pipeline.event_engine.emit(event)

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_add_output(self) -> None:
        """Test adding outputs to pipeline."""
        pipeline = StreamPipeline()
        output = LogOutput("test_output")

        pipeline.add_output(output)

        assert len(pipeline.output_dispatcher.outputs) == 1
        assert pipeline.output_dispatcher.outputs[0].output_id == "test_output"

    @pytest.mark.asyncio
    async def test_output_dispatch(self) -> None:
        """Test event dispatch to outputs."""
        pipeline = StreamPipeline()

        # Create a mock output that captures events
        class MockOutput:
            def __init__(self) -> None:
                self.output_id = "mock"
                self.is_running = True
                self.events: list[Event] = []

            async def start(self) -> None:
                pass

            async def stop(self) -> None:
                pass

            async def send_event(self, event: Event) -> None:
                self.events.append(event)

        mock_output = MockOutput()
        pipeline.output_dispatcher.outputs.append(mock_output)  # type: ignore

        await pipeline.output_dispatcher.start()

        event = Event(event_type="test", source_id="test", data={})
        await pipeline.output_dispatcher.dispatch(event)

        assert len(mock_output.events) == 1
        assert mock_output.events[0].event_type == "test"

        await pipeline.output_dispatcher.stop()
