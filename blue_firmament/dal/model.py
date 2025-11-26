"""BF DAL Model

DALModel extends BaseModel with DAL-specific functionality for database operations.
"""

__all__ = [
    "DALModel",
    "DALModelTV",
]

import typing
from typing import Optional as Opt

from ..model.main import BaseModel, BFModelMetaclass, ModelTV

if typing.TYPE_CHECKING:
    from .types import DALPath
    from .query_components.filters import EqFilter
    from .query_components import DALQueryComponent
    from .base import DataAccessLayer


class DALModel(BaseModel):
    """Data Access Layer Model - BaseModel with DAL integration.

    Extends BaseModel with DAL-specific functionality:
    - DAL class configuration
    - DAL path management
    - DAL query helpers (equals, key filters)

    Class Attributes
    ----------------
    __dal__: Type[DataAccessLayer]
        The DAL class to use for database operations.
    __dal_path__: DALPath
        The path for DAL operations (e.g., table name).
    __table_name__: str
        Alias for DAL path's table component.
    __schema_name__: str
        Alias for DAL path's schema component.

    Examples
    --------
    >>> class User(DALModel, dal_path=("users",)):
    ...     _id: Column[int] = column(primary_key=True)
    ...     name: Column[str] = column(nullable=False)
    ...
    >>> # Access DAL path
    >>> User.dal_path()
    ('users',)
    >>> # Get key field
    >>> User._get_key_field()
    Column[int](name='_id', primary_key=True)
    """

    # DAL-related class variables
    __dal__: typing.ClassVar[Opt[typing.Type["DataAccessLayer"]]] = None
    __dal_path__: typing.ClassVar[Opt["DALPath"]] = None
    __table_name__: typing.ClassVar[Opt[str]] = None
    __schema_name__: typing.ClassVar[Opt[str]] = None

    def __init_subclass__(
        cls,
        dal_path: Opt["DALPath"] = None,
        dal: Opt[typing.Type["DataAccessLayer"]] = None,
        table_name: Opt[str] = None,
        schema_name: Opt[str] = None,
        **kwargs
    ):
        """Initialize DALModel subclass with DAL configuration.

        Parameters
        ----------
        dal_path : DALPath, optional
            The path for DAL operations.
        dal : Type[DataAccessLayer], optional
            The DAL class to use.
        table_name : str, optional
            Table name (alternative to dal_path).
        schema_name : str, optional
            Schema/database name.
        """
        super().__init_subclass__(**kwargs)

        if dal_path is not None:
            cls.__dal_path__ = dal_path
        if dal is not None:
            cls.__dal__ = dal
        if table_name is not None:
            cls.__table_name__ = table_name
        if schema_name is not None:
            cls.__schema_name__ = schema_name

        # Build dal_path from table_name and schema_name if not provided
        if cls.__dal_path__ is None and cls.__table_name__ is not None:
            if cls.__schema_name__ is not None:
                cls.__dal_path__ = (cls.__schema_name__, cls.__table_name__)
            else:
                cls.__dal_path__ = (cls.__table_name__,)

    @classmethod
    def dal_path(cls) -> "DALPath":
        """Get the DAL path for this model.

        Returns
        -------
        DALPath
            The path for DAL operations.

        Raises
        ------
        ValueError
            If DAL path is not configured.
        """
        if not cls.__dal_path__:
            raise ValueError(f"dal_path not configured for {cls.__name__}")
        return cls.__dal_path__

    @classmethod
    def table_name(cls) -> str:
        """Get the table name from DAL path.

        Returns
        -------
        str
            The table name.

        Raises
        ------
        ValueError
            If DAL path is not configured.
        """
        if cls.__table_name__:
            return cls.__table_name__
        path = cls.dal_path()
        return path[-1] if path else ""

    @classmethod
    def schema_name(cls) -> Opt[str]:
        """Get the schema name from DAL path.

        Returns
        -------
        str or None
            The schema name, or None if not configured.
        """
        if cls.__schema_name__:
            return cls.__schema_name__
        path = cls.__dal_path__
        if path and len(path) > 1:
            return path[0]
        return None

    @classmethod
    def get_dal_class(cls) -> typing.Type["DataAccessLayer"]:
        """Get the configured DAL class.

        Returns
        -------
        Type[DataAccessLayer]
            The DAL class.

        Raises
        ------
        ValueError
            If DAL class is not configured.
        """
        if cls.__dal__ is None:
            raise ValueError(f"DAL class not configured for {cls.__name__}")
        return cls.__dal__

    @classmethod
    def has_dal(cls) -> bool:
        """Check if DAL is configured for this model."""
        return cls.__dal__ is not None

    @classmethod
    def has_dal_path(cls) -> bool:
        """Check if DAL path is configured for this model."""
        return cls.__dal_path__ is not None

    def equals(self) -> typing.Tuple["DALQueryComponent", ...]:
        """Get EqFilter for all fields.

        Returns
        -------
        Tuple[DALQueryComponent, ...]
            A tuple of EqFilters for all fields.
        """
        return tuple(
            field.equals(self._get_value(field))
            for field in self.__fields__.values()
        )

    @property
    def key_value(self) -> typing.Any:
        """Get the value of the key field.

        Returns
        -------
        Any
            The key field value.

        Raises
        ------
        KeyError
            If no key field is defined.
        """
        return self._get_value(self._get_key_field())

    @property
    def key_eqf(self) -> "EqFilter":
        """Get an EqFilter for the key field.

        Returns
        -------
        EqFilter
            An EqFilter for the key field.

        Raises
        ------
        KeyError
            If no key field is defined.
        """
        key_field = self._get_key_field()
        return key_field.equals(self._get_value(key_field))

    def dump_to_insert_dict(
        self,
        exclude_auto_increment: bool = True,
    ) -> dict:
        """Dump model to dict suitable for INSERT operations.

        Parameters
        ----------
        exclude_auto_increment : bool
            Whether to exclude auto-increment fields (natural keys).

        Returns
        -------
        dict
            Dictionary suitable for INSERT operations.
        """
        from ..model.converter import ModelConverter
        converter = ModelConverter(self.__class__)
        data = converter.dump_to_dict(self)
        
        # DAL-specific: exclude natural key if requested
        if exclude_auto_increment:
            key_field = self._try_get_key_field()
            if key_field and key_field.is_key_natural():
                data.pop(key_field.in_model_name, None)
        
        return data

    def dump_to_update_dict(
        self,
        only_dirty: bool = True,
    ) -> dict:
        """Dump model to dict suitable for UPDATE operations.

        Parameters
        ----------
        only_dirty : bool
            Whether to only include dirty fields.

        Returns
        -------
        dict
            Dictionary suitable for UPDATE operations.
        """
        from ..model.converter import ModelConverter
        converter = ModelConverter(self.__class__)
        return converter.dump_to_dict(self, only_dirty=only_dirty)


DALModelTV = typing.TypeVar('DALModelTV', bound=DALModel)
"""DAL Model type variable."""
