# chuk_mcp/protocol/mcp_pydantic_base.py
import os
import inspect
from dataclasses import dataclass

# PERFORMANCE: Use fast JSON implementation (orjson if available, stdlib json fallback)
from chuk_mcp.protocol import fast_json as json
from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Union,
    get_args,
    get_origin,
    get_type_hints,
    Callable,
)

"""Enhanced minimal-footprint drop-in replacement for Pydantic.

This provides a clean, generic fallback implementation that:
1. Properly handles Union types and type aliases like RequestId
2. Provides strict validation that matches Pydantic behavior  
3. Supports all Pydantic API methods for compatibility
4. Has no domain-specific logic - purely generic validation
5. Handles forward references and complex type resolution
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

        # Check if we have Pydantic v2
        try:
            from pydantic import __version__ as pydantic_version

            PYDANTIC_V2 = pydantic_version.startswith("2.")
        except Exception:
            PYDANTIC_V2 = False

        PYDANTIC_AVAILABLE = True
    else:
        PYDANTIC_AVAILABLE = False
except ImportError:
    PYDANTIC_AVAILABLE = False

# Re-exports when Pydantic is available
if PYDANTIC_AVAILABLE:

    class McpPydanticBase(PydanticBase):
        """Enhanced Pydantic base class with standard configuration."""

        if PYDANTIC_V2:
            # Pydantic v2 configuration
            model_config = {
                "extra": "allow",
                "validate_assignment": True,
                "populate_by_name": True,
            }
        else:
            # Pydantic v1 configuration
            class Config:
                extra = "allow"
                validate_assignment = True
                allow_population_by_field_name = True

        def model_dump_mcp(self, **kwargs) -> Dict[str, Any]:
            """Convenience method for MCP compatibility."""
            if PYDANTIC_V2:
                return self.model_dump(**kwargs)
            else:
                return self.dict(**kwargs)

    Field = PydanticField
    ConfigDict = PydanticConfigDict
else:
    # Clean generic fallback implementation

    class ValidationError(Exception):  # type: ignore[no-redef]
        """Validation error with field path tracking."""

        def __init__(
            self,
            message: str,
            field_path: str = "",
            error_type: str = "validation_error",
        ):
            self.field_path = field_path
            self.error_type = error_type
            self.message = message
            super().__init__(f"{field_path}: {message}" if field_path else message)

        def __repr__(self):
            return f"ValidationError(message='{self.message}', field_path='{self.field_path}')"

    def _get_type_name(t: Any) -> str:
        """Get a readable name for a type."""
        if hasattr(t, "__name__"):
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

    def _resolve_type_alias(annotation, field_name=None, class_module=None):
        """Enhanced generic type alias resolution with debugging."""

        # If it already has an origin (like Union[str, int]), it's resolved
        if hasattr(annotation, "__origin__"):
            return annotation

        # Check if it's a string forward reference
        if isinstance(annotation, str):
            return annotation

        # For type aliases, try multiple resolution strategies
        if hasattr(annotation, "__name__"):
            alias_name = annotation.__name__

            # Strategy 1: Look in the class module's globals
            if class_module and hasattr(class_module, "__dict__"):
                module_dict = class_module.__dict__
                if alias_name in module_dict:
                    alias_value = module_dict[alias_name]
                    if hasattr(alias_value, "__origin__") or hasattr(
                        alias_value, "__args__"
                    ):
                        return alias_value

            # Strategy 2: Look in the annotation's own module
            if hasattr(annotation, "__module__"):
                try:
                    import sys

                    if annotation.__module__ in sys.modules:
                        module = sys.modules[annotation.__module__]
                        module_dict = getattr(module, "__dict__", {})
                        if alias_name in module_dict:
                            alias_value = module_dict[alias_name]
                            if hasattr(alias_value, "__origin__") or hasattr(
                                alias_value, "__args__"
                            ):
                                return alias_value
                except (ImportError, AttributeError, KeyError):
                    pass

            # Strategy 3: Global resolution attempt - check all imported modules
            # This is more aggressive but needed for cross-module type aliases
            try:
                import sys

                for module_name, module in sys.modules.items():
                    if (
                        module
                        and hasattr(module, "__dict__")
                        and alias_name in module.__dict__
                    ):
                        alias_value = module.__dict__[alias_name]
                        if hasattr(alias_value, "__origin__") or hasattr(
                            alias_value, "__args__"
                        ):
                            # Found the type alias in some module
                            return alias_value
            except (ImportError, AttributeError, KeyError):
                pass

            # Strategy 4: Check if the annotation itself has the resolved value
            if hasattr(annotation, "__args__") and hasattr(annotation, "__origin__"):
                return annotation

        return annotation

    # PERFORMANCE: Cache for Union type checks
    _union_type_cache: Dict[int, bool] = {}

    def _is_union_str_int(annotation):
        """Check if an annotation is Union[str, int] or Union[int, str].

        PERFORMANCE OPTIMIZED: Cached result to avoid repeated get_origin/get_args calls.
        """
        annotation_id = id(annotation)
        if annotation_id in _union_type_cache:
            return _union_type_cache[annotation_id]

        origin = get_origin(annotation)
        if origin is Union:
            args = get_args(annotation)
            non_none_args = [arg for arg in args if arg is not type(None)]
            result = set(non_none_args) == {str, int}
        else:
            result = False

        _union_type_cache[annotation_id] = result
        return result

    def _should_be_permissive_int(annotation, field_name=None):
        """Check if an int field should be permissive (allow strings)."""
        # Check if the original annotation (before resolution) was a Union[str, int]
        return _is_union_str_int(annotation)

    def _deep_validate(
        name: str,
        value: Any,
        expected: Any,
        path: str = "",
        class_module=None,
        original_annotation=None,
    ) -> Any:
        """Recursive validation with enhanced type alias resolution."""
        current_path = f"{path}.{name}" if path else name

        if value is None:
            if _is_optional(expected):
                return None
            raise ValidationError("field required", current_path, "missing")

        # Handle typing.Any
        if expected is Any:
            return value

        # Handle Optional types
        if _is_optional(expected):
            expected = _get_non_none_type(expected)
            if expected is Any:
                return value

        # CRITICAL: Resolve type aliases before processing
        resolved_type = _resolve_type_alias(expected, name, class_module)
        if resolved_type != expected:
            return _deep_validate(
                name,
                value,
                resolved_type,
                path,
                class_module,
                original_annotation=expected,
            )

        origin = get_origin(expected)

        # Handle Union types properly
        if origin is Union:
            args = get_args(expected)
            non_none_args = [arg for arg in args if arg is not type(None)]

            # Try each type in the union
            validation_errors = []
            for union_type in non_none_args:
                try:
                    return _deep_validate(name, value, union_type, path, class_module)
                except ValidationError as e:
                    validation_errors.append(str(e))
                except TypeError as e:
                    validation_errors.append(str(e))

            # If no types matched, raise error
            type_names = [_get_type_name(t) for t in non_none_args]
            raise ValidationError(
                f"value does not match any type in Union[{', '.join(type_names)}]",
                current_path,
                "union_mismatch",
            )

        # Simple type validation
        if origin is None:
            if expected is Any:
                return value

            if inspect.isclass(expected):
                # If it's already the right type, accept it
                if isinstance(value, expected):
                    return value

                # Type coercion for basic types
                if expected is str:
                    # For str fields, only accept actual strings or convertible values
                    if isinstance(value, str):
                        return value
                    elif isinstance(value, (int, float, bool)):
                        return str(value)
                    else:
                        raise ValidationError(
                            "value is not a valid string", current_path, "type_error"
                        )
                elif expected is int:
                    # Check if this field should be permissive based on its original type annotation
                    is_permissive = original_annotation and _should_be_permissive_int(
                        original_annotation, name
                    )

                    if isinstance(value, bool):  # bool is subclass of int
                        return int(value)
                    elif isinstance(value, int):
                        return value
                    elif isinstance(value, float):
                        if value.is_integer():
                            return int(value)
                        else:
                            raise ValidationError(
                                "value is not a valid integer",
                                current_path,
                                "type_error",
                            )
                    elif isinstance(value, str):
                        if is_permissive:
                            # For fields that were originally Union[str, int], be permissive
                            # Try conversion first, but accept strings if conversion fails
                            if value.isdigit() or (
                                value.startswith("-") and value[1:].isdigit()
                            ):
                                try:
                                    return int(value)
                                except ValueError:
                                    return value  # Keep as string
                            else:
                                return value  # Keep as string (like "test-1")
                        else:
                            # For strict int fields, only allow valid integer strings
                            if value.isdigit() or (
                                value.startswith("-") and value[1:].isdigit()
                            ):
                                try:
                                    return int(value)
                                except ValueError:
                                    raise ValidationError(
                                        "value is not a valid integer",
                                        current_path,
                                        "type_error",
                                    )
                            else:
                                raise ValidationError(
                                    "value is not a valid integer",
                                    current_path,
                                    "type_error",
                                )
                    else:
                        raise ValidationError(
                            "value is not a valid integer", current_path, "type_error"
                        )
                elif expected is float:
                    if isinstance(value, (int, float)):
                        return float(value)
                    elif isinstance(value, str):
                        try:
                            return float(value)
                        except ValueError:
                            raise ValidationError(
                                "value is not a valid float",
                                current_path,
                                "type_error",
                            )
                    else:
                        raise ValidationError(
                            "value is not a valid float", current_path, "type_error"
                        )
                elif expected is bool:
                    if isinstance(value, bool):
                        return value
                    elif isinstance(value, str):
                        lower_val = value.lower()
                        if lower_val in ("true", "1", "yes", "on"):
                            return True
                        elif lower_val in ("false", "0", "no", "off"):
                            return False
                        else:
                            raise ValidationError(
                                "value is not a valid boolean",
                                current_path,
                                "type_error",
                            )
                    else:
                        raise ValidationError(
                            "value is not a valid boolean", current_path, "type_error"
                        )

                # Check if it's a McpPydanticBase subclass
                if hasattr(expected, "__bases__") and any(
                    issubclass(base, McpPydanticBase) for base in expected.__mro__[1:]
                ):
                    if isinstance(value, dict):
                        try:
                            return expected(**value)
                        except Exception as e:
                            raise ValidationError(
                                f"failed to construct {expected.__name__}: {e}",
                                current_path,
                                "type_error",
                            )
                    elif isinstance(value, expected):
                        return value
                    else:
                        raise ValidationError(
                            f"value is not a valid {expected.__name__}",
                            current_path,
                            "type_error",
                        )

                # For other classes, try construction
                if isinstance(value, expected):
                    return value
                else:
                    try:
                        return expected(value)
                    except Exception:
                        raise ValidationError(
                            f"value is not a valid {expected.__name__}",
                            current_path,
                            "type_error",
                        )

            return value

        # List validation
        if origin in (list, List):
            if not isinstance(value, (list, tuple)):
                raise ValidationError(
                    "value is not a valid list", current_path, "type_error"
                )

            item_type = get_args(expected)[0] if get_args(expected) else Any
            validated_items = []
            for i, item in enumerate(value):
                if item_type is Any:
                    validated_items.append(item)
                else:
                    validated_item = _deep_validate(
                        f"[{i}]", item, item_type, current_path, class_module
                    )
                    validated_items.append(validated_item)
            return validated_items

        # Dict validation
        if origin in (dict, Dict):
            if not isinstance(value, dict):
                raise ValidationError(
                    "value is not a valid dict", current_path, "type_error"
                )

            args = get_args(expected)
            key_type = args[0] if args else Any
            val_type = args[1] if len(args) > 1 else Any

            validated_dict = {}
            for k, v in value.items():
                validated_key = (
                    k
                    if key_type is Any
                    else _deep_validate("key", k, key_type, current_path, class_module)
                )
                validated_value = (
                    v
                    if val_type is Any
                    else _deep_validate(
                        f"[{k}]", v, val_type, current_path, class_module
                    )
                )
                validated_dict[validated_key] = validated_value
            return validated_dict

        # Default: return as-is for unknown types
        return value

    class Field:  # type: ignore[no-redef]
        """Field descriptor for model attributes."""

        __slots__ = (
            "default",
            "default_factory",
            "alias",
            "description",
            "title",
            "required",
            "kwargs",
            "json_schema_extra",
        )

        def __init__(
            self,
            default: Any = ...,
            default_factory: Optional[Callable[[], Any]] = None,
            alias: Optional[str] = None,
            title: Optional[str] = None,
            description: Optional[str] = None,
            json_schema_extra: Optional[Dict[str, Any]] = None,
            **kwargs,
        ):
            if default is not ... and default_factory is not None:
                raise TypeError("Cannot specify both 'default' and 'default_factory'")

            self.default = default
            self.default_factory = default_factory
            self.alias = alias
            self.title = title
            self.description = description
            self.json_schema_extra = json_schema_extra or {}
            self.kwargs = kwargs

            # Determine if field is required
            self.required = default is ... and default_factory is None

    @dataclass
    class McpPydanticBase:  # type: ignore[no-redef]
        """Generic fallback base class that mimics Pydantic behavior.

        PERFORMANCE OPTIMIZED:
        - Type resolution caching to avoid repeated module lookups
        - Cached type hints per class to avoid repeated get_type_hints() calls
        """

        # Class-level metadata
        __model_fields__: ClassVar[Dict[str, Field]] = {}  # type: ignore[valid-type]
        __model_required__: ClassVar[Set[str]] = set()
        __field_aliases__: ClassVar[Dict[str, str]] = {}

        # PERFORMANCE: Type resolution cache (shared across all instances)
        # Key: (class_name, field_name, type_id) -> resolved_type
        __type_cache__: ClassVar[Dict[Tuple[str, str, int], Any]] = {}

        # PERFORMANCE: Type hints cache per class
        # Key: class_id -> type_hints dict
        __hints_cache__: ClassVar[Dict[int, Dict[str, Any]]] = {}

        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__(**kwargs)

            cls.__model_fields__ = {}
            cls.__model_required__ = set()
            cls.__field_aliases__ = {}

            # Analyze type hints and class attributes
            try:
                hints = get_type_hints(cls, include_extras=True)
            except (NameError, AttributeError, TypeError):
                hints = getattr(cls, "__annotations__", {})

            for name, hint in hints.items():
                if name.startswith("__") and name.endswith("__"):
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

                # Handle requirements
                if isinstance(hint, str):
                    if field.required:
                        cls.__model_required__.add(name)
                else:
                    if field.required and not _is_optional(hint):
                        cls.__model_required__.add(name)

                cls.__model_fields__[name] = field

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
                elif field.default_factory is not None:  # type: ignore[attr-defined]
                    values[name] = field.default_factory()  # type: ignore[attr-defined]
                elif field.default is not ...:  # type: ignore[attr-defined]
                    values[name] = field.default  # type: ignore[attr-defined]
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
                raise ValidationError(  # type: ignore[call-arg]
                    f"Missing required fields: {', '.join(missing)}",
                    error_type="missing_fields",
                )

        def _validate_types(self, values: Dict[str, Any]):
            """Validate field types with enhanced type alias resolution.

            PERFORMANCE OPTIMIZED:
            - Cached type hints lookup per class
            - Cached type resolution to avoid repeated module scans
            """
            try:
                # PERFORMANCE: Cache type hints per class to avoid repeated get_type_hints() calls
                class_id = id(self.__class__)
                if class_id not in self.__class__.__hints_cache__:
                    try:
                        self.__class__.__hints_cache__[class_id] = get_type_hints(
                            self.__class__, include_extras=True
                        )
                    except (NameError, AttributeError, TypeError):
                        # Fall back to raw annotations if get_type_hints fails
                        self.__class__.__hints_cache__[class_id] = getattr(
                            self.__class__, "__annotations__", {}
                        )

                hints = self.__class__.__hints_cache__[class_id]

                # First try to get raw annotations to preserve type aliases
                raw_annotations = getattr(self.__class__, "__annotations__", {})

                # Get the module where this class is defined for type alias resolution
                class_module = inspect.getmodule(self.__class__)
                class_name = self.__class__.__name__

                # Process each field
                for name, annotation in raw_annotations.items():
                    if name.startswith("__") and name.endswith("__"):
                        continue

                    if name in values:
                        # PERFORMANCE: Check type cache first
                        cache_key = (class_name, name, id(annotation))
                        if cache_key in self.__class__.__type_cache__:
                            expected_type = self.__class__.__type_cache__[cache_key]
                        else:
                            # Type not cached - resolve it
                            expected_type = hints.get(name, annotation)

                            # Try to resolve the raw annotation if it matches
                            if expected_type == annotation:
                                resolved_annotation = _resolve_type_alias(
                                    annotation, name, class_module
                                )
                                if resolved_annotation != annotation:
                                    expected_type = resolved_annotation

                            # PERFORMANCE: Cache the resolved type for future instances
                            self.__class__.__type_cache__[cache_key] = expected_type

                        # Validate with class module context for type alias resolution
                        # Pass the original annotation so we can detect Union[str, int] patterns
                        validated_value = _deep_validate(
                            name,
                            values[name],
                            expected_type,
                            class_module=class_module,
                            original_annotation=annotation,
                        )
                        values[name] = validated_value

            except ValidationError:
                # Re-raise validation errors - don't suppress them
                raise
            except Exception:
                # Only suppress non-validation exceptions
                return

        def _call_post_init_hooks(self):
            """Call post-initialization hooks."""
            post_init = getattr(self, "__post_init__", None)
            if callable(post_init):
                post_init()

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
            """Serialize to dictionary."""
            result = {}

            for key, value in self.__dict__.items():
                if key.startswith("__"):
                    continue

                if include and key not in include:
                    continue
                if exclude and self._should_exclude(key, exclude):
                    continue
                if exclude_none and value is None:
                    continue

                output_key = key
                if by_alias and key in self.__class__.__field_aliases__:
                    output_key = self.__class__.__field_aliases__[key]

                result[output_key] = self._serialize_value(
                    value, exclude, exclude_none, by_alias, include, **kwargs
                )

            return result

        def _serialize_value(
            self, value, exclude, exclude_none, by_alias, include, **kwargs
        ):
            """Serialize a value recursively."""
            if hasattr(value, "model_dump"):
                return value.model_dump(
                    exclude=exclude,
                    exclude_none=exclude_none,
                    by_alias=by_alias,
                    include=include,
                    **kwargs,
                )
            elif isinstance(value, list):
                return [
                    self._serialize_value(
                        item, exclude, exclude_none, by_alias, include, **kwargs
                    )
                    for item in value
                ]
            elif isinstance(value, dict):
                return {
                    k: self._serialize_value(
                        v, exclude, exclude_none, by_alias, include, **kwargs
                    )
                    for k, v in value.items()
                }
            else:
                return value

        def _should_exclude(
            self, key: str, exclude: Union[Set[str], Dict[str, Any]]
        ) -> bool:
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
            """Serialize to JSON string."""
            data = self.model_dump(
                exclude=exclude,
                exclude_none=exclude_none,
                by_alias=by_alias,
                include=include,
                **kwargs,
            )

            if separators is None:
                separators = (",", ":")

            return json.dumps(data, indent=indent, separators=separators, default=str)

        def model_dump_mcp(self, **kwargs) -> Dict[str, Any]:
            """Convenience method for MCP compatibility."""
            return self.model_dump(**kwargs)

        @classmethod
        def model_validate(cls, data: Union[Dict[str, Any], Any]):
            """Validate and create instance from data."""
            if isinstance(data, dict):
                return cls(**data)
            elif isinstance(data, cls):
                return data
            elif hasattr(data, "__dict__"):
                return cls(**data.__dict__)
            elif hasattr(data, "model_dump"):
                return cls(**data.model_dump())
            else:
                raise ValidationError(  # type: ignore[call-arg]
                    f"Cannot validate {type(data)} as {cls.__name__}",
                    error_type="invalid_input",
                )

        # Pydantic v1 compatibility methods
        def json(self, **kwargs) -> str:
            return self.model_dump_json(**kwargs)

        def dict(self, **kwargs) -> Dict[str, Any]:
            return self.model_dump(**kwargs)

    def ConfigDict(**kwargs) -> Dict[str, Any]:  # type: ignore[no-redef]
        """Configuration dictionary."""
        defaults = {
            "extra": "allow",
            "validate_assignment": True,
            "use_enum_values": True,
            "arbitrary_types_allowed": True,
        }
        defaults.update(kwargs)
        return defaults

    # Dummy decorators for compatibility
    def validator(*args, **kwargs):
        """Dummy validator decorator for fallback mode."""

        def decorator(func):
            return func

        return decorator

    def root_validator(*args, **kwargs):  # type: ignore[no-redef]
        """Dummy root validator decorator for fallback mode."""

        def decorator(func):
            return func

        return decorator
