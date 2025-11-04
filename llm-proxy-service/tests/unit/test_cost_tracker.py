"""
Unit tests for cost tracker.
"""

import pytest
from src.utils.cost_tracker import CostTracker
from shared.common_types import LLMResponse, LLMProvider


class TestCostTracker:
    """Test cost tracking functionality."""

    @pytest.fixture
    def cost_tracker(self):
        """Create a cost tracker instance."""
        config = {
            "enabled": True,
            "pricing": {
                "openai": {
                    "gpt-3.5-turbo": {"prompt": 0.0005, "completion": 0.0015}
                },
                "ollama": {
                    "default": {"prompt": 0.0, "completion": 0.0}
                },
            },
        }
        return CostTracker(config)

    @pytest.mark.asyncio
    async def test_track_request(self, cost_tracker):
        """Test tracking a request."""
        response = LLMResponse(
            content="Test response",
            provider=LLMProvider.OPENAI,
            model="gpt-3.5-turbo",
            usage={
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            },
            latency_ms=100.0,
        )

        await cost_tracker.track_request(response)

        summary = await cost_tracker.get_summary()
        assert summary.total_cost_usd > 0
        assert "openai" in summary.by_provider

    @pytest.mark.asyncio
    async def test_ollama_cost_is_zero(self, cost_tracker):
        """Test that Ollama costs are zero."""
        response = LLMResponse(
            content="Test response",
            provider=LLMProvider.OLLAMA,
            model="llama3.2:3b",
            usage={
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            },
            latency_ms=100.0,
        )

        await cost_tracker.track_request(response)

        summary = await cost_tracker.get_summary()
        assert summary.by_provider.get("ollama", 0.0) == 0.0
