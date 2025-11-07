"""
Tests for base_config module.
"""

import os
import pytest
from shared.base_config import get_env, merge_configs, _deep_merge


class TestGetEnv:
    """Tests for get_env function."""

    def test_get_env_string_default(self):
        """Test getting string env var with default."""
        # Unset var should return default
        result = get_env("NONEXISTENT_VAR", "default_value")
        assert result == "default_value"

    def test_get_env_string_set(self):
        """Test getting string env var when set."""
        os.environ["TEST_STRING_VAR"] = "test_value"
        result = get_env("TEST_STRING_VAR", "default")
        assert result == "test_value"
        del os.environ["TEST_STRING_VAR"]

    def test_get_env_int_normal(self):
        """Test getting int env var with normal integer string."""
        os.environ["TEST_INT_VAR"] = "5432"
        result = get_env("TEST_INT_VAR", 1234, value_type=int)
        assert result == 5432
        assert isinstance(result, int)
        del os.environ["TEST_INT_VAR"]

    def test_get_env_int_from_tcp_url(self):
        """Test extracting port number from Kubernetes TCP URL."""
        # This is the main bug fix - Kubernetes sets POSTGRES_PORT to tcp://host:port
        os.environ["TEST_PORT_VAR"] = "tcp://10.43.125.137:5432"
        result = get_env("TEST_PORT_VAR", 1234, value_type=int)
        assert result == 5432
        assert isinstance(result, int)
        del os.environ["TEST_PORT_VAR"]

    def test_get_env_int_from_http_url(self):
        """Test extracting port number from HTTP URL."""
        os.environ["TEST_PORT_VAR"] = "http://localhost:8080"
        result = get_env("TEST_PORT_VAR", 1234, value_type=int)
        assert result == 8080
        assert isinstance(result, int)
        del os.environ["TEST_PORT_VAR"]

    def test_get_env_int_from_https_url(self):
        """Test extracting port number from HTTPS URL."""
        os.environ["TEST_PORT_VAR"] = "https://example.com:443/path"
        result = get_env("TEST_PORT_VAR", 1234, value_type=int)
        assert result == 443
        assert isinstance(result, int)
        del os.environ["TEST_PORT_VAR"]

    def test_get_env_int_url_without_port_fails(self):
        """Test that URL without port raises ValueError."""
        os.environ["TEST_PORT_VAR"] = "tcp://10.43.125.137"
        with pytest.raises(ValueError, match="No port found in URL"):
            get_env("TEST_PORT_VAR", 1234, value_type=int)
        del os.environ["TEST_PORT_VAR"]

    def test_get_env_int_invalid_fails(self):
        """Test that invalid int string raises ValueError."""
        os.environ["TEST_INT_VAR"] = "not_a_number"
        with pytest.raises(ValueError, match="Failed to convert"):
            get_env("TEST_INT_VAR", 1234, value_type=int)
        del os.environ["TEST_INT_VAR"]

    def test_get_env_float(self):
        """Test getting float env var."""
        os.environ["TEST_FLOAT_VAR"] = "3.14"
        result = get_env("TEST_FLOAT_VAR", 1.0, value_type=float)
        assert result == 3.14
        assert isinstance(result, float)
        del os.environ["TEST_FLOAT_VAR"]

    def test_get_env_bool_true_values(self):
        """Test boolean true values."""
        true_values = ["true", "TRUE", "True", "1", "yes", "YES", "on", "ON"]
        for val in true_values:
            os.environ["TEST_BOOL_VAR"] = val
            result = get_env("TEST_BOOL_VAR", False, value_type=bool)
            assert result is True, f"Failed for value: {val}"
            del os.environ["TEST_BOOL_VAR"]

    def test_get_env_bool_false_values(self):
        """Test boolean false values."""
        false_values = ["false", "FALSE", "0", "no", "NO", "off", "OFF"]
        for val in false_values:
            os.environ["TEST_BOOL_VAR"] = val
            result = get_env("TEST_BOOL_VAR", True, value_type=bool)
            assert result is False, f"Failed for value: {val}"
            del os.environ["TEST_BOOL_VAR"]

    def test_get_env_required_missing_fails(self):
        """Test that required missing var raises ValueError."""
        with pytest.raises(ValueError, match="Required environment variable not set"):
            get_env("NONEXISTENT_REQUIRED_VAR", required=True)

    def test_get_env_required_set(self):
        """Test that required set var returns value."""
        os.environ["TEST_REQUIRED_VAR"] = "value"
        result = get_env("TEST_REQUIRED_VAR", required=True)
        assert result == "value"
        del os.environ["TEST_REQUIRED_VAR"]


class TestMergeConfigs:
    """Tests for merge_configs function."""

    def test_merge_two_configs(self):
        """Test merging two simple configs."""
        config1 = {"a": 1, "b": 2}
        config2 = {"b": 3, "c": 4}
        result = merge_configs(config1, config2)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_merge_nested_configs(self):
        """Test merging nested configs."""
        config1 = {"service": {"name": "test", "port": 8000}, "database": {"host": "localhost"}}
        config2 = {"service": {"port": 9000, "debug": True}, "redis": {"host": "localhost"}}
        result = merge_configs(config1, config2)
        assert result == {
            "service": {"name": "test", "port": 9000, "debug": True},
            "database": {"host": "localhost"},
            "redis": {"host": "localhost"},
        }

    def test_merge_multiple_configs(self):
        """Test merging more than two configs."""
        config1 = {"a": 1}
        config2 = {"b": 2}
        config3 = {"c": 3}
        result = merge_configs(config1, config2, config3)
        assert result == {"a": 1, "b": 2, "c": 3}


class TestDeepMerge:
    """Tests for _deep_merge function."""

    def test_deep_merge_flat(self):
        """Test deep merge with flat dicts."""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_deep_merge_nested(self):
        """Test deep merge with nested dicts."""
        base = {"a": {"b": 1, "c": 2}, "d": 3}
        override = {"a": {"b": 10}, "e": 4}
        result = _deep_merge(base, override)
        assert result == {"a": {"b": 10, "c": 2}, "d": 3, "e": 4}

    def test_deep_merge_preserves_base(self):
        """Test that deep merge doesn't modify the base dict."""
        base = {"a": {"b": 1}}
        override = {"a": {"c": 2}}
        result = _deep_merge(base, override)
        # Original base should be unchanged
        assert base == {"a": {"b": 1}}
        # Result should have merged values
        assert result == {"a": {"b": 1, "c": 2}}
