"""Unit tests for base_config module."""

import os
import pytest
from base_config import get_env


class TestGetEnv:
    """Test environment variable parsing with type conversion."""

    def test_get_env_kubernetes_port_format(self):
        """Test parsing port from Kubernetes service URL format."""
        # Set up environment variable with Kubernetes format
        os.environ["TEST_PORT"] = "tcp://10.43.125.137:5432"

        # Should extract port 5432 from the URL
        result = get_env("TEST_PORT", value_type=int)
        assert result == 5432

        # Clean up
        del os.environ["TEST_PORT"]

    def test_get_env_plain_port_number(self):
        """Test parsing plain integer port number."""
        os.environ["TEST_PORT"] = "5432"

        result = get_env("TEST_PORT", value_type=int)
        assert result == 5432

        del os.environ["TEST_PORT"]

    def test_get_env_redis_port_format(self):
        """Test parsing Redis port from Kubernetes format."""
        os.environ["REDIS_PORT"] = "tcp://10.43.125.138:6379"

        result = get_env("REDIS_PORT", value_type=int)
        assert result == 6379

        del os.environ["REDIS_PORT"]

    def test_get_env_qdrant_port_format(self):
        """Test parsing Qdrant port from Kubernetes format."""
        os.environ["QDRANT_PORT"] = "tcp://10.43.125.139:6333"

        result = get_env("QDRANT_PORT", value_type=int)
        assert result == 6333

        del os.environ["QDRANT_PORT"]

    def test_get_env_default_value(self):
        """Test that default value is returned when env var is not set."""
        result = get_env("NONEXISTENT_VAR", default=9999, value_type=int)
        assert result == 9999

    def test_get_env_string_value(self):
        """Test getting string environment variable."""
        os.environ["TEST_STRING"] = "hello"

        result = get_env("TEST_STRING")
        assert result == "hello"

        del os.environ["TEST_STRING"]

    def test_get_env_bool_value(self):
        """Test boolean conversion."""
        os.environ["TEST_BOOL"] = "true"

        result = get_env("TEST_BOOL", value_type=bool)
        assert result is True

        del os.environ["TEST_BOOL"]

    def test_get_env_float_value(self):
        """Test float conversion."""
        os.environ["TEST_FLOAT"] = "3.14"

        result = get_env("TEST_FLOAT", value_type=float)
        assert result == 3.14

        del os.environ["TEST_FLOAT"]

    def test_get_env_required_missing(self):
        """Test that error is raised for required missing variable."""
        with pytest.raises(ValueError, match="Required environment variable not set"):
            get_env("MISSING_REQUIRED", required=True)

    def test_get_env_url_with_path(self):
        """Test parsing port from URL with path."""
        os.environ["TEST_PORT"] = "tcp://10.43.125.137:5432/db"

        result = get_env("TEST_PORT", value_type=int)
        assert result == 5432

        del os.environ["TEST_PORT"]

    def test_get_env_hostname_port_format(self):
        """Test parsing port from hostname:port format with protocol."""
        os.environ["TEST_PORT"] = "tcp://postgres-service:5432"

        result = get_env("TEST_PORT", value_type=int)
        assert result == 5432

        del os.environ["TEST_PORT"]
