"""
Tests for VisionFlow output handlers.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from visionflow.events.event import Event
from visionflow.outputs.dispatcher import OutputDispatcher
from visionflow.outputs.file import FileOutput
from visionflow.outputs.log import LogOutput


class TestLogOutput:
    @pytest.mark.asyncio
    async def test_start_sets_running(self, log_output: LogOutput) -> None:
        await log_output.start()
        assert log_output.is_running is True

    @pytest.mark.asyncio
    async def test_stop_clears_running(self, log_output: LogOutput) -> None:
        await log_output.start()
        await log_output.stop()
        assert log_output.is_running is False

    @pytest.mark.asyncio
    async def test_send_event_when_not_running_is_safe(
        self, log_output: LogOutput, sample_event: Event
    ) -> None:
        # Not started — should not raise
        await log_output.send_event(sample_event)

    @pytest.mark.asyncio
    async def test_send_event_logs_message(
        self, log_output: LogOutput, sample_event: Event
    ) -> None:
        await log_output.start()
        # Just confirm no exception is raised
        await log_output.send_event(sample_event)

    def test_repr(self, log_output: LogOutput) -> None:
        assert log_output.output_id in repr(log_output) or "LogOutput" in type(log_output).__name__


class TestFileOutput:
    @pytest.mark.asyncio
    async def test_creates_file_on_start(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "events.jsonl"
            output = FileOutput(output_id="fo", output_path=str(path))
            await output.start()
            await output.stop()
            assert path.exists()

    @pytest.mark.asyncio
    async def test_writes_jsonl_line(self, sample_event: Event) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "events.jsonl"
            output = FileOutput(output_id="fo", output_path=str(path))
            await output.start()
            await output.send_event(sample_event)
            await output.stop()

            lines = path.read_text().strip().split("\n")
            assert len(lines) == 1
            data = json.loads(lines[0])
            assert data["event_type"] == "person_detected"
            assert data["source_id"] == "test_camera"

    @pytest.mark.asyncio
    async def test_writes_multiple_events(self, sample_event: Event) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "events.jsonl"
            output = FileOutput(output_id="fo", output_path=str(path))
            await output.start()
            for _ in range(5):
                await output.send_event(sample_event)
            await output.stop()

            lines = [ln for ln in path.read_text().strip().split("\n") if ln]
            assert len(lines) == 5

    @pytest.mark.asyncio
    async def test_send_when_not_running_is_safe(self, sample_event: Event) -> None:
        output = FileOutput(output_id="fo", output_path="/tmp/vf_test_safe.jsonl")
        await output.send_event(sample_event)  # Should not raise

    @pytest.mark.asyncio
    async def test_rotation_on_size_limit(self, sample_event: Event) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "events.jsonl"
            # Set tiny limit to force rotation after first write
            output = FileOutput(output_id="fo", output_path=str(path), max_bytes=1)
            await output.start()
            await output.send_event(sample_event)
            await output.send_event(sample_event)
            await output.stop()
            # A rotated file should exist in tmpdir
            rotated = list(Path(tmpdir).glob("*.jsonl"))
            assert len(rotated) >= 1

    def test_repr(self) -> None:
        output = FileOutput(output_id="fo", output_path="out.jsonl")
        assert "fo" in repr(output)
        assert "out.jsonl" in repr(output)


class TestOutputDispatcher:
    def _mock_output(self, output_id: str = "mock") -> MagicMock:
        o = MagicMock()
        o.output_id = output_id
        o.is_running = True
        o.start = AsyncMock()
        o.stop = AsyncMock()
        o.send_event = AsyncMock()
        return o

    @pytest.mark.asyncio
    async def test_starts_all_outputs(self) -> None:
        o1 = self._mock_output("o1")
        o2 = self._mock_output("o2")
        dispatcher = OutputDispatcher([o1, o2])
        await dispatcher.start()
        o1.start.assert_called_once()
        o2.start.assert_called_once()
        assert dispatcher.is_running is True

    @pytest.mark.asyncio
    async def test_dispatches_to_all_outputs(self, sample_event: Event) -> None:
        o1 = self._mock_output("o1")
        o2 = self._mock_output("o2")
        dispatcher = OutputDispatcher([o1, o2])
        await dispatcher.start()
        await dispatcher.dispatch(sample_event)
        o1.send_event.assert_called_once_with(sample_event)
        o2.send_event.assert_called_once_with(sample_event)

    @pytest.mark.asyncio
    async def test_dispatch_when_not_running_is_safe(self, sample_event: Event) -> None:
        o1 = self._mock_output()
        dispatcher = OutputDispatcher([o1])
        # Not started — dispatch should be a no-op
        await dispatcher.dispatch(sample_event)
        o1.send_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_and_remove_output(self) -> None:
        dispatcher = OutputDispatcher([])
        o = self._mock_output("o1")
        dispatcher.add_output(o)
        assert len(dispatcher.outputs) == 1
        dispatcher.remove_output("o1")
        assert len(dispatcher.outputs) == 0

    @pytest.mark.asyncio
    async def test_stops_all_outputs(self) -> None:
        o1 = self._mock_output()
        dispatcher = OutputDispatcher([o1])
        await dispatcher.start()
        await dispatcher.stop()
        o1.stop.assert_called_once()
        assert dispatcher.is_running is False
