"""Backward compatibility module for transport -> event.source migration.

This module provides backward compatibility for code that imports from
`blue_firmament.transport`. New code should import from `blue_firmament.event.source`.

.. deprecated:: 0.4.0
    Use `blue_firmament.event.source` instead.
"""

import warnings

warnings.warn(
    "The 'blue_firmament.transport' module is deprecated. "
    "Use 'blue_firmament.event.source' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything from event.source module
from ..event.source import Method, HTTPTransporter
from ..event.source.base import BaseTransporter, BaseEventSource
from ..event.source.pubsub import PubSubTransporter, PubSubEventSource
from ..event.source.queue import QueueTransporter, QueueEventSource

__all__ = [
    'Method',
    'HTTPTransporter',
    'BaseTransporter',
    'BaseEventSource',
    'PubSubTransporter',
    'PubSubEventSource',
    'QueueTransporter',
    'QueueEventSource'
]
