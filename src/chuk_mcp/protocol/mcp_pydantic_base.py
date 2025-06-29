# chuk_mcp/mcp_client/mcp_pydantic_base.py
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
)

"""Minimal-footprint drop-in replacement for Pydantic when the real package
is unavailable or disabled via the ``MCP_FORCE_FALLBACK`` environment
variable.

Key goals
──────────
1. **Transparent pass-through** when Pydantic *is* installed — original
   behaviour and performance preserved.
2. **Just-enough fallback**: primitives, Optional, List, Dict, nested models —
   so the rest of the codebase runs without heavy deps.
3. Maintain a **tiny public API** (`Field`, `model_dump(*)`, etc.) to make
   future migrations painless.
4. **Support leading underscore fields** like `_meta` for MCP compatibility.
"""

FORCE_FALLBACK = os.environ.get("MCP_FORCE_FALLBACK") == "1"

try:
    if not FORCE_FALLBACK:
        from pydantic import (
            BaseModel as PydanticBase,  # type: ignore
            Field as PydanticField,  # type: ignore
            ConfigDict as PydanticConfigDict,  # type: ignore
            ValidationError,  # type: ignore
        )

        PYDANTIC_AVAILABLE = True
    else:
        PYDANTIC_AVAILABLE = False
except ImportError:
    PYDANTIC_AVAILABLE = False

# ---------------------------------------------------------------------------
# 1. Re-exports when the real Pydantic is present
# ---------------------------------------------------------------------------
if PYDANTIC_AVAILABLE:

    McpPydanticBase = PydanticBase  # noqa: N816
    Field = PydanticField
    ConfigDict = PydanticConfigDict

# ---------------------------------------------------------------------------
# 2. Lightweight fallback implementation
# ---------------------------------------------------------------------------
else:

    class ValidationError(Exception):
        """Raised on validation failures in the fallback implementation."""

    # ────────────────────────────────────────────────────────────────────
    # Helper functions
    # ────────────────────────────────────────────────────────────────────

    def _is_optional(t: Any) -> bool:
        origin, args = get_origin(t), get_args(t)
        return origin is Union and type(None) in args  # noqa: E721

    def _deep_validate(name: str, value: Any, expected: Any) -> None:
        """Recursively validate *value* against *expected* (two levels deep)."""
        if value is None:
            if _is_optional(expected):
                return
            raise ValidationError(f"{name} cannot be None")

        origin = get_origin(expected)

        if origin is None:
            if inspect.isclass(expected) and isinstance(value, expected):
                return
            raise ValidationError(f"{name} must be of type {expected.__name__}")

        if origin in (list, List):
            if not isinstance(value, list):
                raise ValidationError(f"{name} must be a list")
            (item_type,) = get_args(expected) or (Any,)
            for i, item in enumerate(value):
                _deep_validate(f"{name}[{i}]", item, item_type)
            return

        if origin in (dict, Dict):
            if not isinstance(value, dict):
                raise ValidationError(f"{name} must be a dict")
            key_type, val_type = get_args(expected) or (Any, Any)
            for k, v in value.items():
                _deep_validate(f"key of {name}", k, key_type)
                _deep_validate(f"value of {name}[{k}]", v, val_type)
            return
        # Unknown complex type → skip deep checks (stay permissive)

    # ────────────────────────────────────────────────────────────────────
    # Field descriptor (subset of pydantic.Field)
    # ────────────────────────────────────────────────────────────────────

    class Field:  # noqa: D101 – minimal drop-in
        __slots__ = ("default", "default_factory", "kwargs", "required", "alias")

        def __init__(self, default: Any = None, default_factory: Optional[Any] = None, 
                    alias: Optional[str] = None, **kwargs):
            if default is not None and default_factory is not None:
                raise TypeError("Specify either 'default' or 'default_factory', not both")

            self.default = default
            self.default_factory = default_factory
            self.alias = alias
            self.kwargs = kwargs
            self.required: bool = kwargs.get("required", False)

    # ────────────────────────────────────────────────────────────────────
    # Main fallback base class
    # ────────────────────────────────────────────────────────────────────

    @dataclass
    class McpPydanticBase:  # noqa: D101
        # Class-level caches populated in ``__init_subclass__``
        __model_fields__: ClassVar[Dict[str, Field]] = {}
        __model_required__: ClassVar[Set[str]] = set()
        __field_aliases__: ClassVar[Dict[str, str]] = {}  # field_name -> alias

        # One-time class analysis
        def __init_subclass__(cls, **kwargs):  # noqa: D401
            super().__init_subclass__(**kwargs)

            cls.__model_fields__ = {}
            cls.__model_required__ = set()
            cls.__field_aliases__ = {}

            hints = get_type_hints(cls, include_extras=True)
            for name, hint in hints.items():
                # Skip special attributes
                if name.startswith('__') and name.endswith('__'):
                    continue
                    
                if hasattr(cls, name):
                    attr_val = getattr(cls, name)
                    field = attr_val if isinstance(attr_val, Field) else Field(default=attr_val)
                else:
                    field = Field()

                # Handle alias
                if field.alias:
                    cls.__field_aliases__[name] = field.alias

                if field.default is None and field.default_factory is None and not _is_optional(hint):
                    field.required = True

                cls.__model_fields__[name] = field
                if field.required:
                    cls.__model_required__.add(name)

            # Project-specific tweaks
            if cls.__name__ == "StdioServerParameters":
                cls.__model_fields__["args"] = Field(default_factory=list)
                cls.__model_required__.discard("args")
            if cls.__name__ == "JSONRPCMessage":
                cls.__model_fields__["jsonrpc"] = Field(default="2.0")

        # Instance construction & validation
        def __init__(self, **data: Any):  # noqa: D401
            values: Dict[str, Any] = {}
            
            # Handle aliases - convert aliased keys to field names
            processed_data = {}
            for key, value in data.items():
                # Check if this key is an alias for any field
                field_name = None
                for fname, field in self.__class__.__model_fields__.items():
                    if field.alias == key:
                        field_name = fname
                        break
                
                if field_name:
                    processed_data[field_name] = value
                else:
                    processed_data[key] = value
            
            # Process fields
            for name, field in self.__class__.__model_fields__.items():
                if name in processed_data:
                    values[name] = processed_data.pop(name)
                elif field.default_factory is not None:
                    values[name] = field.default_factory()
                else:
                    values[name] = field.default

            # Accept extra keys ("extra = allow")
            values.update(processed_data)

            missing = [n for n in self.__class__.__model_required__ if values.get(n) is None]
            if missing:
                raise ValidationError(f"Missing required field(s): {', '.join(missing)}")

            hints = get_type_hints(self.__class__, include_extras=True)
            for name, expected in hints.items():
                if name.startswith('__') and name.endswith('__'):
                    continue
                if name in values:
                    _deep_validate(name, values[name], expected)

            object.__setattr__(self, "__dict__", values)

            post_init = getattr(self, "__post_init__", None)
            if callable(post_init):
                post_init()
            
            # Call model_post_init if it exists
            model_post_init = getattr(self, "model_post_init", None)
            if callable(model_post_init):
                model_post_init(None)  # Pass None as context

        # Public helpers mirroring Pydantic v2 API
        def model_dump(
            self,
            *,
            exclude: Optional[Union[Set[str], Dict[str, Any]]] = None,
            exclude_none: bool = False,
            by_alias: bool = False,
            **kwargs,
        ) -> Dict[str, Any]:
            """Return dict of *public* fields (internal caches stripped)."""
            result: Dict[str, Any] = {}
            for k, v in self.__dict__.items():
                if k.startswith("__"):
                    continue  # internal cache attrs
                if exclude and ((k in exclude) or (isinstance(exclude, dict) and k in exclude)):
                    continue
                if exclude_none and v is None:
                    continue
                
                # Handle aliases
                output_key = k
                if by_alias and k in self.__class__.__field_aliases__:
                    output_key = self.__class__.__field_aliases__[k]
                
                if isinstance(v, McpPydanticBase):
                    result[output_key] = v.model_dump(exclude=exclude, exclude_none=exclude_none, 
                                                     by_alias=by_alias, **kwargs)
                else:
                    result[output_key] = v
            return result

        def model_dump_json(
            self,
            *,
            exclude: Optional[Union[Set[str], Dict[str, Any]]] = None,
            exclude_none: bool = False,
            by_alias: bool = False,
            indent: Optional[int] = None,
            separators: Optional[tuple] = None,
            **kwargs,
        ) -> str:
            data = self.model_dump(exclude=exclude, exclude_none=exclude_none, 
                                 by_alias=by_alias, **kwargs)
            if separators is None:
                separators = (",", ":")
            return json.dumps(data, indent=indent, separators=separators)

        # Aliases for Pydantic v1 compatibility
        def json(self, **kwargs):
            return self.model_dump_json(**kwargs)

        def dict(self, **kwargs):  # noqa: D401
            return self.model_dump(**kwargs)

        @classmethod
        def model_validate(cls, data: Union[Dict[str, Any], Any]):  # noqa: D401
            if isinstance(data, dict):
                return cls(**data)
            else:
                # For non-dict data, try to convert to dict first
                if hasattr(data, '__dict__'):
                    return cls(**data.__dict__)
                else:
                    raise ValidationError(f"Cannot validate {type(data)} as {cls.__name__}")

    # ConfigDict shim
    def ConfigDict(**kwargs) -> Dict[str, Any]:  # noqa: D401
        return dict(**kwargs)