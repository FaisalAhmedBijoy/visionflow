"""
Output module - event distribution channels.
"""

from visionflow.outputs.api import RestAPIOutput
from visionflow.outputs.base import BaseOutput
from visionflow.outputs.dispatcher import OutputDispatcher
from visionflow.outputs.kafka import KafkaOutput
from visionflow.outputs.log import LogOutput
from visionflow.outputs.websocket import WebSocketOutput

__all__ = [
    "BaseOutput",
    "LogOutput",
    "WebSocketOutput",
    "RestAPIOutput",
    "KafkaOutput",
    "OutputDispatcher",
]
