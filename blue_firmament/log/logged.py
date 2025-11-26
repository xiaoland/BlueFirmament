"""LoggedModel - BaseModel with logging functionality

This module separates observation/logging responsibilities from BaseModel.
"""

__all__ = [
    "LoggedModel",
]

import typing
from typing import Optional as Opt, Callable

from ..model.main import BaseModel, BFModelMetaclass

if typing.TYPE_CHECKING:
    from .types import LoggerT


class LoggedModelMetaclass(BFModelMetaclass):
    """Metaclass for LoggedModel that adds logging to initialization."""
    
    __builtin_ivars__ = BFModelMetaclass.__builtin_ivars__.copy()
    __builtin_ivars__['__logger__'] = None
    
    def __new__(
        cls, name: str,
        bases: typing.Tuple[type[typing.Any], ...],
        attrs: typing.Dict[str, typing.Any],
        logger_factory: Opt[Callable[[str], "LoggerT"]] = None,
        **kwargs
    ):
        # Exclude base LoggedModel class
        if name == "LoggedModel":
            return super().__new__(cls, name, bases, attrs, **kwargs)
            
        # Store logger_factory in class if provided
        if logger_factory is not None:
            attrs["__logger_factory__"] = logger_factory
            
        return super().__new__(cls, name, bases, attrs, **kwargs)


class LoggedModel(BaseModel, metaclass=LoggedModelMetaclass):
    """Model with logging capabilities.
    
    Extends BaseModel with logging functionality. Use this when you want
    your model to automatically log instantiation and other events.
        
    Instance Variables  
    ------------------
    __logger__: Optional[LoggerT]
        Model-level logger instance.
    
    Class Variables
    ---------------
    __logger_factory__: Optional[Callable[[str], LoggerT]]
        Factory function to create logger instances. If not provided,
        uses the default logger factory from the log module.
    
    Examples
    --------
    >>> from blue_firmament.log import LoggedModel
    >>> 
    >>> class User(LoggedModel):
    ...     name: str
    ...     email: str
    >>> 
    >>> user = User(name="John", email="john@example.com")
    # This will log: "Model instantiated" with model_data
    
    >>> # With custom logger factory
    >>> class CustomLoggedUser(LoggedModel, logger_factory=my_custom_factory):
    ...     name: str
    """
    
    # Instance variable - note: Not using ClassVar as this should be per-instance
    __logger__: Opt["LoggerT"] = None
    """Model level logger
    
    - Instance variable
    """
    
    # Class variable for logger factory
    __logger_factory__: typing.ClassVar[Opt[Callable[[str], "LoggerT"]]] = None
    """Logger factory function"""
    
    def __post_init__(self) -> None:
        """Log model instantiation after init."""
        super().__post_init__()
        
        # Initialize logger using factory
        factory = self.__class__.__logger_factory__
        if factory is not None:
            self.__logger__ = factory(self.__class__.__name__)
        else:
            # Default logger factory logic
            from . import get_logger
            logger = get_logger(self.__class__.__name__)
            self.__logger__ = logger.bind(model_id=id(self))
        
        # Log instantiation using ModelConverter
        from ..model.converter import ModelConverter
        converter = ModelConverter(self.__class__)
        self.__logger__.info("Model instantiated", model_data=converter.dump_to_dict(self))
