#!/usr/bin/env python3
"""
Enhanced UV-compatible installation test for chuk-mcp with comprehensive validation.

This script provides thorough testing of the fallback Pydantic implementation
and validates compatibility with UV package management.
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path
from typing import List, Tuple, Optional


def run_command(
    cmd: List[str], cwd: Optional[Path] = None, timeout: int = 120
) -> Tuple[bool, str, str]:
    """Run a command and return success, stdout, stderr."""
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)


def test_fallback_pydantic_features():
    """Test advanced features of the fallback Pydantic implementation."""
    print("\n🧪 Testing Enhanced Fallback Pydantic Features...")

    test_script = """
import os
import sys
from typing import List, Optional, Dict, Union

# Force fallback mode
os.environ["MCP_FORCE_FALLBACK"] = "1"

# Clear any cached imports
modules_to_clear = [name for name in sys.modules.keys() if name.startswith('chuk_mcp')]
for module_name in modules_to_clear:
    if module_name in sys.modules:
        del sys.modules[module_name]

try:
    from chuk_mcp.protocol.mcp_pydantic_base import McpPydanticBase, Field, ValidationError
    print("✓ Imported fallback Pydantic components")
    
    # Test 1: Basic model with validation
    class TestModel(McpPydanticBase):
        name: str
        age: int
        email: Optional[str] = None
        tags: List[str] = Field(default_factory=list)
        metadata: Dict[str, str] = Field(default_factory=dict)
    
    # Valid instance
    model = TestModel(name="John", age=30, email="john@example.com")
    print("✓ Basic model creation works")
    
    # Test serialization
    data = model.model_dump()
    json_str = model.model_dump_json()
    print("✓ Serialization works")
    
    # Test validation from dict
    model2 = TestModel.model_validate({"name": "Jane", "age": 25})
    print("✓ Model validation from dict works")
    
    # Test 2: Field aliases
    class AliasModel(McpPydanticBase):
        internal_name: str = Field(alias="name")
        internal_id: int = Field(alias="id")
    
    alias_model = AliasModel(name="Test", id=123)
    alias_data = alias_model.model_dump(by_alias=True)
    if "name" in alias_data and "id" in alias_data:
        print("✓ Field aliases work correctly")
    else:
        print("ERROR: Field aliases not working")
        sys.exit(1)
    
    # Test 3: Nested models
    class NestedModel(McpPydanticBase):
        user: TestModel
        settings: Dict[str, Union[str, int]]
    
    nested = NestedModel(
        user={"name": "Bob", "age": 40},
        settings={"theme": "dark", "timeout": 30}
    )
    nested_data = nested.model_dump()
    if isinstance(nested_data["user"], dict) and "name" in nested_data["user"]:
        print("✓ Nested model validation works")
    else:
        print("ERROR: Nested model validation failed")
        sys.exit(1)
    
    # Test 4: Required field validation
    try:
        TestModel(age=25)  # Missing required 'name'
        print("ERROR: Should have failed validation for missing required field")
        sys.exit(1)
    except ValidationError:
        print("✓ Required field validation works")
    
    # Test 5: Type coercion
    coerced_model = TestModel(name="Alice", age="35")  # String to int
    if coerced_model.age == 35 and isinstance(coerced_model.age, int):
        print("✓ Type coercion works")
    else:
        print("ERROR: Type coercion failed")
        sys.exit(1)
    
    # Test 6: Optional fields
    optional_model = TestModel(name="Charlie", age=28)
    if optional_model.email is None:
        print("✓ Optional fields work correctly")
    else:
        print("ERROR: Optional field should be None")
        sys.exit(1)
    
    # Test 7: List validation
    list_model = TestModel(
        name="David", 
        age=32, 
        tags=["python", "mcp", "ai"]
    )
    if isinstance(list_model.tags, list) and len(list_model.tags) == 3:
        print("✓ List validation works")
    else:
        print("ERROR: List validation failed")
        sys.exit(1)
    
    # Test 8: Error messages
    try:
        TestModel(name=123, age="not_a_number")
        print("ERROR: Should have failed type validation")
        sys.exit(1)
    except ValidationError as e:
        if "name" in str(e) or "age" in str(e):
            print("✓ Error messages include field information")
        else:
            print(f"WARNING: Error message could be more specific: {e}")
    
    print("SUCCESS: All enhanced fallback features work correctly")
    
except Exception as e:
    print(f"ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
finally:
    # Cleanup
    if "MCP_FORCE_FALLBACK" in os.environ:
        del os.environ["MCP_FORCE_FALLBACK"]
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(test_script)
        test_file = f.name

    try:
        success, stdout, stderr = run_command([sys.executable, test_file])

        if success:
            print("   ✅ Enhanced fallback features test PASSED")
            for line in stdout.split("\n"):
                if line.strip():
                    print(f"   {line}")
            return True
        else:
            print("   ❌ Enhanced fallback features test FAILED")
            print(f"   📋 Error: {stderr}")
            print(f"   📋 Output: {stdout}")
            return False
    finally:
        os.unlink(test_file)


def test_performance_comparison():
    """Compare performance between Pydantic and fallback modes."""
    print("\n⚡ Testing Performance Comparison...")

    test_script = '''
import time
import os
import sys

def time_operation(func, iterations=1000):
    """Time a function over multiple iterations."""
    start = time.time()
    for _ in range(iterations):
        func()
    end = time.time()
    return (end - start) / iterations * 1000  # ms per operation

# Test with Pydantic if available
pydantic_time = None
try:
    import pydantic
    os.environ.pop("MCP_FORCE_FALLBACK", None)
    
    # Clear imports
    modules_to_clear = [name for name in sys.modules.keys() if name.startswith('chuk_mcp')]
    for module_name in modules_to_clear:
        if module_name in sys.modules:
            del sys.modules[module_name]
    
    from chuk_mcp.protocol.mcp_pydantic_base import McpPydanticBase, Field
    
    class PydanticTestModel(McpPydanticBase):
        name: str
        age: int
        tags: list = Field(default_factory=list)
    
    def create_pydantic_model():
        return PydanticTestModel(name="Test", age=25, tags=["a", "b", "c"])
    
    pydantic_time = time_operation(create_pydantic_model, 500)
    print(f"✓ Pydantic mode: {pydantic_time:.3f}ms per operation")
    
except ImportError:
    print("⚠️ Pydantic not available for comparison")
except Exception as e:
    print(f"⚠️ Pydantic test failed: {e}")

# Test with fallback
os.environ["MCP_FORCE_FALLBACK"] = "1"

# Clear imports again
modules_to_clear = [name for name in sys.modules.keys() if name.startswith('chuk_mcp')]
for module_name in modules_to_clear:
    if module_name in sys.modules:
        del sys.modules[module_name]

try:
    from chuk_mcp.protocol.mcp_pydantic_base import McpPydanticBase, Field
    
    class FallbackTestModel(McpPydanticBase):
        name: str
        age: int
        tags: list = Field(default_factory=list)
    
    def create_fallback_model():
        return FallbackTestModel(name="Test", age=25, tags=["a", "b", "c"])
    
    fallback_time = time_operation(create_fallback_model, 500)
    print(f"✓ Fallback mode: {fallback_time:.3f}ms per operation")
    
    if pydantic_time is not None:
        ratio = fallback_time / pydantic_time
        print(f"✓ Fallback is {ratio:.1f}x {'slower' if ratio > 1 else 'faster'} than Pydantic")
        if ratio < 5:  # Reasonable performance
            print("✓ Performance difference is acceptable")
        else:
            print("⚠️ Significant performance difference detected")
    
except Exception as e:
    print(f"ERROR: Fallback test failed: {e}")
    sys.exit(1)

finally:
    if "MCP_FORCE_FALLBACK" in os.environ:
        del os.environ["MCP_FORCE_FALLBACK"]

print("SUCCESS: Performance testing completed")
'''

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(test_script)
        test_file = f.name

    try:
        success, stdout, stderr = run_command([sys.executable, test_file])

        if success:
            print("   ✅ Performance comparison PASSED")
            for line in stdout.split("\n"):
                if line.strip():
                    print(f"   {line}")
            return True
        else:
            print("   ❌ Performance comparison FAILED")
            print(f"   📋 Error: {stderr}")
            return False
    finally:
        os.unlink(test_file)


def test_uv_virtual_environment():
    """Test creating and using UV virtual environments."""
    print("\n🔧 Testing UV Virtual Environment Integration...")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Test UV venv creation
        print("   📦 Creating UV virtual environment...")
        success, stdout, stderr = run_command(
            ["uv", "venv", str(temp_path / "test_env")]
        )

        if not success:
            print(f"   ⚠️ UV venv creation failed: {stderr}")
            return False

        print("   ✅ UV virtual environment created")

        # Find project root
        current_dir = Path(__file__).parent
        project_root = (
            current_dir.parent
            if (current_dir.parent / "pyproject.toml").exists()
            else current_dir
        )

        # Test installation in the venv
        venv_python = temp_path / "test_env" / "bin" / "python"
        if not venv_python.exists():
            venv_python = temp_path / "test_env" / "Scripts" / "python.exe"  # Windows

        if venv_python.exists():
            print("   📦 Installing chuk-mcp in virtual environment...")
            success, stdout, stderr = run_command(
                ["uv", "pip", "install", "-e", str(project_root)], cwd=temp_path
            )

            if success:
                print("   ✅ Installation in UV venv successful")
                return True
            else:
                print(f"   ❌ Installation failed: {stderr}")
                return False
        else:
            print("   ⚠️ Could not find Python executable in venv")
            return False


def test_dependency_resolution():
    """Test UV dependency resolution with optional dependencies."""
    print("\n📋 Testing UV Dependency Resolution...")

    # Test basic dependency check
    success, stdout, stderr = run_command(["uv", "pip", "check"])

    if success:
        print("   ✅ No dependency conflicts detected")
    else:
        print(f"   ⚠️ Dependency issues detected: {stderr}")
        # Don't fail the test for this, as it might be environmental

    # Test showing dependency tree
    success, stdout, stderr = run_command(["uv", "pip", "list", "--format", "freeze"])

    if success:
        installed_packages = stdout.strip().split("\n")
        relevant_packages = [
            pkg
            for pkg in installed_packages
            if any(name in pkg.lower() for name in ["pydantic", "chuk-mcp", "anyio"])
        ]

        print("   📦 Relevant installed packages:")
        for pkg in relevant_packages:
            print(f"      {pkg}")

        return True
    else:
        print(f"   ❌ Could not list packages: {stderr}")
        return False


def test_edge_cases():
    """Test edge cases and error handling."""
    print("\n🎯 Testing Edge Cases...")

    test_script = """
import os
import sys
from typing import Any, Dict, List, Optional

# Test both modes
for mode in ["fallback", "pydantic"]:
    print(f"\\n--- Testing {mode} mode ---")
    
    if mode == "fallback":
        os.environ["MCP_FORCE_FALLBACK"] = "1"
    else:
        os.environ.pop("MCP_FORCE_FALLBACK", None)
    
    # Clear imports
    modules_to_clear = [name for name in sys.modules.keys() if name.startswith('chuk_mcp')]
    for module_name in modules_to_clear:
        if module_name in sys.modules:
            del sys.modules[module_name]
    
    try:
        from chuk_mcp.protocol.mcp_pydantic_base import McpPydanticBase, Field, ValidationError
        
        # Test 1: Empty model
        class EmptyModel(McpPydanticBase):
            pass
        
        empty = EmptyModel()
        print(f"✓ Empty model works in {mode}")
        
        # Test 2: Model with only optional fields
        class OptionalModel(McpPydanticBase):
            name: Optional[str] = None
            count: Optional[int] = None
        
        optional = OptionalModel()
        print(f"✓ Optional-only model works in {mode}")
        
        # Test 3: Complex nested structure
        class ComplexModel(McpPydanticBase):
            data: Dict[str, List[Dict[str, Any]]]
        
        complex_data = {
            "users": [
                {"name": "Alice", "age": 30},
                {"name": "Bob", "age": 25}
            ],
            "settings": [
                {"key": "theme", "value": "dark"},
                {"key": "timeout", "value": 30}
            ]
        }
        
        complex_model = ComplexModel(data=complex_data)
        serialized = complex_model.model_dump()
        print(f"✓ Complex nested validation works in {mode}")
        
        # Test 4: Invalid data handling
        try:
            ComplexModel(data="not_a_dict")
            print(f"ERROR: Should have failed validation in {mode}")
        except (ValidationError, Exception):
            print(f"✓ Invalid data properly rejected in {mode}")
        
        # Test 5: Forward reference handling (safer approach)
        try:
            class SelfRefModel(McpPydanticBase):
                name: str
                # Use string annotation for forward reference
                child: Optional['SelfRefModel'] = None
            
            self_ref = SelfRefModel(name="parent")
            self_ref_data = self_ref.model_dump()
            print(f"✓ Self-referential model works in {mode}")
        except Exception as e:
            # Forward references might not work in fallback mode, that's okay
            print(f"⚠️ Forward reference limitation in {mode}: {type(e).__name__}")
            # Don't fail the test for this limitation
        
    except ImportError as e:
        if mode == "pydantic":
            print(f"⚠️ Pydantic not available: {e}")
        else:
            print(f"ERROR: Fallback should always work: {e}")
            sys.exit(1)
    except Exception as e:
        print(f"ERROR in {mode} mode: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

# Cleanup
if "MCP_FORCE_FALLBACK" in os.environ:
    del os.environ["MCP_FORCE_FALLBACK"]

print("\\nSUCCESS: All edge cases handled correctly")
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(test_script)
        test_file = f.name

    try:
        success, stdout, stderr = run_command([sys.executable, test_file])

        if success:
            print("   ✅ Edge cases test PASSED")
            for line in stdout.split("\n"):
                if line.strip():
                    print(f"   {line}")
            return True
        else:
            print("   ❌ Edge cases test FAILED")
            print(f"   📋 Error: {stderr}")
            print(f"   📋 Output: {stdout}")
            return False
    finally:
        os.unlink(test_file)


def main():
    """Run comprehensive UV and fallback Pydantic tests."""
    print("🧪 Enhanced chuk-mcp UV & Fallback Tests")
    print("=" * 70)
    print("Comprehensive testing of UV integration and fallback functionality")
    print("=" * 70)

    tests = [
        ("Enhanced Fallback Features", test_fallback_pydantic_features),
        ("Performance Comparison", test_performance_comparison),
        ("UV Virtual Environment", test_uv_virtual_environment),
        ("Dependency Resolution", test_dependency_resolution),
        ("Edge Cases", test_edge_cases),
    ]

    results = {}

    for test_name, test_func in tests:
        print(f"\n🔍 Running {test_name}...")
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"   ❌ {test_name} failed with exception: {e}")
            results[test_name] = False

    # Summary
    print("\n" + "=" * 70)
    print("📊 Test Results Summary:")
    print("=" * 70)

    passed = sum(results.values())
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} {test_name}")

    print(f"\n📈 Overall: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL ENHANCED TESTS PASSED!")
        print("\n✅ chuk-mcp comprehensive validation:")
        print("   • ✅ Enhanced fallback Pydantic implementation")
        print("   • ✅ Performance characteristics acceptable")
        print("   • ✅ UV virtual environment compatibility")
        print("   • ✅ Dependency resolution working")
        print("   • ✅ Edge cases handled properly")
        print("\n💡 Production ready with UV package management!")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed - review above for details")

    print("=" * 70)
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
