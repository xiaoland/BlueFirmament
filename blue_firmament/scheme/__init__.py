"""Blue Firmament's abilities that helps you defining schemas for your backend application.

DEPRECATED: This module is deprecated. Use `blue_firmament.model` instead.
This module now re-exports from `blue_firmament.model` for backwards compatibility.
"""

__all__ = [
    "BaseScheme",
    "NoProxyScheme",
    "SchemeTV",
    "merge_scheme",
    "field",
    "private_field",
    "FieldT",
    "PFieldT",
    "CompositeField",
    "field_validator",
    "field_validators",
    "scheme_validator",
    "BaseConverter",
    "AnyConverter",
    "UnionConverter",
    "OptionalConveter",
    "StrConverter",
    "IntConverter",
    "ListConverter",
    "TupleConverter",
    "SetConverter",
    "DictConverter",
    "DatetimeConverter",
    "TimeConverter",
]

# Re-export from model module for backwards compatibility
from ..model import (
    BaseScheme,
    NoProxyScheme,
    SchemeTV,
    merge_scheme,
    field,
    private_field,
    FieldT,
    PFieldT,
    CompositeField,
    field_validator,
    field_validators,
    scheme_validator,
    BaseConverter,
    AnyConverter,
    UnionConverter,
    OptionalConveter,
    StrConverter,
    IntConverter,
    ListConverter,
    TupleConverter,
    SetConverter,
    DictConverter,
    DatetimeConverter,
    TimeConverter,
)
