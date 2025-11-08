#!/usr/bin/env python3
"""
Simple test script to verify the TCP URL port parsing fix.
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, '/home/user/ashiorid_ai_manager')

# Import directly from the module file to avoid dependency issues
import importlib.util
spec = importlib.util.spec_from_file_location("base_config", "/home/user/ashiorid_ai_manager/shared/base_config.py")
base_config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base_config)
get_env = base_config.get_env


def test_tcp_url_parsing():
    """Test that TCP URLs are correctly parsed for port numbers."""
    print("Testing TCP URL port parsing...")

    # Test 1: Normal integer string
    os.environ["TEST_PORT_1"] = "5432"
    result = get_env("TEST_PORT_1", value_type=int)
    assert result == 5432, f"Expected 5432, got {result}"
    print("✓ Test 1 passed: Normal integer string '5432' -> 5432")
    del os.environ["TEST_PORT_1"]

    # Test 2: TCP URL (the main bug we're fixing)
    os.environ["TEST_PORT_2"] = "tcp://10.43.125.137:5432"
    result = get_env("TEST_PORT_2", value_type=int)
    assert result == 5432, f"Expected 5432, got {result}"
    print("✓ Test 2 passed: TCP URL 'tcp://10.43.125.137:5432' -> 5432")
    del os.environ["TEST_PORT_2"]

    # Test 3: HTTP URL with port
    os.environ["TEST_PORT_3"] = "http://localhost:8080"
    result = get_env("TEST_PORT_3", value_type=int)
    assert result == 8080, f"Expected 8080, got {result}"
    print("✓ Test 3 passed: HTTP URL 'http://localhost:8080' -> 8080")
    del os.environ["TEST_PORT_3"]

    # Test 4: HTTPS URL with port and path
    os.environ["TEST_PORT_4"] = "https://example.com:443/path"
    result = get_env("TEST_PORT_4", value_type=int)
    assert result == 443, f"Expected 443, got {result}"
    print("✓ Test 4 passed: HTTPS URL 'https://example.com:443/path' -> 443")
    del os.environ["TEST_PORT_4"]

    # Test 5: Default value when env var not set
    result = get_env("NONEXISTENT_PORT", 9999, value_type=int)
    assert result == 9999, f"Expected 9999, got {result}"
    print("✓ Test 5 passed: Nonexistent var returns default 9999")

    # Test 6: URL without port should fail
    os.environ["TEST_PORT_6"] = "tcp://10.43.125.137"
    try:
        result = get_env("TEST_PORT_6", value_type=int)
        assert False, "Expected ValueError for URL without port"
    except ValueError as e:
        assert "No port found in URL" in str(e), f"Unexpected error message: {e}"
        print("✓ Test 6 passed: URL without port raises ValueError")
    finally:
        del os.environ["TEST_PORT_6"]

    print("\n🎉 All tests passed! The fix works correctly.")


if __name__ == "__main__":
    try:
        test_tcp_url_parsing()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
