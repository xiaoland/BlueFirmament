"""BlueFirmament Event Model.

Event is a data model representing an occurrence in the system.
"""

__all__ = [
    "Event",
    "EventID",
]

import typing
import uuid
from typing import Optional as Opt

from ..scheme import BaseScheme
from ..scheme.field import Field, field


class EventID(BaseScheme):
    """Event identifier.

    Composed of a path that identifies the event type.
    Path uses dot notation (e.g., "user.created", "order.completed").
    """

    path: str
    """Event path using dot notation (e.g., 'user.created')"""

    separator: str = "."
    """Separator used in the path"""

    def __post_init__(self) -> None:
        super().__post_init__()
        # Normalize path
        if not self.path:
            raise ValueError("Event path cannot be empty")

    @property
    def segments(self) -> list[str]:
        """Path split by separator."""
        return self.path.split(self.separator)

    def matches(self, pattern: str) -> bool:
        """Check if this event ID matches a pattern.

        Pattern can include wildcards:
        - '*' matches any single segment
        - '**' matches any number of segments

        Examples:
            - 'user.created' matches 'user.created'
            - 'user.*' matches 'user.created', 'user.deleted'
            - 'user.**' matches 'user.created', 'user.profile.updated'
        """
        pattern_segments = pattern.split(self.separator)
        event_segments = self.segments

        return self._match_segments(pattern_segments, event_segments)

    @staticmethod
    def _match_segments(pattern: list[str], segments: list[str]) -> bool:
        """Match pattern segments against event segments."""
        p_idx, s_idx = 0, 0

        while p_idx < len(pattern) and s_idx < len(segments):
            if pattern[p_idx] == "**":
                # Match any number of remaining segments
                if p_idx == len(pattern) - 1:
                    return True
                # Try matching remaining pattern with rest of segments
                for i in range(s_idx, len(segments) + 1):
                    if EventID._match_segments(pattern[p_idx + 1 :], segments[i:]):
                        return True
                return False
            elif pattern[p_idx] == "*":
                # Match single segment
                p_idx += 1
                s_idx += 1
            elif pattern[p_idx] == segments[s_idx]:
                p_idx += 1
                s_idx += 1
            else:
                return False

        # Handle trailing '**'
        while p_idx < len(pattern) and pattern[p_idx] == "**":
            p_idx += 1

        return p_idx == len(pattern) and s_idx == len(segments)

    def __str__(self) -> str:
        return self.path

    def __eq__(self, other: object) -> bool:
        if isinstance(other, EventID):
            return self.path == other.path
        if isinstance(other, str):
            return self.path == other
        return False

    def __hash__(self) -> int:
        return hash(self.path)


class Event(BaseScheme, partial=True):
    """Event model representing an occurrence in the system.

    Events are emitted by event sources and handled by event handlers
    through the event bus.

    Attributes:
        id: Unique identifier for this event type
        trace_id: Unique identifier for tracing this specific event instance
        parameters: Data associated with the event
        metadata: Additional metadata about the event
    """

    id: Field[EventID]
    """Event identifier"""

    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    """Unique trace ID for this event instance"""

    parameters: typing.Any = field(default_factory=dict)
    """Event parameters/payload"""

    metadata: typing.Any = field(default_factory=dict)
    """Event metadata"""

    @classmethod
    def create(
        cls,
        path: str,
        parameters: Opt[dict[str, typing.Any]] = None,
        metadata: Opt[dict[str, typing.Any]] = None,
        separator: str = ".",
    ) -> typing.Self:
        """Create an event with the given path and parameters.

        Args:
            path: Event path (e.g., 'user.created')
            parameters: Event data
            metadata: Additional metadata
            separator: Path separator
        """
        return cls(
            id=EventID(path=path, separator=separator),
            parameters=parameters or {},
            metadata=metadata or {},
        )

    def __str__(self) -> str:
        return f"Event({self.id}, trace={self.trace_id})"
