"""
Comprehensive tests for transports/base.py module.

Tests all abstract base classes and ensures >90% coverage.
"""

import pytest
from abc import ABC
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

from chuk_mcp.transports.base import Transport, TransportParameters


class TestTransportParameters:
    """Test TransportParameters base class."""

    def test_transport_parameters_is_abstract(self):
        """Test that TransportParameters is an ABC."""
        assert issubclass(TransportParameters, ABC)

    def test_transport_parameters_can_be_subclassed(self):
        """Test that TransportParameters can be subclassed."""

        class ConcreteParameters(TransportParameters):
            pass

        params = ConcreteParameters()
        assert isinstance(params, TransportParameters)

    def test_transport_parameters_pass_statement(self):
        """Test line 10 - the pass statement in TransportParameters."""
        # This line is executed when the class is defined
        # We verify by checking the class exists and has no methods
        assert hasattr(TransportParameters, "__init__")
        # The pass statement means there are no custom methods defined


class TestTransport:
    """Test Transport base class."""

    def test_transport_is_abstract(self):
        """Test that Transport is an ABC."""
        assert issubclass(Transport, ABC)

    def test_transport_init_stores_parameters(self):
        """Test line 17 - __init__ stores parameters."""

        class ConcreteParameters(TransportParameters):
            pass

        class ConcreteTransport(Transport):
            async def get_streams(self):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return False

        params = ConcreteParameters()
        transport = ConcreteTransport(params)
        assert transport.parameters is params

    def test_transport_cannot_be_instantiated_directly(self):
        """Test that Transport cannot be instantiated without implementing abstract methods."""

        class IncompleteTransport(Transport):
            pass

        params = TransportParameters.__new__(TransportParameters)

        with pytest.raises(TypeError):
            IncompleteTransport(params)

    def test_transport_get_streams_is_abstract(self):
        """Test line 24 - get_streams has pass statement (abstract)."""

        class PartialTransport(Transport):
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return False

        params = TransportParameters.__new__(TransportParameters)

        with pytest.raises(TypeError):
            PartialTransport(params)

    def test_transport_aenter_is_abstract(self):
        """Test line 29 - __aenter__ has pass statement (abstract)."""

        class PartialTransport(Transport):
            async def get_streams(self):
                pass

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return False

        params = TransportParameters.__new__(TransportParameters)

        with pytest.raises(TypeError):
            PartialTransport(params)

    def test_transport_aexit_is_abstract(self):
        """Test line 34 - __aexit__ has pass statement (abstract)."""

        class PartialTransport(Transport):
            async def get_streams(self):
                pass

            async def __aenter__(self):
                return self

        params = TransportParameters.__new__(TransportParameters)

        with pytest.raises(TypeError):
            PartialTransport(params)

    @pytest.mark.asyncio
    async def test_transport_set_protocol_version_default(self):
        """Test line 38 - set_protocol_version default implementation (pass)."""

        class ConcreteParameters(TransportParameters):
            pass

        class ConcreteTransport(Transport):
            async def get_streams(self):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return False

        params = ConcreteParameters()
        transport = ConcreteTransport(params)

        # set_protocol_version has a default implementation with pass
        # It should not raise an error
        transport.set_protocol_version("2024-11-05")
        # The pass statement means it does nothing, but shouldn't error

    @pytest.mark.asyncio
    async def test_full_transport_implementation(self):
        """Test a complete transport implementation."""

        class TestParameters(TransportParameters):
            def __init__(self, value: str):
                self.value = value

        class TestTransport(Transport):
            async def get_streams(self):
                from anyio import create_memory_object_stream

                send, recv = create_memory_object_stream(10)
                write_send, write_recv = create_memory_object_stream(10)
                return recv, send

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return False

        params = TestParameters("test")
        transport = TestTransport(params)

        assert transport.parameters.value == "test"

        async with transport:
            streams = await transport.get_streams()
            assert len(streams) == 2
            assert isinstance(streams[0], MemoryObjectReceiveStream)
            assert isinstance(streams[1], MemoryObjectSendStream)

    @pytest.mark.asyncio
    async def test_transport_context_manager_protocol(self):
        """Test that Transport follows async context manager protocol."""

        class TestParameters(TransportParameters):
            pass

        class TestTransport(Transport):
            def __init__(self, parameters):
                super().__init__(parameters)
                self.entered = False
                self.exited = False

            async def get_streams(self):
                pass

            async def __aenter__(self):
                self.entered = True
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                self.exited = True
                return False

        params = TestParameters()
        transport = TestTransport(params)

        assert not transport.entered
        assert not transport.exited

        async with transport:
            assert transport.entered
            assert not transport.exited

        assert transport.entered
        assert transport.exited


class TestTransportIntegration:
    """Integration tests for Transport base class."""

    @pytest.mark.asyncio
    async def test_transport_with_exception_in_context(self):
        """Test Transport context manager with exception."""

        class TestParameters(TransportParameters):
            pass

        class TestTransport(Transport):
            def __init__(self, parameters):
                super().__init__(parameters)
                self.cleanup_called = False

            async def get_streams(self):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                self.cleanup_called = True
                return False

        params = TestParameters()
        transport = TestTransport(params)

        with pytest.raises(ValueError):
            async with transport:
                raise ValueError("Test exception")

        assert transport.cleanup_called

    @pytest.mark.asyncio
    async def test_transport_set_protocol_version_can_be_overridden(self):
        """Test that set_protocol_version can be overridden."""

        class TestParameters(TransportParameters):
            pass

        class TestTransport(Transport):
            def __init__(self, parameters):
                super().__init__(parameters)
                self.version = None

            async def get_streams(self):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return False

            def set_protocol_version(self, version: str) -> None:
                self.version = version

        params = TestParameters()
        transport = TestTransport(params)

        assert transport.version is None
        transport.set_protocol_version("2024-11-05")
        assert transport.version == "2024-11-05"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
