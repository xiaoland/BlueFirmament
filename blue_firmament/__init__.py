"""Blue Firmament - A Python backend framework.
"""

__version__ = "0.1.2"
__name__ = "blue_firmament"
__all__ = [
    "listen_to",
    "Method",
    "BlueFirmamentApp",
    # Event module
    "Event",
    "EventID",
    "EventBus",
    "EventSource",
]


from .core import BlueFirmamentApp
from .task import listen_to, Method
from .event import Event, EventID, EventBus, EventSource

from .utils import json_
json_.override_json_encoder(json_.JsonEncoder)