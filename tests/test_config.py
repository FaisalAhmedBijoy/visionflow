"""
Tests for VisionFlow configuration loading and validation.
"""

from __future__ import annotations

import tempfile

import pytest

from visionflow.config.config import (
    OutputConfig,
    PipelineConfig,
    SourceConfig,
    WorkerConfig,
    load_config,
    save_config,
)

MINIMAL_YAML = """
name: Test Pipeline
sources:
  - id: cam1
    type: rtsp
    url: rtsp://example.com/stream
    fps: 25
"""

FULL_YAML = """
name: Full Pipeline
sources:
  - id: rtsp_cam
    type: rtsp
    url: rtsp://cam.local/stream
    fps: 30
  - id: vid_file
    type: file
    url: /data/video.mp4
    fps: 25
workers:
  - id: detector
    type: yolo
    model: yolov8n.pt
    enabled: true
  - id: ocr_reader
    type: ocr
    model: ""
    enabled: false
    config:
      engine: tesseract
outputs:
  - id: logger
    type: log
    enabled: true
  - id: api
    type: rest_api
    enabled: true
    config:
      host: 0.0.0.0
      port: 8000
log_level: DEBUG
debug: true
"""


class TestSourceConfig:
    def test_minimal_source(self) -> None:
        src = SourceConfig(id="cam1", type="rtsp", url="rtsp://x.com/s")
        assert src.fps == 30  # default

    def test_custom_fps(self) -> None:
        src = SourceConfig(id="cam1", type="file", url="video.mp4", fps=15)
        assert src.fps == 15


class TestWorkerConfig:
    def test_enabled_by_default(self) -> None:
        wc = WorkerConfig(id="w1", type="yolo", model="yolov8n.pt")
        assert wc.enabled is True

    def test_extra_config(self) -> None:
        wc = WorkerConfig(id="w1", type="ocr", model="", config={"engine": "tesseract"})
        assert wc.config["engine"] == "tesseract"


class TestOutputConfig:
    def test_enabled_by_default(self) -> None:
        oc = OutputConfig(id="o1", type="log")
        assert oc.enabled is True


class TestPipelineConfig:
    def test_default_name(self) -> None:
        config = PipelineConfig(sources=[])
        assert config.name == "VisionFlow Pipeline"

    def test_empty_workers_and_outputs(self) -> None:
        config = PipelineConfig(sources=[])
        assert config.workers == []
        assert config.outputs == []

    def test_log_level_default(self) -> None:
        config = PipelineConfig(sources=[])
        assert config.log_level == "INFO"


class TestLoadConfig:
    def test_load_minimal_yaml(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            f.write(MINIMAL_YAML)
            path = f.name

        config = load_config(path)
        assert config.name == "Test Pipeline"
        assert len(config.sources) == 1
        assert config.sources[0].id == "cam1"
        assert config.sources[0].fps == 25

    def test_load_full_yaml(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            f.write(FULL_YAML)
            path = f.name

        config = load_config(path)
        assert config.name == "Full Pipeline"
        assert len(config.sources) == 2
        assert len(config.workers) == 2
        assert len(config.outputs) == 2
        assert config.debug is True
        assert config.log_level == "DEBUG"

    def test_load_nonexistent_file_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/path/config.yaml")

    def test_load_invalid_yaml_raises(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            f.write("not: [valid: yaml: structure")
            path = f.name

        with pytest.raises(Exception):
            load_config(path)

    def test_load_non_mapping_yaml_raises(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            f.write("- item1\n- item2\n")
            path = f.name

        with pytest.raises(ValueError, match="YAML mapping"):
            load_config(path)


class TestSaveConfig:
    def test_round_trip(self) -> None:
        config = PipelineConfig(
            name="Round Trip Test",
            sources=[SourceConfig(id="s1", type="file", url="v.mp4", fps=30)],
            workers=[WorkerConfig(id="w1", type="yolo", model="yolov8n.pt")],
            outputs=[OutputConfig(id="o1", type="log")],
        )

        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            path = f.name

        save_config(config, path)
        loaded = load_config(path)

        assert loaded.name == config.name
        assert len(loaded.sources) == 1
        assert loaded.sources[0].id == "s1"
        assert len(loaded.workers) == 1
        assert loaded.workers[0].model == "yolov8n.pt"
