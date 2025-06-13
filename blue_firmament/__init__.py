"""Blue Firmament - A Python backend framework.
"""

__version__ = "0.1.2"
__name__ = "blue_firmament"
__all__ = [
    "task",
    "Method",
    "BlueFirmamentApp"
]


from .core import BlueFirmamentApp
from .task import task, Method
