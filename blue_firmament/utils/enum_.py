"""Utils related to Enums."""

__all__ = [
    'dump_enum',
    'load_enum',
]

import typing
import enum


DumpEnumValueType = typing.TypeVar('DumpEnumValueType')
@typing.overload
def dump_enum(enum_member: enum.Enum) -> DumpEnumValueType:
    ...
@typing.overload
def dump_enum(enum_member: DumpEnumValueType) -> DumpEnumValueType:
    ...
@typing.overload
def dump_enum(enum_member: None) -> None:
    ...
def dump_enum(enum_member: enum.Enum | DumpEnumValueType | None) -> DumpEnumValueType | None:
    """Dump enum member to its value.
    """
    if enum_member is None:
        return None
    if isinstance(enum_member, enum.Enum):
        return enum_member.value
    return enum_member


EnumType = typing.TypeVar('EnumType', bound=enum.Enum)
@typing.overload
def load_enum(
    enum_class: typing.Type[EnumType],
    name: str | int | EnumType,
) -> EnumType:
    ...
@typing.overload
def load_enum(
    enum_class: typing.Type[EnumType],
    name: None,
) -> None:
    ...
def load_enum(
    enum_class: typing.Type[EnumType],
    value: str | int | EnumType | None,
) -> EnumType | None:
    """Resolve enum member from value.

    :param enum_class: The enum class.
    :param value: The enum member value or a member of the enum class.

    :raise ValueError: If no enum member for this value in the enum class.
    :returns: Enum member. If you pass None as name, returns None.
    """
    if value is None:
        return None
    if isinstance(value, enum.Enum):
        return value
    else:
        try:
            return enum_class(value)
        except ValueError as e:
            raise ValueError(
                f"Value '{value}' is not a valid member of enum '{enum_class.__name__}'"
            ) from e
