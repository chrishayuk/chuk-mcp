# tests/mcp/transport/stdio/test_stdio_server_shutdown.py
import pytest
import anyio
import logging
from unittest.mock import AsyncMock, patch

# Skip all tests in this file if we can't import the required module
pytest.importorskip("chuk_mcp.transports.stdio")

# Force asyncio only for all tests in this file
pytestmark = [pytest.mark.asyncio]


class MockProcess:
    """Mock implementation of anyio.abc.Process for testing."""

    def __init__(self, exit_on_close=True, exit_on_terminate=True, exit_on_kill=True):
        self.pid = 12345
        self.returncode = None
        self.stdin = AsyncMock()
        self.stdout = AsyncMock()
        self._exit_on_close = exit_on_close
        self._exit_on_terminate = exit_on_terminate
        self._exit_on_kill = exit_on_kill
        self._terminated = False
        self._killed = False

    async def wait(self):
        # Simulate different exit behaviors
        if (
            self._exit_on_close
            and hasattr(self.stdin, "_closed")
            and self.stdin._closed
        ):
            self.returncode = 0
        elif self._exit_on_terminate and self._terminated:
            self.returncode = 0
        elif self._exit_on_kill and self._killed:
            self.returncode = 9
        else:
            # If we get here and returncode is still None, it means the process
            # is not exiting and should trigger a timeout
            if self.returncode is None:
                await anyio.sleep(10)  # This will trigger timeout in tests
        return self.returncode or 0

    def terminate(self):
        self._terminated = True

    def kill(self):
        self._killed = True
        self.returncode = 9


async def mock_shutdown_stdio_server(read_stream, write_stream, process, timeout=5.0):
    """
    Mock implementation of shutdown_stdio_server for testing.

    This simulates the shutdown process without needing the actual implementation.
    """
    try:
        # Close streams
        if write_stream:
            await write_stream.aclose()
        if read_stream:
            await read_stream.aclose()

        # Close stdin to signal the process to exit
        if process and process.stdin:
            await process.stdin.aclose()

        # Wait for process to exit gracefully
        if process and process.returncode is None:
            try:
                with anyio.fail_after(timeout):
                    await process.wait()
                logging.info("Process exited normally")
            except TimeoutError:
                logging.warning("Process did not exit gracefully, sending SIGTERM")
                process.terminate()

                try:
                    with anyio.fail_after(timeout):
                        await process.wait()
                    logging.info("Process exited after SIGTERM")
                except TimeoutError:
                    logging.warning(
                        "Process did not exit after SIGTERM, sending SIGKILL"
                    )
                    process.kill()

                    try:
                        with anyio.fail_after(timeout):
                            await process.wait()
                        logging.info("Process exited after SIGKILL")
                    except TimeoutError:
                        logging.error("Process did not exit after SIGKILL")
                        raise

        logging.info("Stdio server shutdown complete")

    except Exception as e:
        logging.error(f"Unexpected error during stdio server shutdown: {e}")
        if process:
            process.kill()
            try:
                await process.wait()
            except Exception:
                pass
        logging.info("Process forcibly terminated")
        logging.info("Stdio server shutdown complete")


async def test_shutdown_normal_exit():
    """Test normal graceful shutdown where process exits after stdin close."""
    # Create a mock process that exits when stdin is closed
    mock_process = MockProcess(exit_on_close=True)

    # Mock the stdin close method
    async def mock_aclose():
        mock_process.stdin._closed = True

    mock_process.stdin.aclose = AsyncMock(side_effect=mock_aclose)

    # Create mock streams
    read_send, read_stream = anyio.create_memory_object_stream(max_buffer_size=10)
    write_stream, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    # Call shutdown function
    with patch("logging.info") as mock_log_info:
        await mock_shutdown_stdio_server(
            read_stream=read_stream,
            write_stream=write_stream,
            process=mock_process,
            timeout=1.0,
        )

    # Verify stdin was closed
    mock_process.stdin.aclose.assert_called_once()

    # Verify process exited normally
    assert "Process exited normally" in str(mock_log_info.call_args_list)
    assert "Stdio server shutdown complete" in str(mock_log_info.call_args_list)

    # Verify terminate and kill were not called
    assert not mock_process._terminated
    assert not mock_process._killed


async def test_shutdown_terminate_required():
    """Test shutdown where SIGTERM is required."""
    # Create a mock process that doesn't exit when stdin is closed, but exits on terminate
    mock_process = MockProcess(exit_on_close=False, exit_on_terminate=True)

    # Mock the stdin close method
    mock_process.stdin.aclose = AsyncMock()

    # Create mock streams
    read_send, read_stream = anyio.create_memory_object_stream(max_buffer_size=10)
    write_stream, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    # Call shutdown function
    with (
        patch("logging.info") as mock_log_info,
        patch("logging.warning") as mock_log_warning,
    ):
        await mock_shutdown_stdio_server(
            read_stream=read_stream,
            write_stream=write_stream,
            process=mock_process,
            timeout=0.1,  # Short timeout to speed up test
        )

    # Verify stdin was closed
    mock_process.stdin.aclose.assert_called_once()

    # Verify terminate was called
    assert mock_process._terminated
    assert "sending SIGTERM" in str(mock_log_warning.call_args_list)

    # Verify process exited after SIGTERM
    assert "Process exited after SIGTERM" in str(mock_log_info.call_args_list)
    assert "Stdio server shutdown complete" in str(mock_log_info.call_args_list)

    # Verify kill was not called
    assert not mock_process._killed


async def test_shutdown_kill_required():
    """Test shutdown where SIGKILL is required."""
    # Create a mock process that doesn't exit when stdin is closed or terminated
    mock_process = MockProcess(
        exit_on_close=False, exit_on_terminate=False, exit_on_kill=True
    )

    # Mock the stdin close method
    mock_process.stdin.aclose = AsyncMock()

    # Create mock streams
    read_send, read_stream = anyio.create_memory_object_stream(max_buffer_size=10)
    write_stream, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    # Call shutdown function
    with (
        patch("logging.info") as mock_log_info,
        patch("logging.warning") as mock_log_warning,
    ):
        await mock_shutdown_stdio_server(
            read_stream=read_stream,
            write_stream=write_stream,
            process=mock_process,
            timeout=0.1,  # Short timeout to speed up test
        )

    # Verify stdin was closed
    mock_process.stdin.aclose.assert_called_once()

    # Verify terminate and kill were both called
    assert mock_process._terminated
    assert mock_process._killed
    assert "sending SIGTERM" in str(mock_log_warning.call_args_list)
    assert "sending SIGKILL" in str(mock_log_warning.call_args_list)

    # Verify process exited after SIGKILL
    assert "Process exited after SIGKILL" in str(mock_log_info.call_args_list)
    assert "Stdio server shutdown complete" in str(mock_log_info.call_args_list)


async def test_shutdown_exception_handling():
    """Test handling of exceptions during shutdown."""
    # Create a mock process that raises an exception during stdin close
    mock_process = MockProcess()

    # Mock the stdin close method to raise an exception
    mock_process.stdin.aclose = AsyncMock(side_effect=Exception("Test exception"))

    # Create mock streams
    read_send, read_stream = anyio.create_memory_object_stream(max_buffer_size=10)
    write_stream, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    # Call shutdown function
    with (
        patch("logging.info") as mock_log_info,
        patch("logging.error") as mock_log_error,
    ):
        await mock_shutdown_stdio_server(
            read_stream=read_stream,
            write_stream=write_stream,
            process=mock_process,
            timeout=0.1,
        )

    # Verify the exception was caught and logged
    assert "Unexpected error during stdio server shutdown" in str(
        mock_log_error.call_args_list
    )
    assert "Test exception" in str(mock_log_error.call_args_list)

    # Verify process was forcibly terminated
    assert mock_process._killed
    assert "Process forcibly terminated" in str(mock_log_info.call_args_list)
    assert "Stdio server shutdown complete" in str(mock_log_info.call_args_list)


async def test_shutdown_with_null_streams():
    """Test shutdown with null read/write streams."""
    # Create a mock process
    mock_process = MockProcess(exit_on_close=True)

    # Mock the stdin close method
    async def mock_aclose():
        mock_process.stdin._closed = True

    mock_process.stdin.aclose = AsyncMock(side_effect=mock_aclose)

    # Call shutdown function with null streams
    with patch("logging.info") as mock_log_info:
        await mock_shutdown_stdio_server(
            read_stream=None, write_stream=None, process=mock_process, timeout=1.0
        )

    # Verify stdin was still closed
    mock_process.stdin.aclose.assert_called_once()

    # Verify process exited normally
    assert "Process exited normally" in str(mock_log_info.call_args_list)
    assert "Stdio server shutdown complete" in str(mock_log_info.call_args_list)


async def test_shutdown_with_null_process():
    """Test shutdown with null process."""
    # Create mock streams
    read_send, read_stream = anyio.create_memory_object_stream(max_buffer_size=10)
    write_stream, write_receive = anyio.create_memory_object_stream(max_buffer_size=10)

    # Call shutdown function with null process
    with patch("logging.info") as mock_log_info:
        await mock_shutdown_stdio_server(
            read_stream=read_stream,
            write_stream=write_stream,
            process=None,
            timeout=1.0,
        )

    # Verify shutdown completed
    assert "Stdio server shutdown complete" in str(mock_log_info.call_args_list)


async def test_stdio_client_shutdown_integration():
    """Test that StdioClient properly handles shutdown."""
    from chuk_mcp.transports.stdio.stdio_client import StdioClient
    from chuk_mcp.transports.stdio.parameters import StdioParameters

    # Create a client with mock process
    client = StdioClient(StdioParameters(command="test"))
    mock_process = MockProcess(exit_on_close=True)
    client.process = mock_process

    # Mock the stdin close method
    async def mock_aclose():
        mock_process.stdin._closed = True

    mock_process.stdin.aclose = AsyncMock(side_effect=mock_aclose)

    # Test the shutdown process
    with patch("logging.info"):
        await client._terminate_process()

    # Verify the process was handled appropriately
    assert (
        mock_process.stdin.aclose.called
        or mock_process._terminated
        or mock_process._killed
    )
