"""
File-based event output handler — writes events to JSONL files with rotation.
"""

from __future__ import annotations

import io
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from visionflow.outputs.base import BaseOutput

if TYPE_CHECKING:
    from visionflow.events.event import Event

logger = logging.getLogger(__name__)


class FileOutput(BaseOutput):
    """
    Append events to a rotating JSONL (JSON Lines) file.

    Each event is written as a single JSON object on its own line, which makes
    the output easy to process with tools like ``jq``, ``pandas``, or any
    log aggregation pipeline.

    File rotation occurs when the file size exceeds ``max_bytes``. Old files
    are renamed with a timestamp suffix and a new file is started.

    Example::

        output = FileOutput(
            output_path="events.jsonl",
            max_bytes=10 * 1024 * 1024,  # rotate at 10 MB
        )
        pipeline.add_output(output)

    Args:
        output_id: Unique identifier for this output handler
        output_path: Destination file path (created if it does not exist)
        max_bytes: File size threshold for rotation in bytes (default 10 MB, 0 = disabled)
        encoding: File encoding (default ``"utf-8"``)
    """

    def __init__(
        self,
        output_id: str = "file_output",
        output_path: str = "visionflow_events.jsonl",
        max_bytes: int = 10 * 1024 * 1024,
        encoding: str = "utf-8",
    ) -> None:
        super().__init__(output_id)
        self.output_path = Path(output_path)
        self.max_bytes = max_bytes
        self.encoding = encoding
        self._file: Optional[io.TextIOWrapper] = None
        self._bytes_written: int = 0

    async def start(self) -> None:
        """Open the output file for appending."""
        try:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            self._file = self.output_path.open("a", encoding=self.encoding)
            self._bytes_written = (
                self.output_path.stat().st_size if self.output_path.exists() else 0
            )
            self.is_running = True
            self._logger.info(f"FileOutput started: {self.output_path}")
        except Exception as e:
            self._logger.error(f"Error opening file '{self.output_path}': {e}", exc_info=True)
            raise

    async def stop(self) -> None:
        """Flush and close the output file."""
        if self._file is not None:
            try:
                self._file.flush()  # type: ignore[union-attr]
                self._file.close()  # type: ignore[union-attr]
            except Exception as e:
                self._logger.error(f"Error closing file: {e}")
            finally:
                self._file = None
        self.is_running = False
        self._logger.info(f"FileOutput stopped: {self.output_path}")

    async def send_event(self, event: "Event") -> None:
        """
        Append an event to the JSONL file.

        If the file has exceeded ``max_bytes``, it is rotated first.

        Args:
            event: Event to write
        """
        if not self.is_running or self._file is None:
            return

        try:
            # Rotate if needed
            if self.max_bytes > 0 and self._bytes_written >= self.max_bytes:
                await self._rotate()

            line = json.dumps(event.to_dict(), default=str) + "\n"
            self._file.write(line)  # type: ignore[union-attr]
            self._file.flush()  # type: ignore[union-attr]
            self._bytes_written += len(line.encode(self.encoding))

        except Exception as e:
            self._logger.error(f"Error writing event to file: {e}", exc_info=True)

    async def _rotate(self) -> None:
        """Rotate the current file by renaming it with a timestamp suffix."""
        try:
            if self._file is not None:
                self._file.flush()  # type: ignore[union-attr]
                self._file.close()  # type: ignore[union-attr]

            timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            rotated = self.output_path.with_suffix(f".{timestamp}.jsonl")
            self.output_path.rename(rotated)
            self._logger.info(f"Rotated log file to: {rotated}")

            self._file = self.output_path.open("a", encoding=self.encoding)
            self._bytes_written = 0
        except Exception as e:
            self._logger.error(f"Error rotating file: {e}", exc_info=True)

    def __repr__(self) -> str:
        return (
            f"FileOutput(output_id={self.output_id!r}, "
            f"output_path={str(self.output_path)!r}, "
            f"max_bytes={self.max_bytes}, is_running={self.is_running})"
        )
