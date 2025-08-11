"""This module contains the operators for data access layer.
"""

import abc
import typing
from typing import Optional as Opt

from . import DALQueryComponent


class DALOperator(DALQueryComponent):
    """Abstract base class for DAL operators.

    Operators are logical constructs that combine or modify filters.
    """

class NotOperator(DALOperator):

    def dump_to_sql(self) -> str:
        return "NOT"

    def dump_to_postgrest(self) -> typing.Tuple[str, tuple]:
        return ("not_", ())

    def dump_to_postgrest_str(self) -> str:
        return "not"


class OrOperator(DALOperator):

    def __init__(self, *filters) -> None:
        super().__init__()
        if len(filters) < 2:
            raise ValueError("OrOperator requires at least two filters")
        self.__filters = filters

    def dump_to_sql(self) -> str:
        return "OR"

    def dump_to_postgrest(self) -> tuple[str, tuple]:
        return ("or_", (",".join(
            filter_.dump_to_postgrest_str()
            for filter_ in self.__filters
        ),))

    def dump_to_postgrest_str(self) -> str:
        return f"or({','.join(
            filter_.dump_to_postgrest_str() 
            for filter_ in self.__filters
        )})"
