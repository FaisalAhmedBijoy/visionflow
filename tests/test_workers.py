"""
Tests for VisionFlow processing workers, pool, and middleware.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from visionflow.events.event import Event
from visionflow.processing.base import BaseWorker
from visionflow.processing.middleware import ConfidenceFilter, EventMiddleware
from visionflow.processing.pool import WorkerPool


class _StubWorker(BaseWorker):
    def __init__(self, worker_id: str = "stub", should_fail: bool = False) -> None:
        super().__init__(worker_id=worker_id, model_name="stub_model")
        self.initialized = False
        self.cleaned = False
        self.should_fail = should_fail

    async def initialize(self) -> None:
        if self.should_fail:
            raise RuntimeError("Initialization failed")
        self.initialized = True

    async def cleanup(self) -> None:
        self.cleaned = True

    async def process_frame(self, frame: object) -> dict:
        return {"stub": True, "worker_id": self.worker_id}


class TestBaseWorker:
    @pytest.mark.asyncio
    async def test_start_calls_initialize(self) -> None:
        worker = _StubWorker("w1")
        await worker.start()
        assert worker.initialized is True
        assert worker.is_running is True

    @pytest.mark.asyncio
    async def test_stop_calls_cleanup(self) -> None:
        worker = _StubWorker("w1")
        await worker.start()
        await worker.stop()
        assert worker.cleaned is True
        assert worker.is_running is False

    @pytest.mark.asyncio
    async def test_double_start_is_idempotent(self) -> None:
        worker = _StubWorker("w1")
        await worker.start()
        await worker.start()
        assert worker.is_running is True

    @pytest.mark.asyncio
    async def test_start_failure_propagates(self) -> None:
        worker = _StubWorker("w1", should_fail=True)
        with pytest.raises(RuntimeError, match="Initialization failed"):
            await worker.start()
        assert worker.is_running is False

    @pytest.mark.asyncio
    async def test_stop_when_not_running_is_safe(self) -> None:
        worker = _StubWorker("w1")
        await worker.stop()

    def test_repr(self) -> None:
        worker = _StubWorker("my_worker")
        assert "my_worker" in repr(worker)
        assert "stub_model" in repr(worker)


class TestWorkerPool:
    def _mock_worker(self, worker_id: str, result: dict) -> MagicMock:
        w = MagicMock()
        w.worker_id = worker_id
        w.is_running = True
        w.start = AsyncMock()
        w.stop = AsyncMock()
        w.process_frame = AsyncMock(return_value=result)
        return w

    @pytest.mark.asyncio
    async def test_starts_all_workers(self) -> None:
        w1 = self._mock_worker("w1", {})
        w2 = self._mock_worker("w2", {})
        pool = WorkerPool([w1, w2])
        await pool.start()
        w1.start.assert_called_once()
        w2.start.assert_called_once()
        assert pool.is_running is True

    @pytest.mark.asyncio
    async def test_stops_all_workers(self) -> None:
        w1 = self._mock_worker("w1", {})
        pool = WorkerPool([w1])
        await pool.start()
        await pool.stop()
        w1.stop.assert_called_once()
        assert pool.is_running is False

    @pytest.mark.asyncio
    async def test_process_frame_collects_results(self) -> None:
        w1 = self._mock_worker("w1", {"classes": ["car"]})
        w2 = self._mock_worker("w2", {"text": "hello"})
        pool = WorkerPool([w1, w2])
        await pool.start()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        results = await pool.process_frame(frame)
        assert results["w1"]["classes"] == ["car"]
        assert results["w2"]["text"] == "hello"

    @pytest.mark.asyncio
    async def test_worker_errors_are_captured(self) -> None:
        w1 = self._mock_worker("w1", {"ok": True})
        w2 = MagicMock()
        w2.worker_id = "w2"
        w2.is_running = True
        w2.start = AsyncMock()
        w2.process_frame = AsyncMock(side_effect=RuntimeError("GPU OOM"))
        pool = WorkerPool([w1, w2])
        await pool.start()
        results = await pool.process_frame(np.zeros((10, 10, 3), dtype=np.uint8))
        assert "error" in results["w2"]
        assert results["w1"]["ok"] is True

    @pytest.mark.asyncio
    async def test_add_and_remove_worker(self) -> None:
        pool = WorkerPool([])
        w = self._mock_worker("w1", {})
        pool.add_worker(w)
        assert len(pool.workers) == 1
        pool.remove_worker("w1")
        assert len(pool.workers) == 0

    @pytest.mark.asyncio
    async def test_raises_if_not_running(self) -> None:
        pool = WorkerPool([])
        with pytest.raises(RuntimeError, match="not running"):
            await pool.process_frame(np.zeros((10, 10, 3), dtype=np.uint8))


class TestEventMiddleware:
    @pytest.mark.asyncio
    async def test_empty_chain_passes_event(self, sample_event: Event) -> None:
        mw = EventMiddleware()
        result = await mw.process(sample_event)
        assert result is sample_event

    @pytest.mark.asyncio
    async def test_transform(self, sample_event: Event) -> None:
        mw = EventMiddleware()

        @mw.use
        async def add_tag(event: Event) -> Event:
            event.metadata["tagged"] = True
            return event

        result = await mw.process(sample_event)
        assert result is not None and result.metadata["tagged"] is True

    @pytest.mark.asyncio
    async def test_drop_returns_none(self, sample_event: Event) -> None:
        mw = EventMiddleware()

        @mw.use
        async def drop(event: Event) -> None:
            return None

        assert await mw.process(sample_event) is None

    @pytest.mark.asyncio
    async def test_exception_drops_event(self, sample_event: Event) -> None:
        mw = EventMiddleware()

        @mw.use
        async def boom(event: Event) -> None:
            raise ValueError("crash")

        assert await mw.process(sample_event) is None

    def test_length_and_clear(self) -> None:
        mw = EventMiddleware()
        mw.use(AsyncMock())
        mw.use(AsyncMock())
        assert mw.length == 2
        mw.clear()
        assert mw.length == 0


class TestConfidenceFilter:
    @pytest.mark.asyncio
    async def test_passes_high_confidence(self, sample_event: Event) -> None:
        filt = ConfidenceFilter(min_confidence=0.5)
        assert await filt.apply(sample_event) is sample_event

    @pytest.mark.asyncio
    async def test_drops_low_confidence(self, low_confidence_event: Event) -> None:
        filt = ConfidenceFilter(min_confidence=0.5)
        assert await filt.apply(low_confidence_event) is None

    @pytest.mark.asyncio
    async def test_passes_event_without_confidence(self) -> None:
        event = Event(event_type="custom", source_id="src", data={})
        filt = ConfidenceFilter(min_confidence=0.9)
        assert await filt.apply(event) is event

    @pytest.mark.asyncio
    async def test_event_type_scoping(self, low_confidence_event: Event) -> None:
        filt = ConfidenceFilter(min_confidence=0.9, event_types=["person_detected"])
        # low_confidence_event.event_type == "object_detected" — should pass through
        assert await filt.apply(low_confidence_event) is low_confidence_event

    def test_repr(self) -> None:
        filt = ConfidenceFilter(min_confidence=0.75)
        assert "0.75" in repr(filt)
