"""Blue Firmament - A Python backend framework."""

__version__ = "0.1.2"
__name__ = "blue_firmament"
__all__ = [
    "BlueFirmamentApp",
    # Event module
    "Event",
    "EventID",
    "EventBus",
    "EventSource",
]


from .app import BlueFirmamentApp
from .event import Event, EventID, EventBus, EventSource

from .utils import json_

json_.override_json_encoder(json_.JsonEncoder)
