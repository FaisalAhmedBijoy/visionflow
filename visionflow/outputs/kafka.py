"""
Kafka output handler.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any, Optional

from visionflow.outputs.base import BaseOutput

if TYPE_CHECKING:
    from visionflow.events.event import Event


class KafkaOutput(BaseOutput):
    """
    Kafka output handler.

    Publishes events to Kafka topics.
    """

    def __init__(
        self,
        output_id: str = "kafka_output",
        brokers: list | None = None,
        topic: str = "visionflow_events",
    ) -> None:
        """
        Initialize Kafka output.

        Args:
            output_id: Unique identifier
            brokers: Kafka broker addresses (e.g., ['localhost:9092'])
            topic: Kafka topic to publish to
        """
        super().__init__(output_id)
        self.brokers = brokers or ["localhost:9092"]
        self.topic = topic
        self._producer: Optional[Any] = None

    async def start(self) -> None:
        """Connect to Kafka broker."""
        try:
            from kafka import KafkaProducer

            self._producer = KafkaProducer(
                bootstrap_servers=self.brokers,
                value_serializer=lambda x: json.dumps(x, default=str).encode("utf-8"),
            )
            self.is_running = True
            self._logger.info(f"Kafka output started (brokers={self.brokers}, topic={self.topic})")
        except ImportError:
            raise ImportError("kafka-python is required. Install with: pip install kafka-python")
        except Exception as e:
            self._logger.error(f"Error connecting to Kafka: {e}", exc_info=True)
            raise

    async def stop(self) -> None:
        """Disconnect from Kafka broker."""
        if self._producer is not None:
            self._producer.close()
            self._producer = None
        self.is_running = False
        self._logger.info("Kafka output stopped")

    async def send_event(self, event: Event) -> None:
        """
        Publish event to Kafka topic.

        Args:
            event: Event to publish
        """
        if not self.is_running or self._producer is None:
            return

        try:
            # Send to Kafka (async wrapper)
            def _send() -> None:
                self._producer.send(self.topic, value=event.to_dict())
                self._producer.flush()

            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _send)

        except Exception as e:
            self._logger.error(f"Error publishing to Kafka: {e}", exc_info=True)
