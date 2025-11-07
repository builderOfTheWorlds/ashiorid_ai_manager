"""
Tests for base_config module.
"""

import os
from base_config import get_env


class TestGetEnv:
    """Tests for get_env function."""

    def test_get_env_with_kubernetes_url_format(self):
        """Test that get_env can parse port from Kubernetes service URL format."""
        # Simulate Kubernetes environment variable
        os.environ["TEST_PORT"] = "tcp://10.43.125.137:5432"

        result = get_env("TEST_PORT", value_type=int)

        assert result == 5432

        # Clean up
        del os.environ["TEST_PORT"]

    def test_get_env_with_regular_port(self):
        """Test that get_env still works with regular port numbers."""
        os.environ["TEST_PORT"] = "5432"

        result = get_env("TEST_PORT", value_type=int)

        assert result == 5432

        # Clean up
        del os.environ["TEST_PORT"]

    def test_get_env_with_default(self):
        """Test that get_env returns default when variable not set."""
        result = get_env("NONEXISTENT_VAR", default=8080, value_type=int)

        assert result == 8080

    def test_get_env_with_redis_url_format(self):
        """Test parsing Redis service URL format."""
        os.environ["REDIS_PORT"] = "tcp://10.43.125.138:6379"

        result = get_env("REDIS_PORT", value_type=int)

        assert result == 6379

        # Clean up
        del os.environ["REDIS_PORT"]

    def test_get_env_with_qdrant_url_format(self):
        """Test parsing Qdrant service URL format."""
        os.environ["QDRANT_PORT"] = "tcp://10.43.125.139:6333"

        result = get_env("QDRANT_PORT", value_type=int)

        assert result == 6333

        # Clean up
        del os.environ["QDRANT_PORT"]

    def test_get_env_bool_conversion(self):
        """Test boolean conversion."""
        os.environ["TEST_BOOL"] = "true"
        assert get_env("TEST_BOOL", value_type=bool) is True

        os.environ["TEST_BOOL"] = "false"
        assert get_env("TEST_BOOL", value_type=bool) is False

        os.environ["TEST_BOOL"] = "1"
        assert get_env("TEST_BOOL", value_type=bool) is True

        os.environ["TEST_BOOL"] = "0"
        assert get_env("TEST_BOOL", value_type=bool) is False

        # Clean up
        del os.environ["TEST_BOOL"]


if __name__ == "__main__":
    # Run the tests
    test = TestGetEnv()

    print("Testing Kubernetes URL format parsing...")
    test.test_get_env_with_kubernetes_url_format()
    print("✓ Kubernetes URL format test passed")

    print("Testing regular port number...")
    test.test_get_env_with_regular_port()
    print("✓ Regular port test passed")

    print("Testing default value...")
    test.test_get_env_with_default()
    print("✓ Default value test passed")

    print("Testing Redis URL format...")
    test.test_get_env_with_redis_url_format()
    print("✓ Redis URL format test passed")

    print("Testing Qdrant URL format...")
    test.test_get_env_with_qdrant_url_format()
    print("✓ Qdrant URL format test passed")

    print("Testing boolean conversion...")
    test.test_get_env_bool_conversion()
    print("✓ Boolean conversion test passed")

    print("\n✅ All tests passed!")
