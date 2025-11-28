"""Blue Firmament - A Python backend framework.
"""

__version__ = "0.1.2"
__name__ = "blue_firmament"
__all__ = [
    "listen_to",
    "Method",
    "BlueFirmamentApp",
    "EventBus",
]


from .app import BlueFirmamentApp
from .event import listen_to, Method, EventBus

from .utils import json_
json_.override_json_encoder(json_.JsonEncoder)