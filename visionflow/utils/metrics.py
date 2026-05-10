"""
Pipeline performance metrics collection and reporting.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Deque, Dict, Optional


@dataclass
class WorkerMetrics:
    """Per-worker latency and throughput metrics."""

    worker_id: str
    total_frames: int = 0
    total_latency_ms: float = 0.0
    error_count: int = 0
    _recent_latencies: Deque[float] = field(default_factory=lambda: deque(maxlen=100))

    @property
    def mean_latency_ms(self) -> float:
        if self.total_frames == 0:
            return 0.0
        return self.total_latency_ms / self.total_frames

    @property
    def recent_mean_latency_ms(self) -> float:
        if not self._recent_latencies:
            return 0.0
        return sum(self._recent_latencies) / len(self._recent_latencies)

    def record(self, latency_ms: float) -> None:
        self.total_frames += 1
        self.total_latency_ms += latency_ms
        self._recent_latencies.append(latency_ms)

    def record_error(self) -> None:
        self.error_count += 1

    def to_dict(self) -> Dict[str, object]:
        return {
            "worker_id": self.worker_id,
            "total_frames": self.total_frames,
            "error_count": self.error_count,
            "mean_latency_ms": round(self.mean_latency_ms, 2),
            "recent_mean_latency_ms": round(self.recent_mean_latency_ms, 2),
        }


class PipelineMetrics:
    """
    Real-time performance metrics for a VisionFlow pipeline.

    Tracks FPS per source, events/s, per-worker inference latency, and uptime.

    Example::

        metrics = PipelineMetrics()
        metrics.start()
        metrics.record_frame("cam1")
        metrics.record_event("person_detected")
        print(metrics.snapshot())
    """

    def __init__(self, fps_window: int = 100) -> None:
        self._fps_window = fps_window
        self._start_time: Optional[float] = None
        self._frame_timestamps: Dict[str, Deque[float]] = defaultdict(
            lambda: deque(maxlen=fps_window)
        )
        self._total_frames: int = 0
        self._event_timestamps: Deque[float] = deque(maxlen=fps_window)
        self._event_counts: Dict[str, int] = defaultdict(int)
        self._total_events: int = 0
        self._workers: Dict[str, WorkerMetrics] = {}

    def start(self) -> None:
        """Mark the pipeline start time."""
        self._start_time = time.monotonic()

    @property
    def uptime_seconds(self) -> float:
        if self._start_time is None:
            return 0.0
        return time.monotonic() - self._start_time

    def record_frame(self, source_id: str) -> None:
        now = time.monotonic()
        self._frame_timestamps[source_id].append(now)
        self._total_frames += 1

    def fps(self, source_id: Optional[str] = None) -> float:
        if source_id is not None:
            timestamps: Deque[float] = self._frame_timestamps.get(source_id, deque())
        else:
            all_ts = sorted(ts for deq in self._frame_timestamps.values() for ts in deq)
            timestamps = deque(all_ts, maxlen=self._fps_window)
        if len(timestamps) < 2:
            return 0.0
        elapsed = timestamps[-1] - timestamps[0]
        return (len(timestamps) - 1) / elapsed if elapsed > 0 else 0.0

    def record_event(self, event_type: str) -> None:
        self._event_timestamps.append(time.monotonic())
        self._event_counts[event_type] += 1
        self._total_events += 1

    @property
    def events_per_second(self) -> float:
        if len(self._event_timestamps) < 2:
            return 0.0
        elapsed = self._event_timestamps[-1] - self._event_timestamps[0]
        return (len(self._event_timestamps) - 1) / elapsed if elapsed > 0 else 0.0

    def record_worker_latency(self, worker_id: str, latency_ms: float) -> None:
        if worker_id not in self._workers:
            self._workers[worker_id] = WorkerMetrics(worker_id=worker_id)
        self._workers[worker_id].record(latency_ms)

    def record_worker_error(self, worker_id: str) -> None:
        if worker_id not in self._workers:
            self._workers[worker_id] = WorkerMetrics(worker_id=worker_id)
        self._workers[worker_id].record_error()

    def snapshot(self) -> Dict[str, object]:
        """Return a point-in-time snapshot of all metrics."""
        return {
            "uptime_seconds": round(self.uptime_seconds, 1),
            "total_frames": self._total_frames,
            "aggregate_fps": round(self.fps(), 2),
            "source_fps": {src: round(self.fps(src), 2) for src in self._frame_timestamps},
            "total_events": self._total_events,
            "events_per_second": round(self.events_per_second, 2),
            "event_type_counts": dict(self._event_counts),
            "workers": {wid: w.to_dict() for wid, w in self._workers.items()},
        }

    def reset(self) -> None:
        """Reset all counters."""
        self._frame_timestamps.clear()
        self._total_frames = 0
        self._event_timestamps.clear()
        self._event_counts.clear()
        self._total_events = 0
        self._workers.clear()

    def __repr__(self) -> str:
        return (
            f"PipelineMetrics(uptime={self.uptime_seconds:.1f}s, "
            f"frames={self._total_frames}, fps={self.fps():.1f}, "
            f"events={self._total_events})"
        )
