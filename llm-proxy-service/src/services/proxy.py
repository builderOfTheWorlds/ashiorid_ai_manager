"""
LLM Proxy Service - main orchestration layer.

Handles:
- Provider selection and failover
- Request caching
- Rate limiting
- Cost tracking
- Request batching
"""

import hashlib
import json
import time
from typing import Dict, List, Optional

import redis.asyncio as aioredis

import sys
sys.path.append('../..')
from shared.common_types import LLMRequest, LLMResponse, LLMProvider
from shared.logging_config import get_logger

from src.services.providers import create_provider, BaseLLMProvider
from src.utils.cost_tracker import CostTracker
from src.models.schemas import CacheStats, ProviderStats, ServiceStats, CostSummary

logger = get_logger(__name__)


class LLMProxyService:
    """Main LLM Proxy Service."""

    def __init__(self, config: Dict):
        self.config = config
        self.providers: Dict[str, BaseLLMProvider] = {}
        self.redis_client: Optional[aioredis.Redis] = None
        self.cost_tracker = CostTracker(config.get("cost_tracking", {}))
        self.start_time = time.time()

        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }
        self.provider_stats: Dict[str, Dict] = {}

    async def initialize(self):
        """Initialize the proxy service."""
        logger.info("Initializing LLM Proxy Service")

        # Initialize providers
        provider_configs = self.config.get("providers", {})
        for provider_name, provider_config in provider_configs.items():
            if provider_config.get("enabled", True):
                try:
                    provider = create_provider(provider_name, provider_config)
                    self.providers[provider_name] = provider
                    self.provider_stats[provider_name] = {
                        "total_requests": 0,
                        "successful_requests": 0,
                        "failed_requests": 0,
                        "total_tokens": 0,
                        "total_latency_ms": 0,
                    }
                    logger.info(f"Initialized provider: {provider_name}")
                except Exception as e:
                    logger.error(f"Failed to initialize provider {provider_name}: {e}")

        # Initialize Redis for caching
        if self.config.get("cache", {}).get("enabled", False):
            try:
                redis_config = self.config.get("redis", {})
                self.redis_client = await aioredis.from_url(
                    redis_config.get("url") or f"redis://{redis_config.get('host', 'redis')}:{redis_config.get('port', 6379)}",
                    decode_responses=True,
                )
                logger.info("Redis cache initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Redis: {e}")
                self.config["cache"]["enabled"] = False

        logger.info(f"LLM Proxy Service initialized with {len(self.providers)} providers")

    async def shutdown(self):
        """Shutdown the proxy service."""
        logger.info("Shutting down LLM Proxy Service")

        # Close Redis connection
        if self.redis_client:
            await self.redis_client.close()

        # Close provider connections (if needed)
        for provider in self.providers.values():
            if hasattr(provider, "close"):
                await provider.close()

        logger.info("LLM Proxy Service shutdown complete")

    async def process_request(self, request: LLMRequest) -> LLMResponse:
        """
        Process an LLM request.

        Handles caching, provider selection, and error handling.
        """
        self.stats["total_requests"] += 1
        start_time = time.time()

        try:
            # Check cache first
            if self.config.get("cache", {}).get("enabled", False):
                cached_response = await self._get_cached_response(request)
                if cached_response:
                    self.stats["cache_hits"] += 1
                    logger.debug("Cache hit")
                    return cached_response
                self.stats["cache_misses"] += 1

            # Select provider
            provider_name = request.provider.value if request.provider else self.config.get("default_provider", "ollama")
            provider = self.providers.get(provider_name)

            if not provider or not provider.enabled:
                raise ValueError(f"Provider {provider_name} is not available")

            # Update provider stats
            self.provider_stats[provider_name]["total_requests"] += 1

            # Generate response
            response = await provider.generate(request)

            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000
            response.latency_ms = latency_ms

            # Update stats
            self.stats["successful_requests"] += 1
            self.provider_stats[provider_name]["successful_requests"] += 1
            self.provider_stats[provider_name]["total_tokens"] += response.usage.get("total_tokens", 0)
            self.provider_stats[provider_name]["total_latency_ms"] += latency_ms

            # Track cost
            await self.cost_tracker.track_request(response)

            # Cache response
            if self.config.get("cache", {}).get("enabled", False):
                await self._cache_response(request, response)

            return response

        except Exception as e:
            self.stats["failed_requests"] += 1
            if provider_name in self.provider_stats:
                self.provider_stats[provider_name]["failed_requests"] += 1
            logger.error(f"Request processing failed: {e}")
            raise

    async def _get_cached_response(self, request: LLMRequest) -> Optional[LLMResponse]:
        """Get cached response if available."""
        if not self.redis_client:
            return None

        try:
            cache_key = self._generate_cache_key(request)
            cached_data = await self.redis_client.get(cache_key)

            if cached_data:
                response_dict = json.loads(cached_data)
                response = LLMResponse(**response_dict)
                response.cached = True
                return response

        except Exception as e:
            logger.error(f"Cache retrieval error: {e}")

        return None

    async def _cache_response(self, request: LLMRequest, response: LLMResponse):
        """Cache a response."""
        if not self.redis_client:
            return

        try:
            cache_key = self._generate_cache_key(request)
            cache_ttl = self.config.get("cache", {}).get("ttl", 3600)

            response_dict = response.model_dump()
            await self.redis_client.setex(
                cache_key,
                cache_ttl,
                json.dumps(response_dict),
            )

        except Exception as e:
            logger.error(f"Cache storage error: {e}")

    def _generate_cache_key(self, request: LLMRequest) -> str:
        """Generate a cache key for a request."""
        # Create a deterministic key from request parameters
        key_data = {
            "provider": request.provider.value if request.provider else "",
            "model": request.model or "",
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        key_string = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()
        return f"llm_cache:{key_hash}"

    async def check_providers(self) -> Dict[str, bool]:
        """Check health of all providers."""
        health_status = {}

        for provider_name, provider in self.providers.items():
            try:
                is_healthy = await provider.check_health()
                health_status[provider_name] = is_healthy
            except Exception as e:
                logger.error(f"Health check failed for {provider_name}: {e}")
                health_status[provider_name] = False

        return health_status

    async def get_providers_info(self) -> List[Dict]:
        """Get information about all providers."""
        providers_info = []

        for provider_name, provider in self.providers.items():
            providers_info.append({
                "name": provider_name,
                "enabled": provider.enabled,
                "models": provider.models,
                "default_model": provider.default_model,
            })

        return providers_info

    async def get_provider_models(self, provider_name: str) -> List[str]:
        """Get available models for a provider."""
        provider = self.providers.get(provider_name)
        if not provider:
            raise ValueError(f"Provider {provider_name} not found")

        return provider.models

    async def get_stats(self) -> ServiceStats:
        """Get service statistics."""
        uptime = time.time() - self.start_time

        # Cache stats
        cache_stats = CacheStats(
            enabled=self.config.get("cache", {}).get("enabled", False),
            total_requests=self.stats["total_requests"],
            cache_hits=self.stats["cache_hits"],
            cache_misses=self.stats["cache_misses"],
            hit_rate=self.stats["cache_hits"] / max(self.stats["total_requests"], 1),
            size=0,  # TODO: Get from Redis
            max_size=self.config.get("cache", {}).get("max_size", 10000),
        )

        # Provider stats
        provider_stats_list = []
        for provider_name, stats in self.provider_stats.items():
            avg_latency = stats["total_latency_ms"] / max(stats["total_requests"], 1)
            provider_stats_list.append(ProviderStats(
                name=provider_name,
                total_requests=stats["total_requests"],
                successful_requests=stats["successful_requests"],
                failed_requests=stats["failed_requests"],
                total_tokens=stats["total_tokens"],
                total_cost=0.0,  # Will be populated by cost tracker
                average_latency_ms=avg_latency,
            ))

        return ServiceStats(
            uptime_seconds=uptime,
            total_requests=self.stats["total_requests"],
            successful_requests=self.stats["successful_requests"],
            failed_requests=self.stats["failed_requests"],
            cache_stats=cache_stats,
            provider_stats=provider_stats_list,
        )

    async def clear_cache(self):
        """Clear the response cache."""
        if not self.redis_client:
            return

        try:
            # Delete all keys matching llm_cache:*
            cursor = 0
            while True:
                cursor, keys = await self.redis_client.scan(
                    cursor=cursor,
                    match="llm_cache:*",
                    count=100,
                )
                if keys:
                    await self.redis_client.delete(*keys)
                if cursor == 0:
                    break

            logger.info("Cache cleared")
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            raise

    async def get_cost_summary(self) -> CostSummary:
        """Get cost summary from cost tracker."""
        return await self.cost_tracker.get_summary()
