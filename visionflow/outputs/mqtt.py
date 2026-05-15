"""
MQTT broker output handler for IoT and edge deployments.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any, Optional

from visionflow.outputs.base import BaseOutput

if TYPE_CHECKING:
    from visionflow.events.event import Event

logger = logging.getLogger(__name__)


class MQTTOutput(BaseOutput):
    """
    Publish pipeline events to an MQTT broker.

    Ideal for IoT and edge deployments where downstream consumers subscribe to
    topics via lightweight MQTT clients (e.g., embedded devices, dashboards).

    Each event is published as a JSON payload to ``{topic_prefix}/{event_type}``.

    Requires the optional ``mqtt`` extra::

        pip install visionflow[mqtt]

    Example::

        output = MQTTOutput(
            broker_host="mqtt.local",
            broker_port=1883,
            topic_prefix="visionflow/camera1",
        )
        pipeline.add_output(output)

    Subscribing::

        # Subscribe to all detections
        mosquitto_sub -h mqtt.local -t "visionflow/camera1/#"

        # Subscribe to a specific event type
        mosquitto_sub -h mqtt.local -t "visionflow/camera1/person_detected"

    Args:
        output_id: Unique identifier
        broker_host: MQTT broker hostname or IP
        broker_port: MQTT broker port (default 1883, TLS typically 8883)
        topic_prefix: Topic prefix; event type is appended as a sub-topic
        qos: MQTT QoS level (0, 1, or 2)
        username: Optional broker username
        password: Optional broker password
        keepalive: Broker keepalive interval in seconds
    """

    def __init__(
        self,
        output_id: str = "mqtt_output",
        broker_host: str = "localhost",
        broker_port: int = 1883,
        topic_prefix: str = "visionflow/events",
        qos: int = 0,
        username: Optional[str] = None,
        password: Optional[str] = None,
        keepalive: int = 60,
    ) -> None:
        super().__init__(output_id)
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.topic_prefix = topic_prefix.rstrip("/")
        self.qos = qos
        self.username = username
        self.password = password
        self.keepalive = keepalive
        self._client: Optional[Any] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    async def start(self) -> None:
        """Connect to the MQTT broker."""
        try:
            import paho.mqtt.client as mqtt
        except ImportError:
            raise ImportError(
                "paho-mqtt is required for MQTT support. "
                "Install with: pip install visionflow[mqtt]"
            )

        try:
            self._loop = asyncio.get_event_loop()
            self._client = mqtt.Client(client_id=self.output_id)

            if self.username:
                self._client.username_pw_set(self.username, self.password)

            self._client.on_connect = self._on_connect
            self._client.on_disconnect = self._on_disconnect

            assert self._client is not None
            # Connect in a thread to avoid blocking the event loop
            await self._loop.run_in_executor(
                None,
                lambda: self._client.connect(
                    self.broker_host, self.broker_port, keepalive=self.keepalive
                ),
            )
            self._client.loop_start()
            self.is_running = True
            self._logger.info(
                f"MQTT output connected: {self.broker_host}:{self.broker_port} "
                f"(prefix={self.topic_prefix!r})"
            )
        except Exception as e:
            self._logger.error(f"Failed to connect to MQTT broker: {e}", exc_info=True)
            raise

    async def stop(self) -> None:
        """Disconnect from the MQTT broker."""
        if self._client is not None:
            try:
                self._client.loop_stop()
                self._client.disconnect()
            except Exception as e:
                self._logger.error(f"Error disconnecting from MQTT: {e}")
            finally:
                self._client = None
        self.is_running = False
        self._logger.info("MQTT output stopped")

    async def send_event(self, event: "Event") -> None:
        """
        Publish an event to ``{topic_prefix}/{event_type}``.

        Args:
            event: Event to publish
        """
        if not self.is_running or self._client is None or self._loop is None:
            return

        topic = f"{self.topic_prefix}/{event.event_type}"
        payload = json.dumps(event.to_dict(), default=str)

        try:
            assert self._client is not None
            await self._loop.run_in_executor(
                None,
                lambda: self._client.publish(topic, payload, qos=self.qos),
            )
        except Exception as e:
            self._logger.error(f"Error publishing MQTT message to {topic!r}: {e}")

    def _on_connect(self, client: Any, userdata: Any, flags: Any, rc: int) -> None:
        if rc == 0:
            self._logger.debug("MQTT broker connected successfully")
        else:
            self._logger.warning(f"MQTT broker connection returned code: {rc}")

    def _on_disconnect(self, client: Any, userdata: Any, rc: int) -> None:
        if rc != 0:
            self._logger.warning(f"Unexpected MQTT disconnect (rc={rc})")

    def __repr__(self) -> str:
        return (
            f"MQTTOutput(output_id={self.output_id!r}, "
            f"broker={self.broker_host}:{self.broker_port}, "
            f"topic_prefix={self.topic_prefix!r}, is_running={self.is_running})"
        )
