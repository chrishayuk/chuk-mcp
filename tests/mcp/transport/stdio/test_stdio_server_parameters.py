# tests/mcp/transport/stdio/test_stdio_server_parameters.py
import pytest

# Import ValidationError from the right location based on which implementation is active
try:
    from pydantic import ValidationError
except ImportError:
    from chuk_mcp.protocol.mcp_pydantic_base import ValidationError

from chuk_mcp.transports.stdio.parameters import StdioParameters

def test_stdio_server_parameters_creation():
    """Test creating StdioParameters with valid data."""
    # Test with minimum required fields
    params = StdioParameters(command="python")
    assert params.command == "python"
    assert params.args == []
    assert params.env is None
    
    # Test with all fields
    params = StdioParameters(
        command="python",
        args=["-m", "mcp.server"],
        env={"TEST_ENV": "value"}
    )
    assert params.command == "python"
    assert params.args == ["-m", "mcp.server"]
    assert params.env == {"TEST_ENV": "value"}


def test_stdio_server_parameters_validation():
    """Test validation of StdioParameters."""
    # Test with missing required field
    with pytest.raises((ValidationError, Exception)):  # Allow catching any exception for more flexibility
        StdioParameters()
    
    # Test with empty command (should pass validation but might be rejected by application logic)
    params = StdioParameters(command="")
    assert params.command == ""
    
    # Test with non-list args
    with pytest.raises((ValidationError, Exception)):
        StdioParameters(command="python", args="not-a-list")
    
    # Test with non-string command
    with pytest.raises((ValidationError, Exception)):
        StdioParameters(command=123)
    
    # Test with invalid env type
    with pytest.raises((ValidationError, Exception)):
        StdioParameters(command="python", env="not-a-dict")


def test_stdio_server_parameters_default_factory():
    """Test the default factory for args field."""
    # Create two instances to ensure the default factory creates new instances
    params1 = StdioParameters(command="python")
    params2 = StdioParameters(command="python")
    
    # Modify one instance's args
    params1.args.append("arg1")
    
    # Verify the other instance is not affected
    assert params1.args == ["arg1"]
    assert params2.args == []


def test_stdio_server_parameters_model_dump():
    """Test the model_dump method."""
    params = StdioParameters(
        command="python",
        args=["-m", "mcp.server"],
        env={"TEST_ENV": "value"}
    )
    
    # Check model_dump
    dump = params.model_dump()
    assert dump == {
        "command": "python",
        "args": ["-m", "mcp.server"],
        "env": {"TEST_ENV": "value"}
    }
    
    # Check model_dump with exclude
    dump = params.model_dump(exclude={"env"})
    assert dump == {
        "command": "python",
        "args": ["-m", "mcp.server"]
    }
    
    # Check model_dump_json
    json_str = params.model_dump_json()
    assert '"command":"python"' in json_str
    assert '"args":["-m","mcp.server"]' in json_str
    assert '"env":{"TEST_ENV":"value"}' in json_str


def test_stdio_parameters_inheritance():
    """Test that StdioParameters properly inherits from TransportParameters."""
    from chuk_mcp.transports.base import TransportParameters
    
    params = StdioParameters(command="python")
    assert isinstance(params, TransportParameters)


def test_stdio_parameters_with_transport():
    """Test that StdioParameters work with StdioTransport."""
    from chuk_mcp.transports.stdio.transport import StdioTransport
    
    params = StdioParameters(command="python", args=["--version"])
    transport = StdioTransport(params)
    
    # Verify the transport holds the parameters
    assert transport.parameters == params
    assert transport.parameters.command == "python"
    assert transport.parameters.args == ["--version"]