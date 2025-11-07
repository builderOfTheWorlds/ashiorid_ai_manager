"""Quick test to verify port parsing from Kubernetes service URL format."""

import os
import sys

# Add shared directory to path
sys.path.insert(0, '/home/user/ashiorid_ai_manager/shared')

# Import just the get_env function (without importing other dependencies)
import importlib.util
spec = importlib.util.spec_from_file_location("base_config", "/home/user/ashiorid_ai_manager/shared/base_config.py")
base_config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base_config)

get_env = base_config.get_env


def test_kubernetes_port_parsing():
    """Test parsing port from Kubernetes service URL format."""
    test_cases = [
        ("tcp://10.43.125.137:5432", 5432),
        ("tcp://redis:6379", 6379),
        ("tcp://10.43.125.139:6333", 6333),
        ("5432", 5432),  # Plain number should still work
        ("tcp://postgres-service:5432/db", 5432),  # With path
    ]

    print("Testing port parsing from Kubernetes service URL format...\n")

    all_passed = True
    for test_value, expected_port in test_cases:
        os.environ["TEST_PORT"] = test_value
        try:
            result = get_env("TEST_PORT", value_type=int)
            if result == expected_port:
                print(f"✓ PASS: '{test_value}' -> {result}")
            else:
                print(f"✗ FAIL: '{test_value}' -> {result} (expected {expected_port})")
                all_passed = False
        except Exception as e:
            print(f"✗ ERROR: '{test_value}' raised {type(e).__name__}: {e}")
            all_passed = False
        finally:
            del os.environ["TEST_PORT"]

    print()
    if all_passed:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(test_kubernetes_port_parsing())
