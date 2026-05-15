"""
Command-line interface for VisionFlow.
"""

from __future__ import annotations

import asyncio
import logging
import platform
import sys
from pathlib import Path
from typing import Any, List

import click

from visionflow import __version__
from visionflow.config.config import PipelineConfig, load_config
from visionflow.core.pipeline import StreamPipeline
from visionflow.ingestion.base import BaseSource
from visionflow.ingestion.file import FileSource
from visionflow.ingestion.rtsp import RTSPSource
from visionflow.ingestion.webcam import WebcamSource
from visionflow.outputs.api import RestAPIOutput
from visionflow.outputs.file import FileOutput
from visionflow.outputs.kafka import KafkaOutput
from visionflow.outputs.log import LogOutput
from visionflow.outputs.websocket import WebSocketOutput
from visionflow.processing.ocr import OCRWorker
from visionflow.processing.pool import WorkerPool
from visionflow.processing.yolo import YOLOWorker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# CLI Group
# ------------------------------------------------------------------ #


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """VisionFlow — Event-driven AI video stream processing framework."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# ------------------------------------------------------------------ #
# visionflow run
# ------------------------------------------------------------------ #


@cli.command()
@click.argument("config_file", type=click.Path(exists=True, path_type=Path))
@click.option("--debug", is_flag=True, help="Enable DEBUG-level logging")
@click.option(
    "--log-file",
    type=click.Path(path_type=Path),
    default=None,
    help="Also write logs to this file",
)
def run(config_file: Path, debug: bool, log_file: Path | None) -> None:
    """
    Run a pipeline from a YAML configuration file.

    \b
    Example:
        visionflow run config.yaml
        visionflow run config.yaml --debug
    """
    if debug:
        logging.getLogger("visionflow").setLevel(logging.DEBUG)

    if log_file is not None:
        fh = logging.FileHandler(log_file)
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s — %(message)s"))
        logging.getLogger().addHandler(fh)

    try:
        logger.info(f"Loading configuration: {config_file}")
        config = load_config(str(config_file))
        pipeline = _build_pipeline(config)

        logger.info(f"Starting pipeline: {config.name!r}")
        asyncio.run(pipeline.run())

    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=debug)
        sys.exit(1)


def _build_pipeline(config: PipelineConfig) -> StreamPipeline:
    """Construct a StreamPipeline from a PipelineConfig."""
    pipeline = StreamPipeline(name=config.name)

    # ---- Sources ----
    for sc in config.sources:
        source: BaseSource
        if sc.type == "rtsp":
            source = RTSPSource(sc.url, sc.id, sc.fps)
        elif sc.type == "file":
            source = FileSource(sc.url, sc.id, sc.fps)
        elif sc.type == "webcam":
            source = WebcamSource(
                device_index=int(sc.url),
                source_id=sc.id,
                fps=sc.fps,
            )
        else:
            logger.warning(f"Unknown source type {sc.type!r} — skipping {sc.id!r}")
            continue
        pipeline.add_source(source)
        logger.info(f"Source added: {sc.id!r} ({sc.type})")

    # ---- Workers ----
    workers: List[Any] = []
    for wc in config.workers:
        if not wc.enabled:
            continue
        if wc.type == "yolo":
            workers.append(YOLOWorker(wc.id, wc.model or "yolov8n.pt"))
        elif wc.type == "ocr":
            workers.append(OCRWorker(wc.id, wc.config.get("engine", "tesseract")))
        else:
            logger.warning(f"Unknown worker type {wc.type!r} — skipping {wc.id!r}")
            continue
        logger.info(f"Worker added: {wc.id!r} ({wc.type})")

    if workers:
        pipeline.workers = workers
        pipeline.worker_pool = WorkerPool(workers)

    # ---- Outputs ----
    for oc in config.outputs:
        if not oc.enabled:
            continue

        if oc.type == "log":
            output: Any = LogOutput(oc.id, oc.config.get("level", "INFO"))

        elif oc.type == "file":
            output = FileOutput(
                output_id=oc.id,
                output_path=oc.config.get("path", "visionflow_events.jsonl"),
                max_bytes=int(oc.config.get("max_bytes", 10 * 1024 * 1024)),
            )

        elif oc.type == "rest_api":
            output = RestAPIOutput(
                output_id=oc.id,
                host=oc.config.get("host", "0.0.0.0"),
                port=int(oc.config.get("port", 8000)),
                max_events=int(oc.config.get("max_events", 1000)),
            )

        elif oc.type == "websocket":
            output = WebSocketOutput(output_id=oc.id)

        elif oc.type == "kafka":
            output = KafkaOutput(
                output_id=oc.id,
                brokers=oc.config.get("brokers", ["localhost:9092"]),
                topic=oc.config.get("topic", "visionflow_events"),
            )

        elif oc.type == "mqtt":
            try:
                from visionflow.outputs.mqtt import MQTTOutput

                output = MQTTOutput(
                    output_id=oc.id,
                    broker_host=oc.config.get("host", "localhost"),
                    broker_port=int(oc.config.get("port", 1883)),
                    topic_prefix=oc.config.get("topic_prefix", "visionflow/events"),
                    qos=int(oc.config.get("qos", 0)),
                )
            except ImportError:
                logger.warning("paho-mqtt not installed — skipping MQTT output")
                continue

        else:
            logger.warning(f"Unknown output type {oc.type!r} — skipping {oc.id!r}")
            continue

        pipeline.add_output(output)
        logger.info(f"Output added: {oc.id!r} ({oc.type})")

    return pipeline


# ------------------------------------------------------------------ #
# visionflow init
# ------------------------------------------------------------------ #


@cli.command()
@click.argument("output_file", type=click.Path(path_type=Path))
@click.option("--name", default="VisionFlow Pipeline", help="Pipeline name")
@click.option(
    "--template",
    type=click.Choice(["basic", "yolo", "multi"]),
    default="basic",
    help="Configuration template to generate",
)
def init(output_file: Path, name: str, template: str) -> None:
    """
    Generate a starter configuration file.

    \b
    Templates:
        basic  — single RTSP source with log output
        yolo   — RTSP source with YOLO detector and REST API
        multi  — multiple sources with YOLO, file output, and REST API

    \b
    Example:
        visionflow init config.yaml --template yolo
    """
    from visionflow.config.config import (
        OutputConfig,
        PipelineConfig,
        SourceConfig,
        WorkerConfig,
        save_config,
    )

    if template == "yolo":
        config = PipelineConfig(
            name=name,
            sources=[
                SourceConfig(
                    id="camera_1", type="rtsp", url="rtsp://camera.example.com/stream", fps=25
                )
            ],
            workers=[WorkerConfig(id="detector", type="yolo", model="yolov8n.pt")],
            outputs=[
                OutputConfig(id="logger", type="log"),
                OutputConfig(id="api", type="rest_api", config={"host": "0.0.0.0", "port": 8000}),
            ],
        )
    elif template == "multi":
        config = PipelineConfig(
            name=name,
            sources=[
                SourceConfig(id="rtsp_cam", type="rtsp", url="rtsp://camera1.local/stream", fps=25),
                SourceConfig(id="video_file", type="file", url="video.mp4", fps=30),
            ],
            workers=[
                WorkerConfig(id="detector", type="yolo", model="yolov8n.pt"),
            ],
            outputs=[
                OutputConfig(id="logger", type="log"),
                OutputConfig(id="events_file", type="file", config={"path": "events.jsonl"}),
                OutputConfig(id="api", type="rest_api", config={"host": "0.0.0.0", "port": 8000}),
            ],
        )
    else:  # basic
        config = PipelineConfig(
            name=name,
            sources=[
                SourceConfig(id="camera_1", type="rtsp", url="rtsp://camera.example.com/stream")
            ],
            workers=[],
            outputs=[OutputConfig(id="logger", type="log")],
        )

    save_config(config, str(output_file))
    click.echo(click.style(f"✓ Config created: {output_file}", fg="green"))
    click.echo(f"  Run it with: visionflow run {output_file}")


# ------------------------------------------------------------------ #
# visionflow validate
# ------------------------------------------------------------------ #


@cli.command()
@click.argument("config_file", type=click.Path(exists=True, path_type=Path))
def validate(config_file: Path) -> None:
    """
    Validate a configuration file without starting the pipeline.

    \b
    Example:
        visionflow validate config.yaml
    """
    try:
        config = load_config(str(config_file))
        click.echo(click.style("✓ Configuration is valid", fg="green"))
        click.echo(f"  Name:    {config.name}")
        click.echo(f"  Sources: {len(config.sources)}")
        click.echo(f"  Workers: {len([w for w in config.workers if w.enabled])}")
        click.echo(f"  Outputs: {len([o for o in config.outputs if o.enabled])}")
    except Exception as e:
        click.echo(click.style(f"✗ Invalid configuration: {e}", fg="red"))
        sys.exit(1)


# ------------------------------------------------------------------ #
# visionflow info
# ------------------------------------------------------------------ #


@cli.command()
def info() -> None:
    """Show VisionFlow environment and dependency information."""

    def _check(pkg: str) -> str:
        try:
            mod = __import__(pkg.replace("-", "_"))
            ver = getattr(mod, "__version__", "installed")
            return click.style(ver, fg="green")
        except ImportError:
            return click.style("not installed", fg="yellow")

    click.echo(f"\n{'VisionFlow Environment':}")
    click.echo("=" * 40)
    click.echo(f"  VisionFlow  : {__version__}")
    click.echo(f"  Python      : {platform.python_version()}")
    click.echo(f"  Platform    : {platform.system()} {platform.machine()}")
    click.echo("")
    click.echo("  Dependencies:")
    for pkg in [
        "cv2",
        "numpy",
        "fastapi",
        "pydantic",
        "ultralytics",
        "pytesseract",
        "kafka",
        "paho",
    ]:
        click.echo(f"    {pkg:<16}: {_check(pkg)}")
    click.echo("")


# ------------------------------------------------------------------ #
# visionflow version
# ------------------------------------------------------------------ #


@cli.command()
def version() -> None:
    """Show the VisionFlow version."""
    click.echo(f"visionflow {__version__}")


# ------------------------------------------------------------------ #
# Entry point
# ------------------------------------------------------------------ #


def main() -> None:
    """Main CLI entry point."""
    cli()


if __name__ == "__main__":
    main()
