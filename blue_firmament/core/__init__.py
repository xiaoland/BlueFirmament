"""Core Module of BlueFirmament

.. deprecated::
    This module is deprecated. Import from blue_firmament directly.
    - BlueFirmamentApp -> from blue_firmament import BlueFirmamentApp
    - BaseMiddleware -> from blue_firmament.event import BaseMiddleware
"""

__all__ = [
    "BlueFirmamentApp"
]


# Backward compatibility - import from new locations
from ..app import BlueFirmamentApp