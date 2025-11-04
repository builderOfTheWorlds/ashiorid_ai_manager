"""
Cost tracking for LLM requests.

Tracks token usage and costs across all providers.
"""

from collections import defaultdict
from typing import Dict

import sys
sys.path.append('../..')
from shared.common_types import LLMResponse
from shared.logging_config import get_logger

from src.models.schemas import CostSummary, CostBreakdown

logger = get_logger(__name__)


class CostTracker:
    """Track costs for LLM requests."""

    def __init__(self, config: Dict):
        self.config = config
        self.enabled = config.get("enabled", True)
        self.pricing = config.get("pricing", {})

        # Cost tracking storage
        self.costs_by_provider: Dict[str, float] = defaultdict(float)
        self.costs_by_model: Dict[str, Dict] = defaultdict(
            lambda: {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_usd": 0.0,
            }
        )

    async def track_request(self, response: LLMResponse):
        """
        Track the cost of an LLM request.

        Args:
            response: LLM response containing usage information
        """
        if not self.enabled:
            return

        try:
            provider = response.provider.value
            model = response.model
            usage = response.usage

            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)

            # Calculate cost
            cost = self._calculate_cost(provider, model, prompt_tokens, completion_tokens)

            # Update totals
            self.costs_by_provider[provider] += cost

            key = f"{provider}:{model}"
            self.costs_by_model[key]["prompt_tokens"] += prompt_tokens
            self.costs_by_model[key]["completion_tokens"] += completion_tokens
            self.costs_by_model[key]["total_tokens"] += prompt_tokens + completion_tokens
            self.costs_by_model[key]["cost_usd"] += cost

            logger.debug(
                f"Cost tracked: provider={provider}, model={model}, "
                f"tokens={prompt_tokens + completion_tokens}, cost=${cost:.6f}"
            )

        except Exception as e:
            logger.error(f"Error tracking cost: {e}")

    def _calculate_cost(
        self,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """
        Calculate the cost of a request.

        Args:
            provider: Provider name
            model: Model name
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens

        Returns:
            Cost in USD
        """
        provider_pricing = self.pricing.get(provider, {})
        model_pricing = provider_pricing.get(model)

        if not model_pricing:
            # Try default pricing for provider
            model_pricing = provider_pricing.get("default", {"prompt": 0.0, "completion": 0.0})

        prompt_cost_per_1k = model_pricing.get("prompt", 0.0)
        completion_cost_per_1k = model_pricing.get("completion", 0.0)

        prompt_cost = (prompt_tokens / 1000) * prompt_cost_per_1k
        completion_cost = (completion_tokens / 1000) * completion_cost_per_1k

        return prompt_cost + completion_cost

    async def get_summary(self) -> CostSummary:
        """
        Get a summary of costs.

        Returns:
            Cost summary
        """
        total_cost = sum(self.costs_by_provider.values())

        by_model = []
        for key, data in self.costs_by_model.items():
            provider, model = key.split(":", 1)
            by_model.append(
                CostBreakdown(
                    provider=provider,
                    model=model,
                    prompt_tokens=data["prompt_tokens"],
                    completion_tokens=data["completion_tokens"],
                    total_tokens=data["total_tokens"],
                    cost_usd=data["cost_usd"],
                )
            )

        return CostSummary(
            total_cost_usd=total_cost,
            by_provider=dict(self.costs_by_provider),
            by_model=by_model,
        )

    def reset(self):
        """Reset all cost tracking."""
        self.costs_by_provider.clear()
        self.costs_by_model.clear()
        logger.info("Cost tracking reset")
