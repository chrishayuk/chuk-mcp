# chuk_mcp/mcp_client/mcp_pydantic_base.py
import os
import json
import inspect
from typing import get_type_hints, get_origin, get_args, List, Dict, Optional, Union, Set, Any

# Use fallback only if explicitly forced.
FORCE_FALLBACK = os.environ.get("MCP_FORCE_FALLBACK") == "1"

try:
    if not FORCE_FALLBACK:
        from pydantic import BaseModel as PydanticBase, Field as PydanticField, ConfigDict as PydanticConfigDict
        from pydantic import ValidationError
        PYDANTIC_AVAILABLE = True
    else:
        PYDANTIC_AVAILABLE = False
except ImportError:
    PYDANTIC_AVAILABLE = False

# Custom exception to mimic Pydantic's ValidationError - defined outside the if/else block
# so it's always available for import
class ValidationError(Exception):
    pass

if PYDANTIC_AVAILABLE:
    # Use real Pydantic.
    McpPydanticBase = PydanticBase
    Field = PydanticField
    ConfigDict = PydanticConfigDict
    # We imported ValidationError from pydantic above, don't need to redefine
else:
    # Fallback implementation
    from dataclasses import dataclass
    from typing import Dict, Any, Optional, Set, Union

    # ValidationError is already defined above
    
    class Field:
        """
        Minimal stand-in for pydantic.Field(...), tracking default and default_factory.
        """
        def __init__(self, default=None, default_factory=None, **kwargs):
            self.default = default
            self.default_factory = default_factory
            self.kwargs = kwargs
            self.required = default is None and default_factory is None and kwargs.get('required', False)

    @dataclass
    class McpPydanticBase:
        """
        Minimal fallback base class with Pydantic-like methods.
        """
        def __post_init__(self):
            cls = self.__class__
            # If not already set up, initialize __model_fields__ and __model_init_required__.
            if not hasattr(cls, '__model_fields__'):
                cls.__model_fields__ = {}
                cls.__model_init_required__ = set()
                annotations = cls.__annotations__ if hasattr(cls, '__annotations__') else {}
                for name, type_hint in annotations.items():
                    if name in cls.__dict__:
                        value = cls.__dict__[name]
                        if isinstance(value, Field):
                            cls.__model_fields__[name] = value
                            if value.required:
                                cls.__model_init_required__.add(name)
                        else:
                            cls.__model_fields__[name] = Field(default=value)
                    else:
                        cls.__model_fields__[name] = Field(default=None, required=True)
                        cls.__model_init_required__.add(name)
    
            # Convert nested dicts into model instances if the annotation appears to be a model.
            for name, type_hint in self.__annotations__.items():
                val = self.__dict__.get(name)
                if val is not None and isinstance(val, dict) and hasattr(type_hint, '__annotations__'):
                    try:
                        self.__dict__[name] = type_hint(**val)
                    except Exception:
                        pass
    
            # Replace any Field objects with their default or default_factory values.
            for key, value in list(self.__dict__.items()):
                if isinstance(value, Field):
                    if value.default_factory is not None:
                        self.__dict__[key] = value.default_factory()
                    else:
                        self.__dict__[key] = value.default
    
            # Validate required fields.
            if hasattr(self.__class__, '__model_init_required__'):
                missing = []
                for field_name in self.__class__.__model_init_required__:
                    if field_name not in self.__dict__ or self.__dict__[field_name] is None:
                        missing.append(field_name)
                if missing:
                    raise ValidationError(f"Missing required fields: {', '.join(missing)}")
            
            # Perform type validation based on type hints
            self._validate_types()
    
        def _validate_types(self):
            """Validate field types based on type annotations"""
            annotations = get_type_hints(self.__class__)
            
            for field_name, expected_type in annotations.items():
                # Skip validation if the field is not set
                if field_name not in self.__dict__:
                    continue
                    
                value = self.__dict__[field_name]
                
                # Skip validation for None values if the field is Optional
                if value is None:
                    origin = get_origin(expected_type)
                    args = get_args(expected_type)
                    if origin is Union and type(None) in args:
                        continue
                    # If the field is not Optional and the value is None, validation is handled elsewhere
                    continue
                
                # Handle Optional types by extracting the actual type
                origin = get_origin(expected_type)
                args = get_args(expected_type)
                
                if origin is Union and type(None) in args:
                    # It's an Optional type, extract the actual type(s)
                    non_none_types = [t for t in args if t is not type(None)]
                    if len(non_none_types) == 1:
                        expected_type = non_none_types[0]
                        origin = get_origin(expected_type)
                        args = get_args(expected_type)
                
                # Handle List, Dict and other container types
                if origin is list or origin is List:
                    if not isinstance(value, list):
                        raise ValidationError(f"{field_name} must be a list")
                elif origin is dict or origin is Dict:
                    if not isinstance(value, dict):
                        raise ValidationError(f"{field_name} must be a dictionary")
                elif expected_type is str or expected_type == str:
                    if not isinstance(value, str):
                        raise ValidationError(f"{field_name} must be a string")
                elif expected_type is int or expected_type == int:
                    if not isinstance(value, int):
                        raise ValidationError(f"{field_name} must be an integer")
                elif expected_type is float or expected_type == float:
                    if not isinstance(value, (int, float)):
                        raise ValidationError(f"{field_name} must be a number")
                elif expected_type is bool or expected_type == bool:
                    if not isinstance(value, bool):
                        raise ValidationError(f"{field_name} must be a boolean")
        
        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__(**kwargs)
            cls.__model_fields__ = {}
            cls.__model_init_required__ = set()
            annotations = cls.__annotations__ if hasattr(cls, '__annotations__') else {}
            for name, type_hint in annotations.items():
                if name in cls.__dict__:
                    value = cls.__dict__[name]
                    if isinstance(value, Field):
                        cls.__model_fields__[name] = value
                        if value.required:
                            cls.__model_init_required__.add(name)
                    else:
                        cls.__model_fields__[name] = Field(default=value)
                else:
                    cls.__model_fields__[name] = Field(default=None, required=True)
                    cls.__model_init_required__.add(name)
            # Special case for StdioServerParameters: ensure args gets a default_factory of list.
            if cls.__name__ == 'StdioServerParameters':
                cls.__model_fields__['args'] = Field(default_factory=list)
                cls.__model_init_required__.discard('args')
            # Special case for JSONRPCMessage: add jsonrpc field.
            if cls.__name__ == 'JSONRPCMessage':
                cls.__model_fields__['jsonrpc'] = Field(default="2.0")
    
        def __init__(self, **data: Any):
            cls = self.__class__
            if not hasattr(cls, '__model_fields__'):
                cls.__model_fields__ = {}
                cls.__model_init_required__ = set()
                annotations = cls.__annotations__ if hasattr(cls, '__annotations__') else {}
                for name, type_hint in annotations.items():
                    if name in cls.__dict__:
                        value = cls.__dict__[name]
                        if isinstance(value, Field):
                            cls.__model_fields__[name] = value
                            if value.required:
                                cls.__model_init_required__.add(name)
                        else:
                            cls.__model_fields__[name] = Field(default=value)
                    else:
                        cls.__model_fields__[name] = Field(default=None, required=True)
                        cls.__model_init_required__.add(name)
            # Initialize declared fields.
            self_dict = {}
            for name, field_obj in self.__class__.__model_fields__.items():
                if name in data:
                    self_dict[name] = data.pop(name)
                else:
                    if field_obj.default_factory is not None:
                        self_dict[name] = field_obj.default_factory()
                    else:
                        self_dict[name] = field_obj.default
            # Add extra fields.
            for k, v in data.items():
                self_dict[k] = v
            object.__setattr__(self, "__dict__", self_dict)
            if hasattr(self, '__post_init__'):
                self.__post_init__()
    
        def model_dump(self, *, exclude: Optional[Union[Set[str], Dict[str, Any]]] = None,
                       exclude_none: bool = False, **kwargs) -> Dict[str, Any]:
            result = {}
            for k, v in self.__dict__.items():
                # If v is a nested model, dump it as a dict.
                if isinstance(v, McpPydanticBase):
                    result[k] = v.model_dump()
                elif isinstance(v, Field):
                    if v.default_factory is not None:
                        result[k] = v.default_factory()
                    else:
                        result[k] = v.default
                else:
                    result[k] = v
            if exclude:
                if isinstance(exclude, set):
                    for field_name in exclude:
                        result.pop(field_name, None)
                elif isinstance(exclude, dict):
                    for field_name in exclude:
                        result.pop(field_name, None)
            if exclude_none:
                result = {k: v for k, v in result.items() if v is not None}
            return result
    
        def model_dump_json(self, *, exclude: Optional[Union[Set[str], Dict[str, Any]]] = None,
                            exclude_none: bool = False, indent: Optional[int] = None,
                            separators: Optional[tuple] = None, **kwargs) -> str:
            data = self.model_dump(exclude=exclude, exclude_none=exclude_none)
            # For JSONRPCMessage, force compact JSON.
            if self.__class__.__name__ == 'JSONRPCMessage':
                return json.dumps(data, separators=(',', ':'), indent=None)
            else:
                if separators is None:
                    separators = (',', ':')
                return json.dumps(data, indent=indent, separators=separators)
    
        def json(self, **kwargs):
            if self.__class__.__name__ == 'JSONRPCMessage':
                data = self.model_dump()
                return json.dumps(data, separators=(',', ':'))
            return self.model_dump_json(**kwargs)
    
        def dict(self, **kwargs):
            return self.model_dump(**kwargs)
    
        @classmethod
        def model_validate(cls, data: Dict[str, Any]):
            return cls(**data)
    
    def ConfigDict(**kwargs) -> Dict[str, Any]:
        return dict(**kwargs)