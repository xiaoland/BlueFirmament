"""Scheme for business
"""

__all__ = [
    "BusinessScheme",
    "EditableScheme"
]

import typing
from typing import Optional as Opt, Annotated as Anno, Literal as Lit
from blue_firmament.dal.base import DataAccessLayer
from blue_firmament.dal.types import DALPath
from ..dal.types import KeyableType
from .field import field, Field as FieldT
from .main import BaseScheme, NoProxyScheme


KeyTV = typing.TypeVar('KeyTV', bound=KeyableType)
class BusinessScheme(
    typing.Generic[KeyTV],
    BaseScheme, 
):
    
    def __init_subclass__(cls, 
        key_type: Opt[typing.Type[KeyTV]] = None,
        **kwargs
    ) -> None:
        super().__init_subclass__(**kwargs)
        if key_type:
            cls._id._set_converter_from_anno(key_type)

    _id: FieldT[KeyTV] = field(is_key=True)

    @property
    def _inserted(self):
        """Is this instance inserted to P.DAL

        Behaviours
        ----------
        >>> BusinessScheme(_id=1)._inserted
        True
        >>> BusinessScheme(_id='abcd')._inserted
        True
        >>> BusinessScheme(_id=0)._inserted
        False
        >>> BusinessScheme(_id='')._inserted
        False
        >>> BusinessScheme(_id=CID(ida=1, idb=None))._inserted
        False
        >>> BusinessScheme(_id=CID(ida=1, idb='cc'))._inserted
        True
        """
        if isinstance(self._id, int):
            return self._id != 0
        if isinstance(self._id, str):
            return self._id != ''
        if isinstance(self._id, BaseScheme):
            return all(
                bool(i)
                for i in self._id.__field_values__.values()
            )
        return False


class EditableScheme(
    NoProxyScheme,
    partial=True,
    inherit_validators=True             
):
    pass
