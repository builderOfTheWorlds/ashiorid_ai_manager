"""
Additional schemas specific to LLM Proxy Service.

Extends the shared common_types with proxy-specific models.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ProviderConfig(BaseModel):
    """Configuration for an LLM provider."""

    name: str
    enabled: bool = True
    base_url: str
    models: List[str]
    default_model: str
    timeout: int = 120
    max_retries: int = 3
    api_key: Optional[str] = None


class CacheStats(BaseModel):
    """Cache statistics."""

    enabled: bool
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    hit_rate: float = 0.0
    size: int = 0
    max_size: int = 0


class ProviderStats(BaseModel):
    """Statistics for a provider."""

    name: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    average_latency_ms: float = 0.0


class ServiceStats(BaseModel):
    """Overall service statistics."""

    uptime_seconds: float
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    cache_stats: CacheStats
    provider_stats: List[ProviderStats]


class CostBreakdown(BaseModel):
    """Cost breakdown by provider and model."""

    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0


class CostSummary(BaseModel):
    """Summary of costs across all providers."""

    total_cost_usd: float = 0.0
    by_provider: Dict[str, float] = Field(default_factory=dict)
    by_model: List[CostBreakdown] = Field(default_factory=list)
    period_start: Optional[str] = None
    period_end: Optional[str] = None
