"""Backward compatibility module for task -> event migration.

This module provides backward compatibility for code that imports from
`blue_firmament.task`. New code should import from `blue_firmament.event`.

.. deprecated:: 0.4.0
    Use `blue_firmament.event` instead.
"""

import warnings

warnings.warn(
    "The 'blue_firmament.task' module is deprecated. "
    "Use 'blue_firmament.event' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything from event module
from ..event import (
    TaskID,
    Task,
    TaskStatus,
    TaskMetadata,
    TaskResult,
    TaskHandler,
    TaskRegistry,
    TaskEntry,
    listen_to,
    Method,
    LazyParameter,
    set_event_broker,
    Event,
    emit,
    simple_emit
)

__all__ = [
    'TaskID',
    'Task',
    'TaskStatus',
    'TaskMetadata',
    'TaskResult',
    'TaskHandler',
    'TaskRegistry',
    'TaskEntry',
    'listen_to',
    'Method',
    'LazyParameter',
    'set_event_broker',
    'Event',
    'emit',
    'simple_emit'
]
