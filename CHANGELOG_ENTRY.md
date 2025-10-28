# Changelog Entry for v0.7.2

## [0.7.2] - 2025-10-28

### Breaking Changes

#### Exception Handling in `send_initialize()`

**Changed**: `send_initialize()` and `send_initialize_with_client_tracking()` now **always raise exceptions** instead of returning `None` on errors.

**Impact**: Code that checks for `None` return values will need to be updated to use exception handling.

**Files Modified**:
- `src/chuk_mcp/protocol/messages/initialize/send_messages.py`

**Changes**:
1. Return type changed from `Optional[InitializeResult]` to `InitializeResult`
2. All exception handlers now use `raise` instead of `return None`
3. Updated docstrings to document all exception types

**Exceptions Raised**:
- `VersionMismatchError` - Protocol version incompatibility
- `TimeoutError` - Server didn't respond in time
- `RetryableError` - Retryable JSON-RPC errors (e.g., 401 authentication failures)
- `NonRetryableError` - Non-retryable JSON-RPC errors
- `Exception` - Other unexpected errors

**Migration Guide**:

Before:
```python
result = await send_initialize(read, write)
if result is None:
    logging.error("Initialization failed")
    return
print(f"Connected to {result.serverInfo.name}")
```

After:
```python
try:
    result = await send_initialize(read, write)
    print(f"Connected to {result.serverInfo.name}")
except RetryableError as e:
    if "401" in str(e).lower():
        # Trigger OAuth re-authentication
        pass
except VersionMismatchError as e:
    logging.error(f"Version mismatch: {e}")
except TimeoutError as e:
    logging.error(f"Timeout: {e}")
except Exception as e:
    logging.error(f"Error: {e}")
```

**Benefits**:
- ✅ Enables automatic OAuth re-authentication in downstream tools (e.g., mcp-cli)
- ✅ Proper error propagation with full stack traces
- ✅ Type safety - no `Optional` checks needed
- ✅ Follows Python exception handling best practices

### Added

#### Examples
- `examples/initialize_error_handling.py` - Comprehensive error handling demonstrations
  - Example 1: Successful initialization
  - Example 2: OAuth 401 error handling
  - Example 3: Version mismatch error
  - Example 4: Timeout error
  - Example 5: Comprehensive error handling pattern

#### Tests
- `tests/mcp/messages/test_initialize_exceptions.py` - Complete test suite for exception handling
  - 8 comprehensive tests covering all error scenarios
  - Tests for 401 errors, server errors, timeouts, version mismatches
  - Critical test verifying NO `None` returns on errors

#### Documentation
- `EXCEPTION_HANDLING_FIX.md` - Detailed technical documentation of the fix
- `EXCEPTION_FIX_VERIFIED.md` - Verification and testing documentation
- `FIX_COMPLETE.md` - Executive summary of the fix
- Updated `README.md` with:
  - Breaking changes section
  - Enhanced FAQ with exception handling examples
  - Error handling best practices
  - Reference to new error handling example

### Changed

#### Tests
- Updated `tests/mcp/messages/test_initialize.py::test_send_initialize_server_error`
  - Changed to expect exceptions instead of `None` returns
  - Added assertions to verify proper exception raising

### Fixed

- OAuth re-authentication flow in mcp-cli now works correctly
  - 401 errors are properly propagated
  - Browser opens automatically for OAuth flow
  - No manual token deletion needed

## Test Results

- ✅ **268/268** message tests passing
- ✅ **19/19** initialize tests passing (8 new + 11 updated)
- ✅ All examples working correctly

## Verification

Run the following to verify the fix:

```bash
# Run error handling examples
uv run python examples/initialize_error_handling.py

# Run exception tests
uv run pytest tests/mcp/messages/test_initialize_exceptions.py -v

# Run all initialize tests
uv run pytest tests/mcp/messages/test_initialize.py -v

# Run full test suite
uv run pytest tests/mcp/messages/ -v
```

## Related Issues

- Fixes OAuth re-authentication in mcp-cli
- Improves error handling throughout the MCP ecosystem
- Enables proper exception propagation for debugging

## Notes for Maintainers

This is a **breaking change** that improves error handling but requires code changes for users who check for `None` returns. The benefits (automatic OAuth re-authentication, proper error propagation, type safety) outweigh the migration cost.

Consider:
- Bumping to v0.8.0 if following strict semantic versioning
- Or keep at v0.7.2 and document as breaking change in patch release
- Update changelog with migration guide
- Announce breaking change in release notes
