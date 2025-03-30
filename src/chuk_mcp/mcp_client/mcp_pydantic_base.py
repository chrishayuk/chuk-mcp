try:
    # Attempt to import real Pydantic
    from pydantic import BaseModel as PydanticBase
    from pydantic import Field as PydanticField
    from pydantic import ConfigDict as PydanticConfigDict
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False

if PYDANTIC_AVAILABLE:
    # Real Pydantic is available
    McpPydanticBase = PydanticBase
    Field = PydanticField
    ConfigDict = PydanticConfigDict

else:
    # Fallback to a pure-Python base class + minimal Field and ConfigDict stubs
    from dataclasses import dataclass, field
    from typing import Dict, Any, Callable, Optional

    @dataclass
    class McpPydanticBase:
        """
        Minimal fallback base class with Pydantic-like methods,
        now modified to accept arbitrary fields in __init__.
        """

        def __init__(self, **data: Any):
            # Instead of using auto-generated dataclass __init__,
            # we manually store each field so arbitrary keys like
            # "command" and "args" won't cause an error.
            object.__setattr__(self, "__dict__", {})
            for k, v in data.items():
                setattr(self, k, v)

        def model_dump(self) -> Dict[str, Any]:
            """
            Simulate Pydantic’s .model_dump().
            Using vars(self) to ensure we dump
            *all* attributes, including those
            not declared as dataclass fields.
            """
            return dict(vars(self))

        @classmethod
        def model_validate(cls, data: Dict[str, Any]):
            """
            Simulate Pydantic’s .model_validate(...).
            Creates a new instance with all fields in data.
            """
            return cls(**data)

    def Field(
        default: Any = None,
        default_factory: Optional[Callable[[], Any]] = None,
        **kwargs
    ) -> Any:
        """
        Minimal stand-in for pydantic.Field(...).
        In real Pydantic, Field returns special metadata.
        Here, we just return either the default or
        the result of default_factory.
        """
        if default_factory is not None:
            return default_factory()
        return default

    def ConfigDict(**kwargs) -> Dict[str, Any]:
        """
        Minimal stand-in for pydantic.ConfigDict(...) (Pydantic 2.x).
        In real Pydantic, ConfigDict configures model behavior (e.g. extra='allow').
        Here, we just return a dict so you can store it if needed,
        but it doesn't affect the fallback base class logic.
        """
        return dict(**kwargs)
