"""
Configuration management for VisionFlow pipelines.

Configurations can be loaded from YAML files or provided programmatically.
All models are validated with Pydantic v2.
"""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SourceConfig(BaseModel):
    """Configuration for a single video source."""

    id: str = Field(..., description="Unique source identifier")
    type: str = Field(..., description="Source type: 'rtsp', 'file', or 'webcam'")
    url: str = Field(..., description="Source URL or file path (or device index for webcam)")
    fps: int = Field(default=30, ge=1, le=120, description="Target frames per second")


class WorkerConfig(BaseModel):
    """Configuration for a single processing worker."""

    id: str = Field(..., description="Unique worker identifier")
    type: str = Field(..., description="Worker type: 'yolo' or 'ocr'")
    model: str = Field(default="", description="Model name or path")
    enabled: bool = Field(default=True, description="Whether to load this worker")
    config: Dict[str, Any] = Field(
        default_factory=dict, description="Worker-specific configuration options"
    )


class OutputConfig(BaseModel):
    """Configuration for a single output handler."""

    id: str = Field(..., description="Unique output identifier")
    type: str = Field(
        ..., description="Output type: 'log', 'file', 'websocket', 'rest_api', 'kafka', 'mqtt'"
    )
    enabled: bool = Field(default=True, description="Whether to activate this output")
    config: Dict[str, Any] = Field(
        default_factory=dict, description="Output-specific configuration options"
    )


class PipelineConfig(BaseSettings):
    """
    Root pipeline configuration.

    Can be populated from a YAML file via :func:`load_config` or from
    environment variables (prefixed with ``VISIONFLOW_``).

    Example YAML::

        name: "My Pipeline"
        sources:
          - id: cam1
            type: rtsp
            url: rtsp://camera.local/stream
            fps: 25
        workers:
          - id: detector
            type: yolo
            model: yolov8n.pt
        outputs:
          - id: logger
            type: log
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="VISIONFLOW_",
        case_sensitive=False,
        extra="ignore",
    )

    name: str = Field(default="VisionFlow Pipeline", description="Human-readable pipeline name")
    sources: List[SourceConfig] = Field(default_factory=list)
    workers: List[WorkerConfig] = Field(default_factory=list)
    outputs: List[OutputConfig] = Field(default_factory=list)
    log_level: str = Field(default="INFO", description="Logging level")
    debug: bool = Field(default=False, description="Enable debug mode")
    max_queue_size: int = Field(
        default=100, description="Maximum number of frames to buffer in the processing queue"
    )


def load_config(config_path: str) -> PipelineConfig:
    """
    Load a :class:`PipelineConfig` from a YAML file.

    Args:
        config_path: Path to a ``.yaml`` or ``.yml`` configuration file

    Returns:
        Validated :class:`PipelineConfig` instance

    Raises:
        FileNotFoundError: If the file does not exist
        ValueError: If the YAML is malformed or fails Pydantic validation
    """
    import yaml

    with open(config_path, "r", encoding="utf-8") as f:
        config_dict = yaml.safe_load(f)

    if not isinstance(config_dict, dict):
        raise ValueError(f"Config file must contain a YAML mapping, got: {type(config_dict)}")

    return PipelineConfig(**config_dict)


def save_config(config: PipelineConfig, output_path: str) -> None:
    """
    Serialize a :class:`PipelineConfig` to a YAML file.

    Args:
        config: Configuration instance to save
        output_path: Destination file path
    """
    import yaml

    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(config.model_dump(), f, default_flow_style=False, allow_unicode=True)
