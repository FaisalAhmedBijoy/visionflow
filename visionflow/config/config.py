"""
Configuration management for VisionFlow pipelines.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class SourceConfig(BaseModel):
    """Configuration for a video source."""

    id: str
    type: str  # 'rtsp', 'file', 'websrc'
    url: str
    fps: int = 30


class WorkerConfig(BaseModel):
    """Configuration for a processing worker."""

    id: str
    type: str  # 'yolo', 'ocr'
    model: str
    enabled: bool = True
    config: Dict[str, Any] = Field(default_factory=dict)


class OutputConfig(BaseModel):
    """Configuration for an output handler."""

    id: str
    type: str  # 'log', 'websocket', 'rest_api', 'kafka'
    enabled: bool = True
    config: Dict[str, Any] = Field(default_factory=dict)


class PipelineConfig(BaseSettings):
    """Main pipeline configuration."""

    name: str = "VisionFlow Pipeline"
    sources: List[SourceConfig]
    workers: List[WorkerConfig] = Field(default_factory=list)
    outputs: List[OutputConfig] = Field(default_factory=list)
    log_level: str = "INFO"
    debug: bool = False

    class Config:
        """Pydantic config."""

        env_file = ".env"
        case_sensitive = False


def load_config(config_path: str) -> PipelineConfig:
    """
    Load pipeline configuration from YAML file.

    Args:
        config_path: Path to YAML config file

    Returns:
        Parsed configuration
    """
    import yaml

    with open(config_path, "r") as f:
        config_dict = yaml.safe_load(f)

    return PipelineConfig(**config_dict)


def save_config(config: PipelineConfig, output_path: str) -> None:
    """
    Save configuration to YAML file.

    Args:
        config: Configuration to save
        output_path: Path to save to
    """
    import yaml

    with open(output_path, "w") as f:
        yaml.dump(config.model_dump(), f, default_flow_style=False)
