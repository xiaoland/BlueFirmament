import abc
import copy
import enum
import typing
from typing import Optional as Opt

from . import DALQueryComponent
from ..utils import dump_field_like
from ..types import FieldLikeType, DALPath


class DALFilter(DALQueryComponent):

    __use_fqfn__ = False

    def __init__(self, field: FieldLikeType, value: typing.Any):
        self._field = field
        self.__value = value

    @property
    def dal_path(self) -> Opt[DALPath]:
        from ...scheme.field import Field, FieldValueProxy
        if isinstance(self._field, Field):
            return self._field.scheme_cls.dal_path()
        if isinstance(self._field, FieldValueProxy):
            return self._field.scheme.dal_path()
        return None

    @property
    def field_name(self) -> str:
        """Get field name.

        If `__use_fqfn__` is True, return fully qualified field name.
        """
        field_name = dump_field_like(self._field)
        if self.__use_fqfn__ and self.dal_path:
            return f"{self.dal_path[0]}.{field_name}"
        return field_name

    @property
    def value(self):
        """Get primitive python types of value

        - enum.Enum -> enum.Enum.value
        """
        # TODO 使用 field.converter 进行 dump
        if isinstance(self.__value, enum.Enum):
            return self.__value.value
        return self.__value

    def fork(
        self,
        use_fqfn: bool = False
    ) -> typing.Self:
        forked = copy.copy(self)
        forked.__use_fqfn__ = use_fqfn
        return forked

    def __repr__(self):
        return super().__repr__() + f'(field={self._field},value={self.value})'


class EqFilter(DALFilter):
    
    def dump_to_sql(self) -> str:
        return f"{self.field_name} = {repr(self.value)}"

    def dump_to_postgrest(self):
        return ('eq', (self.field_name, self.value))

    def dump_to_postgrest_str(self) -> str:
        return f"{self.field_name}.eq.{self.value}"

class NotEqFilter(DALFilter):
    
    def dump_to_sql(self) -> str:
        return f"{self.field_name} != {repr(self.value)}"

    def dump_to_postgrest(self):
        return ('neq', (self.field_name, self.value))

    def dump_to_postgrest_str(self) -> str:
        return f"{self.field_name}.neq.{repr(self.value)}"

class IsFilter(DALFilter):

    __filter_name__ = 'is_'
    
    def __init__(self, field: FieldLikeType, value: bool | None) -> None:
        super().__init__(field, value)
    
    def dump_to_sql(self) -> str:
        return f"{self.field_name} IS {repr(self.value)}"

    def dump_to_postgrest(self):
        return (self.__filter_name__, (self.field_name, self.value))

    def dump_to_postgrest_str(self) -> str:
        if self.value is None:
            return f"{self.field_name}.is.null"
        elif self.value is True:
            return f"{self.field_name}.is.true"
        elif self.value is False:
            return f"{self.field_name}.is.false"
        else:
            raise ValueError("Value must be bool or None for IsFilter")

class InFilter(DALFilter):

    def __init__(self, field: FieldLikeType, value: typing.Iterable) -> None:
        super().__init__(field, value)
    
    def dump_to_sql(self) -> str:
        return f"{self.field_name} IN ({', '.join(repr(v) for v in self.value)})"

    def dump_to_postgrest(self):
        return ("in_", (self.field_name, self.value))

    def dump_to_postgrest_str(self) -> str:
        return f"{self.field_name}.in.({','.join(repr(v) for v in self.value)})"

class ContainsFilter(DALFilter):
    
    def __init__(self, field: FieldLikeType, /, *values: typing.Any) -> None:
        super().__init__(field, values)
    
    def dump_to_sql(self) -> str:
        return f"{self.field_name} LIKE {repr('%' + self.value + '%')}"

    def dump_to_postgrest(self):
        return ("contains", (self.field_name, self.value))

    def dump_to_postgrest_str(self) -> str:
        values = ",".join(f'"{value}"' for value in self.value)
        return f"{self.field_name}.cs.{{{values}}}"
