"""BF DAL Column

Column is a Field subclass with SQL-related properties for database mapping.
"""

__all__ = [
    "Column",
    "column",
]

import typing
from typing import Optional as Opt

from .._types import Undefined, _undefined

# Import Field and BaseConverter at module level - this will work because dal/column.py
# is not imported directly by model/field.py
from ..model.field import Field
from ..model.converter import BaseConverter
from .query_components.filters import (
    ContainsFilter, EqFilter, NotEqFilter,
    InFilter, IsFilter
)
from .query_components.modifiers import OrderModifier
from .query_components.operators import NotOperator


FieldValueTV = typing.TypeVar('FieldValueTV')


class Column(Field[FieldValueTV]):
    """Database Column - Field with SQL-related properties.

    Extends Field with additional properties for SQL database mapping:
    - table_name: SQL table name
    - column_name: SQL column name (defaults to field name)
    - column_type: SQL column type
    - nullable: Whether the column allows NULL
    - primary_key: Whether this column is a primary key
    - auto_increment: Whether this column auto-increments
    - unique: Whether this column has a unique constraint
    - index: Whether this column is indexed
    - foreign_key: Foreign key reference
    - default_sql: SQL default expression
    - check_constraint: SQL CHECK constraint

    Examples
    --------
    >>> class User(DALModel):
    ...     _id: Column[int] = column(primary_key=True, auto_increment=True)
    ...     name: Column[str] = column(column_type="VARCHAR(255)", nullable=False)
    ...     email: Column[str] = column(unique=True)
    ...     department_id: Column[int] = column(foreign_key="departments._id")
    """

    def __init__(
        self,
        default: typing.Union[Undefined, FieldValueTV] = _undefined,
        default_factory: Opt[typing.Callable[[], FieldValueTV]] = None,
        vtype: Undefined | typing.Type[FieldValueTV] = _undefined,
        name: Opt[str] = None,
        in_model_name: Opt[str] = None,
        model_cls: Opt[typing.Type] = None,
        is_key: bool = False,
        is_key_natural: bool = False,
        is_foreign_key: bool = False,
        converter: Opt[BaseConverter[FieldValueTV]] = None,
        validators: Opt[typing.Iterable] = None,
        is_partial: bool = False,
        dump_flags: Opt[set[str]] = None,
        init: bool = True,
        # SQL-specific properties
        column_name: Opt[str] = None,
        column_type: Opt[str] = None,
        nullable: bool = True,
        primary_key: bool = False,
        auto_increment: bool = False,
        unique: bool = False,
        index: bool = False,
        foreign_key: Opt[str] = None,
        default_sql: Opt[str] = None,
        check_constraint: Opt[str] = None,
    ):
        """
        :param default: Default value for the column.
        :param default_factory: Factory function for default value.
        :param vtype: Value type annotation.
        :param name: Field name in DAL.
        :param in_model_name: Field name in model.
        :param model_cls: Model class this column belongs to.
        :param is_key: Whether this is a key field.
        :param is_key_natural: Whether this is a natural key.
        :param is_foreign_key: Whether this is a foreign key.
        :param converter: Value converter.
        :param validators: Value validators.
        :param is_partial: Whether this field is partial.
        :param dump_flags: Dump flags for serialization.
        :param init: Whether to include in __init__.
        :param column_name: SQL column name (defaults to field name).
        :param column_type: SQL data type (e.g., 'VARCHAR(255)', 'INTEGER').
        :param nullable: Whether NULL is allowed.
        :param primary_key: Whether this is a primary key.
        :param auto_increment: Whether value auto-increments.
        :param unique: Whether value must be unique.
        :param index: Whether to create an index.
        :param foreign_key: Foreign key reference (e.g., 'users._id').
        :param default_sql: SQL default expression (e.g., 'CURRENT_TIMESTAMP').
        :param check_constraint: SQL CHECK constraint expression.
        """
        # Handle primary_key setting is_key
        if primary_key:
            is_key = True
            if auto_increment:
                is_key_natural = False
            else:
                is_key_natural = True

        super().__init__(
            default=default,
            default_factory=default_factory,
            vtype=vtype,
            name=name,
            in_model_name=in_model_name,
            model_cls=model_cls,
            is_key=is_key,
            is_key_natural=is_key_natural,
            is_foreign_key=is_foreign_key or (foreign_key is not None),
            converter=converter,
            validators=validators,
            is_partial=is_partial,
            dump_flags=dump_flags,
            init=init,
        )

        self.__column_name = column_name
        self.__column_type = column_type
        self.__nullable = nullable
        self.__primary_key = primary_key
        self.__auto_increment = auto_increment
        self.__unique = unique
        self.__index = index
        self.__foreign_key = foreign_key
        self.__default_sql = default_sql
        self.__check_constraint = check_constraint

    @property
    def column_name(self) -> str:
        """SQL column name. Defaults to field name if not specified."""
        return self.__column_name or self.name

    @property
    def column_type(self) -> Opt[str]:
        """SQL data type (e.g., 'VARCHAR(255)', 'INTEGER')."""
        return self.__column_type

    @property
    def nullable(self) -> bool:
        """Whether the column allows NULL values."""
        return self.__nullable

    @property
    def primary_key(self) -> bool:
        """Whether this column is a primary key."""
        return self.__primary_key

    @property
    def auto_increment(self) -> bool:
        """Whether this column auto-increments."""
        return self.__auto_increment

    @property
    def unique(self) -> bool:
        """Whether this column has a unique constraint."""
        return self.__unique

    @property
    def index(self) -> bool:
        """Whether this column is indexed."""
        return self.__index

    @property
    def foreign_key(self) -> Opt[str]:
        """Foreign key reference (e.g., 'users._id')."""
        return self.__foreign_key

    @property
    def default_sql(self) -> Opt[str]:
        """SQL default expression (e.g., 'CURRENT_TIMESTAMP')."""
        return self.__default_sql

    @property
    def check_constraint(self) -> Opt[str]:
        """SQL CHECK constraint expression."""
        return self.__check_constraint

    def dump_to_sql_create(self) -> str:
        """Generate SQL column definition for CREATE TABLE.

        Returns
        -------
        str
            SQL column definition string.

        Example
        -------
        >>> col = Column[int](name='_id', primary_key=True, auto_increment=True)
        >>> col.dump_to_sql_create()
        '_id INTEGER PRIMARY KEY AUTOINCREMENT'
        """
        parts = [self.column_name]

        if self.__column_type:
            parts.append(self.__column_type)
        elif hasattr(self, 'vtype'):
            # Infer SQL type from Python type
            parts.append(self._infer_sql_type())

        if self.__primary_key:
            parts.append("PRIMARY KEY")

        if self.__auto_increment:
            parts.append("AUTOINCREMENT")

        if not self.__nullable:
            parts.append("NOT NULL")

        if self.__unique and not self.__primary_key:
            parts.append("UNIQUE")

        if self.__default_sql:
            parts.append(f"DEFAULT {self.__default_sql}")

        if self.__check_constraint:
            parts.append(f"CHECK ({self.__check_constraint})")

        return " ".join(parts)

    def _infer_sql_type(self) -> str:
        """Infer SQL type from Python type."""
        try:
            vtype = self.vtype
            type_mapping = {
                int: "INTEGER",
                float: "REAL",
                str: "TEXT",
                bool: "BOOLEAN",
                bytes: "BLOB",
            }
            return type_mapping.get(vtype, "TEXT")
        except ValueError:
            return "TEXT"

    # DAL Query Methods
    def equals(self, value: FieldValueTV) -> EqFilter:
        """Get an EqFilter for this column equals the given value.
        
        Example
        -------
        >>> Column[int](name='_id').equals(1)
        EqFilter(field='_id', value=1)
        """
        return EqFilter(self, value)
    
    def contains(self, *value: typing.Any) -> ContainsFilter:
        """Get a ContainsFilter for this column containing all given values."""
        return ContainsFilter(self, *value)
    
    def not_equals(self, value: typing.Any) -> NotEqFilter:
        """Get a NotEqFilter for this column not equaling the given value."""
        return NotEqFilter(self, value)
    
    def in_(self, value: typing.Iterable[typing.Any]) -> InFilter:
        """Get an InFilter for this column being in the given values."""
        return InFilter(self, value)
    
    def not_in_(self, value: typing.Iterable[typing.Any]) -> tuple[NotOperator, InFilter]:
        """Get filters for this column not being in the given values."""
        return (NotOperator(), self.in_(value))

    def is_(self, value: bool | None) -> IsFilter:
        """Get an IsFilter for this column being the given boolean or None."""
        return IsFilter(self, value)

    def is_not(self, value: bool | None) -> tuple[NotOperator, IsFilter]:
        """Get filters for this column not being the given boolean or None."""
        return (NotOperator(), self.is_(value))
    
    def order_by(self, *, desc: bool = False) -> OrderModifier:
        """Get an OrderModifier for ordering by this column.
        
        Parameters
        ----------
        desc : bool
            If True, order descending. Default is ascending.
        """
        return OrderModifier(self, desc=desc)

    def fork(
        self,
        default: Undefined | FieldValueTV = _undefined,
        default_factory: Opt[typing.Callable[[], FieldValueTV]] = None,
        vtype: Undefined | typing.Type[FieldValueTV] = _undefined,
        name: Opt[str] = None,
        in_model_name: Opt[str] = None,
        model_cls: Opt[typing.Type] = None,
        is_key: bool = False,
        is_key_natural: bool = False,
        is_foreign_key: bool = False,
        converter: Opt[BaseConverter[FieldValueTV]] = None,
        fork_validators: bool = False,
        is_partial: Opt[bool] = None,
        dump_flags: Opt[set[str]] = None,
        init: Opt[bool] = None,
        # SQL-specific properties
        column_name: Opt[str] = None,
        column_type: Opt[str] = None,
        nullable: Opt[bool] = None,
        primary_key: Opt[bool] = None,
        auto_increment: Opt[bool] = None,
        unique: Opt[bool] = None,
        index: Opt[bool] = None,
        foreign_key: Opt[str] = None,
        default_sql: Opt[str] = None,
        check_constraint: Opt[str] = None,
    ) -> typing.Self:
        """Create a copy of this column with optional overrides."""
        parent_fork = super().fork(
            default=default,
            default_factory=default_factory,
            vtype=vtype,
            name=name,
            in_model_name=in_model_name,
            model_cls=model_cls,
            is_key=is_key,
            is_key_natural=is_key_natural,
            is_foreign_key=is_foreign_key,
            converter=converter,
            fork_validators=fork_validators,
            is_partial=is_partial,
            dump_flags=dump_flags,
            init=init,
        )

        # Create a Column from the parent fork
        return Column(
            default=parent_fork._Field__default,
            default_factory=parent_fork._Field__default_factory,
            vtype=parent_fork._Field__vtype,
            name=parent_fork._Field__name,
            in_model_name=parent_fork._Field__in_model_name,
            model_cls=parent_fork._Field__model_cls,
            is_key=parent_fork._Field__is_key,
            is_key_natural=parent_fork._Field__is_key_natural,
            is_foreign_key=parent_fork._Field__is_foreign_key,
            converter=parent_fork._Field__converter,
            validators=parent_fork._Field__validators if fork_validators else None,
            is_partial=parent_fork._Field__is_partial,
            dump_flags=parent_fork._Field__dump_flags,
            init=parent_fork._Field__init,
            column_name=column_name or self.__column_name,
            column_type=column_type or self.__column_type,
            nullable=nullable if nullable is not None else self.__nullable,
            primary_key=primary_key if primary_key is not None else self.__primary_key,
            auto_increment=auto_increment if auto_increment is not None else self.__auto_increment,
            unique=unique if unique is not None else self.__unique,
            index=index if index is not None else self.__index,
            foreign_key=foreign_key or self.__foreign_key,
            default_sql=default_sql or self.__default_sql,
            check_constraint=check_constraint or self.__check_constraint,
        )


T = typing.TypeVar('T')

def column(
    default: T | Undefined = _undefined,
    default_factory: Opt[typing.Callable[[], T]] = None,
    name: Opt[str] = None,
    is_key: bool = False,
    is_natural_key: bool = False,
    is_foreign_key: bool = False,
    converter: Opt[BaseConverter] = None,
    validators: Opt[typing.Iterable] = None,
    is_partial: bool = False,
    dump_flags: Opt[set[str]] = None,
    init: bool = True,
    # SQL-specific properties
    column_name: Opt[str] = None,
    column_type: Opt[str] = None,
    nullable: bool = True,
    primary_key: bool = False,
    auto_increment: bool = False,
    unique: bool = False,
    index: bool = False,
    foreign_key: Opt[str] = None,
    default_sql: Opt[str] = None,
    check_constraint: Opt[str] = None,
) -> Column[T]:
    """Create a Column with the specified properties.

    This is a convenience function for creating Column instances.

    Examples
    --------
    >>> class User(DALModel):
    ...     _id: Column[int] = column(primary_key=True, auto_increment=True)
    ...     name: Column[str] = column(column_type="VARCHAR(255)", nullable=False)
    """
    return Column[T](
        default=default,
        default_factory=default_factory,
        name=name,
        is_key=is_key or is_natural_key or primary_key,
        is_key_natural=is_natural_key or (primary_key and not auto_increment),
        is_foreign_key=is_foreign_key or (foreign_key is not None),
        converter=converter,
        validators=validators,
        is_partial=is_partial,
        dump_flags=dump_flags,
        init=init,
        column_name=column_name,
        column_type=column_type,
        nullable=nullable,
        primary_key=primary_key,
        auto_increment=auto_increment,
        unique=unique,
        index=index,
        foreign_key=foreign_key,
        default_sql=default_sql,
        check_constraint=check_constraint,
    )
