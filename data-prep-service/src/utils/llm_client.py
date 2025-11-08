"""
LLM client for communicating with llm-proxy-service.
"""

import httpx
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

import sys
sys.path.append('../..')
from shared.logging_config import get_logger
from shared.common_types import LLMRequest, LLMMessage, LLMProvider

logger = get_logger(__name__)


class LLMClient:
    """Client for llm-proxy-service communication."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize LLM client.

        Args:
            config: Service configuration
        """
        self.config = config
        self.llm_proxy_url = config.get('llm_proxy', {}).get('url', 'http://llm-proxy-service:8001')
        self.timeout = config.get('llm_proxy', {}).get('timeout_seconds', 30)
        self.max_retries = config.get('llm_proxy', {}).get('max_retries', 3)
        self.client = httpx.AsyncClient(timeout=self.timeout)
        self.cache: Dict[str, Any] = {}

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    def _get_cache_key(self, prompt: str, model: str) -> str:
        """
        Generate cache key for a prompt.

        Args:
            prompt: The prompt text
            model: Model name

        Returns:
            Cache key
        """
        import hashlib
        content = f"{model}:{prompt}"
        return hashlib.md5(content.encode()).hexdigest()

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        use_cache: bool = True,
    ) -> Optional[str]:
        """
        Generate text using LLM.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            model: Model name (uses config default if not provided)
            temperature: Sampling temperature
            use_cache: Whether to use cached responses

        Returns:
            Generated text or None if failed
        """
        # Use model from config if not provided
        if not model:
            model = self.config.get('processing', {}).get('llm_enhancement', {}).get('model', 'llama3.2')

        # Check cache
        cache_key = self._get_cache_key(prompt, model)
        if use_cache and cache_key in self.cache:
            logger.debug(f"Cache hit for prompt: {prompt[:50]}...")
            return self.cache[cache_key]

        # Build messages
        messages = []
        if system_prompt:
            messages.append(LLMMessage(role="system", content=system_prompt))
        messages.append(LLMMessage(role="user", content=prompt))

        # Create request
        llm_request = LLMRequest(
            messages=messages,
            provider=LLMProvider.OLLAMA,
            model=model,
            temperature=temperature,
            stream=False,
        )

        # Try with retries
        for attempt in range(self.max_retries):
            try:
                response = await self.client.post(
                    f"{self.llm_proxy_url}/chat/completions",
                    json=llm_request.model_dump(),
                )

                if response.status_code == 200:
                    result = response.json()
                    content = result.get('content', '')

                    # Cache the result
                    if use_cache:
                        self.cache[cache_key] = content

                    return content
                else:
                    logger.warning(
                        f"LLM request failed with status {response.status_code}: {response.text}"
                    )

            except httpx.TimeoutException:
                logger.warning(f"LLM request timeout (attempt {attempt + 1}/{self.max_retries})")
            except httpx.RequestError as e:
                logger.warning(f"LLM request error (attempt {attempt + 1}/{self.max_retries}): {e}")
            except Exception as e:
                logger.error(f"Unexpected error during LLM request: {e}", exc_info=True)

            # Wait before retry (exponential backoff)
            if attempt < self.max_retries - 1:
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)

        logger.error(f"Failed to get LLM response after {self.max_retries} attempts")
        return None

    async def batch_generate(
        self,
        prompts: List[str],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        batch_size: int = 5,
        rate_limit_delay: float = 0.5,
    ) -> List[Optional[str]]:
        """
        Generate text for multiple prompts with batching and rate limiting.

        Args:
            prompts: List of prompts
            system_prompt: Optional system prompt
            model: Model name
            temperature: Sampling temperature
            batch_size: Number of concurrent requests
            rate_limit_delay: Delay between batches in seconds

        Returns:
            List of generated texts (None for failures)
        """
        results = []

        for i in range(0, len(prompts), batch_size):
            batch = prompts[i:i + batch_size]

            # Process batch concurrently
            tasks = [
                self.generate(
                    prompt=p,
                    system_prompt=system_prompt,
                    model=model,
                    temperature=temperature,
                )
                for p in batch
            ]

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle exceptions
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch generation error: {result}")
                    results.append(None)
                else:
                    results.append(result)

            # Rate limiting delay
            if i + batch_size < len(prompts):
                await asyncio.sleep(rate_limit_delay)

        return results

    async def health_check(self) -> bool:
        """
        Check if LLM proxy service is healthy.

        Returns:
            True if service is healthy
        """
        try:
            response = await self.client.get(
                f"{self.llm_proxy_url}/health",
                timeout=5.0,
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"LLM proxy health check failed: {e}")
            return False

    def clear_cache(self):
        """Clear the response cache."""
        self.cache.clear()
        logger.info("LLM response cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Cache statistics
        """
        return {
            "cache_size": len(self.cache),
            "cache_keys": list(self.cache.keys())[:10],  # First 10 keys
        }
