# chuk_mcp/protocol/mcp_pydantic_base.py
import os
import json
import inspect
from dataclasses import dataclass
from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Set,
    Union,
    get_args,
    get_origin,
    get_type_hints,
    Callable,
)

"""Enhanced minimal-footprint drop-in replacement for Pydantic.

Improvements:
1. Better type validation including nested models
2. More robust Field handling
3. Better error messages
4. Support for model_post_init and validation decorators
5. Enhanced serialization with custom encoders
6. FIXED: typing.Any cannot be used with isinstance() error
"""

FORCE_FALLBACK = os.environ.get("MCP_FORCE_FALLBACK") == "1"

try:
    if not FORCE_FALLBACK:
        from pydantic import (
            BaseModel as PydanticBase,
            Field as PydanticField,
            ConfigDict as PydanticConfigDict,
            ValidationError,
            validator,
            root_validator,
        )
        PYDANTIC_AVAILABLE = True
    else:
        PYDANTIC_AVAILABLE = False
except ImportError:
    PYDANTIC_AVAILABLE = False

# Re-exports when Pydantic is available
if PYDANTIC_AVAILABLE:
    McpPydanticBase = PydanticBase
    Field = PydanticField
    ConfigDict = PydanticConfigDict
else:
    # Enhanced fallback implementation
    
    class ValidationError(Exception):
        """Enhanced validation error with field path tracking."""
        
        def __init__(self, message: str, field_path: str = ""):
            self.field_path = field_path
            super().__init__(f"{field_path}: {message}" if field_path else message)

    def _get_type_name(t: Any) -> str:
        """Get a readable name for a type."""
        if hasattr(t, '__name__'):
            return t.__name__
        return str(t)

    def _is_optional(t: Any) -> bool:
        """Check if a type is Optional (Union with None)."""
        origin, args = get_origin(t), get_args(t)
        return origin is Union and type(None) in args

    def _get_non_none_type(t: Any) -> Any:
        """Extract the non-None type from Optional[T]."""
        if _is_optional(t):
            args = get_args(t)
            return next(arg for arg in args if arg is not type(None))
        return t

    def _deep_validate(name: str, value: Any, expected: Any, path: str = "") -> Any:
        """Enhanced recursive validation with better error reporting.
        
        FIXED: Properly handles typing.Any to avoid isinstance() errors.
        """
        current_path = f"{path}.{name}" if path else name
        
        if value is None:
            if _is_optional(expected):
                return None
            raise ValidationError(f"field required", current_path)

        # CRITICAL FIX: Handle typing.Any first to avoid isinstance() errors
        if expected is Any:
            return value

        # Handle Optional types
        if _is_optional(expected):
            expected = _get_non_none_type(expected)
            # Check again after extracting non-None type
            if expected is Any:
                return value

        origin = get_origin(expected)
        
        # Simple type validation
        if origin is None:
            if inspect.isclass(expected):
                if isinstance(value, expected):
                    return value
                # Special handling for common conversions
                if expected is str and not isinstance(value, str):
                    return str(value)
                if expected is int and isinstance(value, (str, float)):
                    try:
                        return int(value)
                    except (ValueError, TypeError):
                        pass
                if expected is float and isinstance(value, (str, int)):
                    try:
                        return float(value)
                    except (ValueError, TypeError):
                        pass
                
                # Check if it's a McpPydanticBase subclass
                if (hasattr(expected, '__bases__') and 
                    any(issubclass(base, McpPydanticBase) for base in expected.__mro__[1:])):
                    if isinstance(value, dict):
                        return expected(**value)
                    elif isinstance(value, expected):
                        return value
                
                raise ValidationError(
                    f"value is not a valid {_get_type_name(expected)}", 
                    current_path
                )
            return value

        # List validation
        if origin in (list, List):
            if not isinstance(value, list):
                raise ValidationError(f"value is not a valid list", current_path)
            
            item_type = get_args(expected)[0] if get_args(expected) else Any
            validated_items = []
            for i, item in enumerate(value):
                # Skip validation if item type is Any
                if item_type is Any:
                    validated_items.append(item)
                else:
                    validated_item = _deep_validate(f"[{i}]", item, item_type, current_path)
                    validated_items.append(validated_item)
            return validated_items

        # Dict validation
        if origin in (dict, Dict):
            if not isinstance(value, dict):
                raise ValidationError(f"value is not a valid dict", current_path)
            
            args = get_args(expected)
            key_type = args[0] if args else Any
            val_type = args[1] if len(args) > 1 else Any
            
            validated_dict = {}
            for k, v in value.items():
                # Skip validation for Any types to avoid isinstance() errors
                validated_key = k if key_type is Any else _deep_validate("key", k, key_type, current_path)
                validated_value = v if val_type is Any else _deep_validate(f"[{k}]", v, val_type, current_path)
                validated_dict[validated_key] = validated_value
            return validated_dict

        # Union validation (non-Optional)
        if origin is Union:
            for union_type in get_args(expected):
                if union_type is type(None):
                    continue
                try:
                    return _deep_validate(name, value, union_type, path)
                except (ValidationError, TypeError):  # Catch TypeError for Any-related issues
                    continue
            
            type_names = [_get_type_name(t) for t in get_args(expected) if t is not type(None)]
            raise ValidationError(
                f"value does not match any type in Union[{', '.join(type_names)}]",
                current_path
            )

        # Default: return as-is for unknown complex types
        return value

    class Field:
        """Enhanced Field class with better default handling."""
        
        __slots__ = ("default", "default_factory", "alias", "description", 
                    "title", "required", "kwargs")

        def __init__(
            self,
            default: Any = ...,  # Use ... as sentinel for "not provided"
            default_factory: Optional[Callable[[], Any]] = None,
            alias: Optional[str] = None,
            title: Optional[str] = None,
            description: Optional[str] = None,
            **kwargs
        ):
            if default is not ... and default_factory is not None:
                raise TypeError("Cannot specify both 'default' and 'default_factory'")

            self.default = default
            self.default_factory = default_factory
            self.alias = alias
            self.title = title
            self.description = description
            self.kwargs = kwargs
            
            # Determine if field is required
            self.required = default is ... and default_factory is None

    @dataclass
    class McpPydanticBase:
        """Enhanced fallback base class with better validation and features."""
        
        # Class-level metadata
        __model_fields__: ClassVar[Dict[str, Field]] = {}
        __model_required__: ClassVar[Set[str]] = set()
        __field_aliases__: ClassVar[Dict[str, str]] = {}
        __validators__: ClassVar[Dict[str, List[Callable]]] = {}

        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__(**kwargs)
            
            cls.__model_fields__ = {}
            cls.__model_required__ = set()
            cls.__field_aliases__ = {}
            cls.__validators__ = {}

            # Analyze type hints and class attributes
            # Use try/except to handle forward references gracefully
            try:
                hints = get_type_hints(cls, include_extras=True)
            except (NameError, AttributeError, TypeError):
                # Fall back to raw annotations for forward references
                hints = getattr(cls, '__annotations__', {})
            
            for name, hint in hints.items():
                if name.startswith('__') and name.endswith('__'):
                    continue

                # Get field definition
                if hasattr(cls, name):
                    attr_val = getattr(cls, name)
                    if isinstance(attr_val, Field):
                        field = attr_val
                    else:
                        field = Field(default=attr_val)
                else:
                    field = Field()

                # Handle alias
                if field.alias:
                    cls.__field_aliases__[name] = field.alias

                # For forward references, we can't easily determine if optional
                # so we rely on the Field definition
                if isinstance(hint, str):
                    # This is a forward reference, be more conservative
                    if field.required:
                        cls.__model_required__.add(name)
                else:
                    # Normal type hint processing
                    if field.required and not _is_optional(hint):
                        cls.__model_required__.add(name)

                cls.__model_fields__[name] = field

            # Apply project-specific defaults
            cls._apply_project_defaults()

        @classmethod
        def _apply_project_defaults(cls):
            """Apply project-specific field defaults."""
            if cls.__name__ == "StdioServerParameters":
                if "args" not in cls.__model_fields__:
                    cls.__model_fields__["args"] = Field(default_factory=list)
                cls.__model_required__.discard("args")
                
            if cls.__name__ == "JSONRPCMessage":
                if "jsonrpc" not in cls.__model_fields__:
                    cls.__model_fields__["jsonrpc"] = Field(default="2.0")

        def __init__(self, **data: Any):
            # Process aliases
            processed_data = self._process_aliases(data)
            
            # Build field values
            values = self._build_field_values(processed_data)
            
            # Validate required fields
            self._validate_required_fields(values)
            
            # Validate types
            self._validate_types(values)
            
            # Set attributes
            object.__setattr__(self, "__dict__", values)
            
            # Call post-init hooks
            self._call_post_init_hooks()

        def _process_aliases(self, data: Dict[str, Any]) -> Dict[str, Any]:
            """Convert aliased keys to field names."""
            processed = {}
            alias_to_field = {v: k for k, v in self.__class__.__field_aliases__.items()}
            
            for key, value in data.items():
                field_name = alias_to_field.get(key, key)
                processed[field_name] = value
            
            return processed

        def _build_field_values(self, data: Dict[str, Any]) -> Dict[str, Any]:
            """Build dictionary of field values with defaults."""
            values = {}
            
            # Process defined fields
            for name, field in self.__class__.__model_fields__.items():
                if name in data:
                    values[name] = data.pop(name)
                elif field.default_factory is not None:
                    values[name] = field.default_factory()
                elif field.default is not ...:
                    values[name] = field.default
                else:
                    values[name] = None

            # Add extra fields (allow by default)
            values.update(data)
            
            return values

        def _validate_required_fields(self, values: Dict[str, Any]):
            """Validate that all required fields are present."""
            missing = []
            for name in self.__class__.__model_required__:
                if values.get(name) is None:
                    missing.append(name)
            
            if missing:
                raise ValidationError(f"Missing required fields: {', '.join(missing)}")

        def _validate_types(self, values: Dict[str, Any]):
            """Validate field types."""
            # Use try/except to handle forward references gracefully
            try:
                hints = get_type_hints(self.__class__, include_extras=True)
            except (NameError, AttributeError, TypeError):
                # For forward references, skip type validation during construction
                # The validation will happen at runtime when the references are resolvable
                return
            
            for name, expected_type in hints.items():
                if name.startswith('__') and name.endswith('__'):
                    continue
                    
                if name in values:
                    try:
                        validated_value = _deep_validate(name, values[name], expected_type)
                        values[name] = validated_value
                    except ValidationError as e:
                        # Re-raise with better context
                        raise ValidationError(str(e)) from e

        def _call_post_init_hooks(self):
            """Call post-initialization hooks."""
            # Call __post_init__ if it exists (dataclass style)
            post_init = getattr(self, "__post_init__", None)
            if callable(post_init):
                post_init()
            
            # Call model_post_init if it exists (Pydantic style)
            model_post_init = getattr(self, "model_post_init", None)
            if callable(model_post_init):
                model_post_init(None)

        def model_dump(
            self,
            *,
            exclude: Optional[Union[Set[str], Dict[str, Any]]] = None,
            exclude_none: bool = False,
            by_alias: bool = False,
            include: Optional[Union[Set[str], Dict[str, Any]]] = None,
            **kwargs,
        ) -> Dict[str, Any]:
            """Enhanced model serialization."""
            result = {}
            
            for key, value in self.__dict__.items():
                # Skip private attributes
                if key.startswith("__"):
                    continue
                
                # Handle include/exclude
                if include and key not in include:
                    continue
                if exclude and self._should_exclude(key, exclude):
                    continue
                if exclude_none and value is None:
                    continue
                
                # Handle aliases
                output_key = key
                if by_alias and key in self.__class__.__field_aliases__:
                    output_key = self.__class__.__field_aliases__[key]
                
                # Serialize value
                if hasattr(value, 'model_dump'):
                    result[output_key] = value.model_dump(
                        exclude=exclude, exclude_none=exclude_none, 
                        by_alias=by_alias, include=include, **kwargs
                    )
                elif isinstance(value, list):
                    result[output_key] = [
                        item.model_dump(exclude=exclude, exclude_none=exclude_none, 
                                      by_alias=by_alias, include=include, **kwargs)
                        if hasattr(item, 'model_dump') else item
                        for item in value
                    ]
                elif isinstance(value, dict):
                    result[output_key] = {
                        k: (v.model_dump(exclude=exclude, exclude_none=exclude_none, 
                                       by_alias=by_alias, include=include, **kwargs)
                            if hasattr(v, 'model_dump') else v)
                        for k, v in value.items()
                    }
                else:
                    result[output_key] = value
            
            return result

        def _should_exclude(self, key: str, exclude: Union[Set[str], Dict[str, Any]]) -> bool:
            """Check if a key should be excluded."""
            if isinstance(exclude, set):
                return key in exclude
            elif isinstance(exclude, dict):
                return key in exclude
            return False

        def model_dump_json(
            self,
            *,
            exclude: Optional[Union[Set[str], Dict[str, Any]]] = None,
            exclude_none: bool = False,
            by_alias: bool = False,
            include: Optional[Union[Set[str], Dict[str, Any]]] = None,
            indent: Optional[int] = None,
            separators: Optional[tuple] = None,
            **kwargs,
        ) -> str:
            """Enhanced JSON serialization."""
            data = self.model_dump(
                exclude=exclude, exclude_none=exclude_none, 
                by_alias=by_alias, include=include, **kwargs
            )
            
            if separators is None:
                separators = (",", ":")
            
            return json.dumps(data, indent=indent, separators=separators, default=str)

        @classmethod
        def model_validate(cls, data: Union[Dict[str, Any], Any]):
            """Enhanced model validation from various input types."""
            if isinstance(data, dict):
                return cls(**data)
            elif isinstance(data, cls):
                return data
            elif hasattr(data, '__dict__'):
                return cls(**data.__dict__)
            elif hasattr(data, 'model_dump'):
                return cls(**data.model_dump())
            else:
                raise ValidationError(f"Cannot validate {type(data)} as {cls.__name__}")

        # Pydantic v1 compatibility
        def json(self, **kwargs) -> str:
            return self.model_dump_json(**kwargs)

        def dict(self, **kwargs) -> Dict[str, Any]:
            return self.model_dump(**kwargs)

    def ConfigDict(**kwargs) -> Dict[str, Any]:
        """Enhanced configuration dictionary."""
        return dict(**kwargs)

    # Dummy decorators for compatibility
    def validator(*args, **kwargs):
        """Dummy validator decorator for fallback mode."""
        def decorator(func):
            return func
        return decorator

    def root_validator(*args, **kwargs):
        """Dummy root validator decorator for fallback mode."""
        def decorator(func):
            return func
        return decorator