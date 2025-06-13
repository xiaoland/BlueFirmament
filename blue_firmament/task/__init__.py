"""Task module of BlueFirmament.

Task is the service unit of an BlueFirmament Application.

Design doc: :doc:`design/task`
"""

__all__ = [
    'TaskID',
    'Task',
    'TaskStatus',
    'TaskMetadata',
    'TaskResult',
    'TaskHandler',
    'TaskRegistry',
    'TaskEntry',
    'task',
    'Method',
    'LazyParameter'
]

from .main import (
    TaskID, Task, TaskMetadata, Method, LazyParameter
)
from .result import (
    TaskStatus, TaskResult
)
from .handler import TaskHandler
from .registry import (
    TaskRegistry, TaskEntry, task
)
