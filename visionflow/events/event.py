"""
Event class definitions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict
from uuid import UUID, uuid4


@dataclass
class Event:
    """
    Core event class representing a detection or inference result.

    Attributes:
        event_type: Type of event (e.g., 'vehicle_detected', 'text_recognized')
        timestamp: When the event was generated
        source_id: ID of the source that generated this event
        data: Event-specific data (detection results, metadata, etc.)
        event_id: Unique identifier for this event
        metadata: Additional contextual information
    """

    event_type: str
    source_id: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    event_id: UUID = field(default_factory=uuid4)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        """String representation of the event."""
        return (
            f"Event(type={self.event_type}, source={self.source_id}, "
            f"timestamp={self.timestamp.isoformat()})"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary format."""
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "source_id": self.source_id,
            "data": self.data,
            "metadata": self.metadata,
        }
