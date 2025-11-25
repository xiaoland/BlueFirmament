"""DataAccessLayer

Design Doc: :doc:`/design/dal`
"""

__all__ = [
    "DALPath", "KeyableType",
    "DataAccessLayer", "DataAccessObject", "DataAccessObjects",
    "Column", "column",
    "DALModel", "DALModelTV",
]


from .types import (
    DALPath, KeyableType
)

from .base import (
    DataAccessLayer, DataAccessObject, DataAccessObjects
)

# Lazy imports to avoid circular dependencies
def __getattr__(name):
    """Lazy import Column and DALModel to avoid circular imports."""
    if name in ("Column", "column"):
        from .column import Column, column
        globals()["Column"] = Column
        globals()["column"] = column
        return Column if name == "Column" else column
    if name in ("DALModel", "DALModelTV"):
        from .model import DALModel, DALModelTV
        globals()["DALModel"] = DALModel
        globals()["DALModelTV"] = DALModelTV
        return DALModel if name == "DALModel" else DALModelTV
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
