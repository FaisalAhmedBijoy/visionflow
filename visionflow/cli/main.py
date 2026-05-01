"""
Command-line interface for VisionFlow.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Optional

import click

from visionflow.config.config import load_config
from visionflow.core.pipeline import StreamPipeline
from visionflow.ingestion.file import FileSource
from visionflow.ingestion.rtsp import RTSPSource
from visionflow.outputs.log import LogOutput
from visionflow.processing.ocr import OCRWorker
from visionflow.processing.yolo import YOLOWorker


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@click.group()
def cli() -> None:
    """VisionFlow: Event-driven AI video stream processing framework."""
    pass


@cli.command()
@click.argument("config_file", type=click.Path(exists=True))
@click.option(
    "--debug", is_flag=True, help="Enable debug logging"
)
def run(config_file: str, debug: bool) -> None:
    """
    Run a pipeline from a configuration file.

    Usage:
        visionflow run config.yaml
    """
    if debug:
        logging.getLogger("visionflow").setLevel(logging.DEBUG)

    try:
        logger.info(f"Loading configuration from {config_file}")
        config = load_config(config_file)

        # Create pipeline
        logger.info(f"Creating pipeline: {config.name}")
        pipeline = StreamPipeline()

        # Add sources
        for source_config in config.sources:
            if source_config.type == "rtsp":
                source = RTSPSource(source_config.url, source_config.id, source_config.fps)
            elif source_config.type == "file":
                source = FileSource(source_config.url, source_config.id, source_config.fps)
            else:
                logger.warning(f"Unknown source type: {source_config.type}")
                continue

            pipeline.add_source(source)
            logger.info(f"Added source: {source_config.id} ({source_config.type})")

        # Add workers
        workers: list[Any] = []
        for worker_config in config.workers:
            if not worker_config.enabled:
                continue

            if worker_config.type == "yolo":
                worker = YOLOWorker(worker_config.id, worker_config.model)
                workers.append(worker)
                logger.info(f"Added worker: {worker_config.id} ({worker_config.type})")
            elif worker_config.type == "ocr":
                worker = OCRWorker(worker_config.id, worker_config.config.get("engine", "tesseract"))
                workers.append(worker)
                logger.info(f"Added worker: {worker_config.id} ({worker_config.type})")
            else:
                logger.warning(f"Unknown worker type: {worker_config.type}")

        if workers:
            pipeline.workers = workers
            from visionflow.processing.pool import WorkerPool

            pipeline.worker_pool = WorkerPool(workers)

        # Add outputs
        for output_config in config.outputs:
            if not output_config.enabled:
                continue

            if output_config.type == "log":
                output = LogOutput(output_config.id, output_config.config.get("level", "INFO"))
            else:
                logger.warning(f"Unknown output type: {output_config.type}")
                continue

            pipeline.add_output(output)
            logger.info(f"Added output: {output_config.id} ({output_config.type})")

        # Register default event handler
        @pipeline.on_event("*")
        async def default_handler(event: Any) -> None:
            logger.info(f"Event received: {event}")

        # Run pipeline
        logger.info("Starting pipeline...")
        asyncio.run(pipeline.run())

    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user")
    except Exception as e:
        logger.error(f"Error running pipeline: {e}", exc_info=True)
        sys.exit(1)


@cli.command()
@click.argument("output_file", type=click.Path())
@click.option(
    "--name", default="VisionFlow Pipeline", help="Pipeline name"
)
def init(output_file: str, name: str) -> None:
    """
    Initialize a new configuration file.

    Usage:
        visionflow init config.yaml
    """
    from visionflow.config.config import PipelineConfig, OutputConfig, SourceConfig, WorkerConfig, save_config

    # Create a minimal example config
    config = PipelineConfig(
        name=name,
        sources=[
            SourceConfig(
                id="camera_1",
                type="rtsp",
                url="rtsp://camera.example.com/stream",
                fps=30,
            )
        ],
        workers=[
            WorkerConfig(
                id="detector",
                type="yolo",
                model="yolov8n.pt",
                enabled=True,
            )
        ],
        outputs=[
            OutputConfig(
                id="logger",
                type="log",
                enabled=True,
            )
        ],
    )

    save_config(config, output_file)
    logger.info(f"Configuration file created: {output_file}")


@cli.command()
def version() -> None:
    """Show VisionFlow version."""
    from visionflow import __version__

    click.echo(f"VisionFlow {__version__}")


def main() -> None:
    """Main CLI entry point."""
    cli()


if __name__ == "__main__":
    main()
