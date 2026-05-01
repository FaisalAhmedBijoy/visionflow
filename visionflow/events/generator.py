"""
Event generator for converting inference results into events.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from visionflow.events.event import Event


class EventGenerator:
    """
    Converts inference results (detections, OCR, etc.) into structured events.

    This is a flexible event factory that maps raw model outputs to domain events.
    """

    def __init__(self) -> None:
        """Initialize the event generator."""
        self._generators: Dict[str, Callable[[Dict[str, Any], str], List[Event]]] = {}

    def register_generator(
        self, event_type: str, generator: Callable[[Dict[str, Any], str], List[Event]]
    ) -> None:
        """
        Register a generator function for a specific event type.

        Args:
            event_type: Type of event to generate
            generator: Function that takes (data, source_id) and returns list of events
        """
        self._generators[event_type] = generator

    def generate(self, event_type: str, data: Dict[str, Any], source_id: str) -> List[Event]:
        """
        Generate events from inference data.

        Args:
            event_type: Type of event to generate
            data: Inference data (e.g., YOLO detections)
            source_id: ID of the source

        Returns:
            List of generated events
        """
        if event_type not in self._generators:
            # Default: create single event with raw data
            return [Event(event_type=event_type, source_id=source_id, data=data)]

        generator = self._generators[event_type]
        return generator(data, source_id)

    @staticmethod
    def default_yolo_generator(detections: Dict[str, Any], source_id: str) -> List[Event]:
        """
        Default YOLO detection event generator.

        Converts YOLO detection results into vehicle/person/object detection events.
        """
        events: List[Event] = []

        # Extract class names and confidences from YOLO output
        classes = detections.get("classes", [])
        confidences = detections.get("confidences", [])
        boxes = detections.get("boxes", [])

        for class_name, confidence, box in zip(classes, confidences, boxes):
            events.append(
                Event(
                    event_type=f"{class_name.lower()}_detected",
                    source_id=source_id,
                    data={
                        "class": class_name,
                        "confidence": float(confidence),
                        "box": box,
                    },
                )
            )

        return events

    @staticmethod
    def default_ocr_generator(ocr_result: Dict[str, Any], source_id: str) -> List[Event]:
        """
        Default OCR event generator.

        Converts OCR results into text recognition events.
        """
        return [
            Event(
                event_type="text_recognized",
                source_id=source_id,
                data={
                    "text": ocr_result.get("text", ""),
                    "confidence": ocr_result.get("confidence", 0.0),
                    "boxes": ocr_result.get("boxes", []),
                },
            )
        ]
