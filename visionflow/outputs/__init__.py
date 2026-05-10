"""
Output module — event distribution channels.

Outputs receive events from the pipeline and forward them to external systems
(REST API, WebSocket, Kafka, MQTT, files, logging).
"""

from visionflow.outputs.api import RestAPIOutput
from visionflow.outputs.base import BaseOutput
from visionflow.outputs.dispatcher import OutputDispatcher
from visionflow.outputs.file import FileOutput
from visionflow.outputs.kafka import KafkaOutput
from visionflow.outputs.log import LogOutput
from visionflow.outputs.mqtt import MQTTOutput
from visionflow.outputs.websocket import WebSocketOutput

__all__ = [
    "BaseOutput",
    "OutputDispatcher",
    "LogOutput",
    "FileOutput",
    "WebSocketOutput",
    "RestAPIOutput",
    "KafkaOutput",
    "MQTTOutput",
]
