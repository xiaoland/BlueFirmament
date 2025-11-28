"""BlueFirmament Middleware

.. deprecated::
    This module is deprecated. Import from blue_firmament.event.middleware instead.
"""

__all__ = [
    "BaseMiddleware",
    "NextT",
    "MiddlewaresT",
]

# Backward compatibility - import from new location
from ..event.middleware import BaseMiddleware, NextT, MiddlewaresT
