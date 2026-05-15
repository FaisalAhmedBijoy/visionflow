"""
Tests for VisionFlow PipelineMetrics.
"""

from __future__ import annotations

import time

from visionflow.utils.metrics import PipelineMetrics, WorkerMetrics


class TestWorkerMetrics:
    def test_initial_state(self) -> None:
        wm = WorkerMetrics(worker_id="w1")
        assert wm.total_frames == 0
        assert wm.mean_latency_ms == 0.0
        assert wm.error_count == 0

    def test_record_single_sample(self) -> None:
        wm = WorkerMetrics(worker_id="w1")
        wm.record(100.0)
        assert wm.total_frames == 1
        assert wm.mean_latency_ms == 100.0
        assert wm.recent_mean_latency_ms == 100.0

    def test_mean_across_samples(self) -> None:
        wm = WorkerMetrics(worker_id="w1")
        wm.record(100.0)
        wm.record(200.0)
        assert wm.mean_latency_ms == 150.0

    def test_error_counter(self) -> None:
        wm = WorkerMetrics(worker_id="w1")
        wm.record_error()
        wm.record_error()
        assert wm.error_count == 2

    def test_to_dict(self) -> None:
        wm = WorkerMetrics(worker_id="w1")
        wm.record(50.0)
        d = wm.to_dict()
        assert d["worker_id"] == "w1"
        assert d["total_frames"] == 1
        assert d["mean_latency_ms"] == 50.0


class TestPipelineMetrics:
    def test_initial_uptime_is_zero(self) -> None:
        m = PipelineMetrics()
        assert m.uptime_seconds == 0.0

    def test_uptime_increases_after_start(self) -> None:
        m = PipelineMetrics()
        m.start()
        time.sleep(0.05)
        assert m.uptime_seconds >= 0.04

    def test_record_frame(self) -> None:
        m = PipelineMetrics()
        m.start()
        m.record_frame("cam1")
        m.record_frame("cam1")
        assert m._total_frames == 2

    def test_fps_returns_zero_with_single_frame(self) -> None:
        m = PipelineMetrics()
        m.start()
        m.record_frame("cam1")
        assert m.fps("cam1") == 0.0

    def test_fps_with_multiple_frames(self) -> None:
        m = PipelineMetrics()
        m.start()
        for _ in range(5):
            m.record_frame("cam1")
            time.sleep(0.01)
        fps = m.fps("cam1")
        assert fps > 0

    def test_record_event(self) -> None:
        m = PipelineMetrics()
        m.start()
        m.record_event("person_detected")
        m.record_event("person_detected")
        m.record_event("car_detected")
        assert m._total_events == 3
        assert m._event_counts["person_detected"] == 2

    def test_record_worker_latency(self) -> None:
        m = PipelineMetrics()
        m.record_worker_latency("yolo", 45.0)
        m.record_worker_latency("yolo", 55.0)
        assert m._workers["yolo"].total_frames == 2
        assert m._workers["yolo"].mean_latency_ms == 50.0

    def test_record_worker_error(self) -> None:
        m = PipelineMetrics()
        m.record_worker_error("yolo")
        assert m._workers["yolo"].error_count == 1

    def test_snapshot_structure(self, metrics: PipelineMetrics) -> None:
        metrics.record_frame("cam1")
        metrics.record_event("person_detected")
        metrics.record_worker_latency("yolo", 30.0)

        snap = metrics.snapshot()
        assert "uptime_seconds" in snap
        assert "total_frames" in snap
        assert "aggregate_fps" in snap
        assert "source_fps" in snap
        assert "total_events" in snap
        assert "events_per_second" in snap
        assert "event_type_counts" in snap
        assert "workers" in snap
        assert snap["total_frames"] == 1
        assert snap["total_events"] == 1

    def test_reset_clears_counters(self, metrics: PipelineMetrics) -> None:
        metrics.record_frame("cam1")
        metrics.record_event("test")
        metrics.reset()
        assert metrics._total_frames == 0
        assert metrics._total_events == 0
        assert len(metrics._workers) == 0

    def test_repr(self, metrics: PipelineMetrics) -> None:
        r = repr(metrics)
        assert "PipelineMetrics" in r
        assert "frames" in r
