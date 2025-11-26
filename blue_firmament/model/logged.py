"""LoggedModel - BaseModel with logging functionality

This module separates observation/logging responsibilities from BaseModel.
"""

__all__ = [
    "LoggedModel",
]

import typing
from typing import Optional as Opt

from .main import BaseModel, BFModelMetaclass

if typing.TYPE_CHECKING:
    from ..log import LoggerT


class LoggedModelMetaclass(BFModelMetaclass):
    """Metaclass for LoggedModel that adds logging to initialization."""
    
    __builtin_cvars__ = BFModelMetaclass.__builtin_cvars__.copy()
    __builtin_cvars__['__disable_log__'] = False
    
    __builtin_ivars__ = BFModelMetaclass.__builtin_ivars__.copy()
    __builtin_ivars__['__logger__'] = None
    
    def __new__(
        cls, name: str,
        bases: typing.Tuple[type[typing.Any], ...],
        attrs: typing.Dict[str, typing.Any],
        disable_log: Opt[bool] = None,
        **kwargs
    ):
        # Exclude base LoggedModel class
        if name == "LoggedModel":
            return super().__new__(cls, name, bases, attrs, **kwargs)
            
        # Set up class vars for logging
        if disable_log is not None:
            attrs["__disable_log__"] = disable_log
            
        return super().__new__(cls, name, bases, attrs, **kwargs)


class LoggedModel(BaseModel, metaclass=LoggedModelMetaclass):
    """Model with logging capabilities.
    
    Extends BaseModel with logging functionality. Use this when you want
    your model to automatically log instantiation and other events.
    
    Class Variables
    ---------------
    __disable_log__: bool
        If True, disables all logging for this model.
        
    Instance Variables  
    ------------------
    __logger__: Optional[LoggerT]
        Model-level logger instance.
    
    Examples
    --------
    >>> class User(LoggedModel):
    ...     name: str
    ...     email: str
    >>> 
    >>> user = User(name="John", email="john@example.com")
    # This will log: "Model instantiated" with model_data
    """
    
    # Class variable
    __disable_log__: typing.ClassVar[bool] = False
    """Disable model internal logs"""
    
    # Instance variable
    __logger__: typing.ClassVar[Opt["LoggerT"]] = None
    """Model level logger
    
    - Instance variable
    """
    
    def __post_init__(self) -> None:
        """Log model instantiation after init."""
        super().__post_init__()
        if not self.__disable_log__:
            self._logger.info("Model instantiated", model_data=self.dump_to_dict())
    
    @property
    def _logger(self) -> "LoggerT":
        """Model level logger

        Context:
        - model_id: id(self)
        """
        if not self.__logger__:
            from ..log import get_logger
            logger = get_logger(self.__class__.__name__)
            logger = logger.bind(
                model_id=id(self),
            )
            self.__logger__ = logger
        return self.__logger__
    
    def _set_logger(self, logger: "LoggerT") -> None:
        """Set model level logger"""
        self.__logger__ = logger
