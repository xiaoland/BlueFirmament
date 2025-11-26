"""BF Model - Abilities to define data models for your backend application."""

__all__ = [
    # Main classes
    "BFModel",
    "BaseModel",
    "NoProxyModel",
    "ModelTV",
    "merge_model",
    # Field classes
    "Field",
    "PrivateField",
    "CompositeField",
    "field",
    "private_field",
    # Validators
    "field_validator",
    "field_validators",
    "model_validator",
    # Converters
    "BaseConverter",
    "AnyConverter",
    "UnionConverter",
    "OptionalConverter",
    "StrConverter",
    "IntConverter",
    "FloatConverter",
    "ListConverter",
    "TupleConverter",
    "SetConverter",
    "DictConverter",
    "DatetimeConverter",
    "TimeConverter",
    "BoolConverter",
    "EnumConverter",
    "SchemeConverter",
    "ModelConverter",
    # Backwards compatibility aliases
    "BaseScheme",
    "NoProxyScheme",
    "SchemeTV",
    "merge_scheme",
    "FieldT",
    "PFieldT",
    "OptionalConveter",  # typo in original, kept for compatibility
    "scheme_validator",
]

from .main import (
    BFModel,
    BaseModel,
    NoProxyModel,
    ModelTV,
    merge as merge_model,
    # Backwards compatibility
    BaseScheme,
    NoProxyScheme,
    SchemeTV,
    merge as merge_scheme,
)
from .field import (
    Field,
    PrivateField,
    CompositeField,
    field,
    private_field,
    Field as FieldT,
    PrivateField as PFieldT,
)
from .converter import (
    BaseConverter,
    AnyConverter,
    UnionConverter,
    OptionalConverter,
    OptionalConverter as OptionalConveter,  # typo in original, kept for compatibility
    StrConverter,
    IntConverter,
    FloatConverter,
    ListConverter,
    TupleConverter,
    SetConverter,
    DictConverter,
    DatetimeConverter,
    TimeConverter,
    BoolConverter,
    EnumConverter,
    ModelConverter,
    ModelConverter as SchemeConverter,  # Backwards compatibility
)
from .validator import (
    field_validator,
    field_validators,
    model_validator,
    model_validator as scheme_validator,  # Backwards compatibility
)
