"""
LLM client service for calling llm-proxy-service.
"""

from typing import Dict, List

import httpx

import sys
sys.path.append('../..')
from shared.common_types import LLMMessage, LLMRequest, LLMProvider
from shared.logging_config import get_logger

logger = get_logger(__name__)


class LLMClientService:
    """Service for calling LLM proxy."""

    def __init__(self, config: Dict):
        self.config = config
        llm_config = config.get("services", {}).get("llm_proxy", {})

        self.url = llm_config.get("url", "http://llm-proxy:8001")
        self.timeout = llm_config.get("timeout", 120)

        self.client = httpx.AsyncClient(base_url=self.url, timeout=self.timeout)

    async def close(self):
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()

    async def health_check(self) -> bool:
        """Check LLM proxy health."""
        try:
            response = await self.client.get("/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"LLM proxy health check failed: {e}")
            return False

    async def chat(
        self,
        messages: List[LLMMessage],
        model: str = "llama3.2:3b",
        temperature: float = 0.8,
        max_tokens: int = 1000,
    ) -> str:
        """
        Send chat request to LLM proxy.

        Args:
            messages: List of messages
            model: Model to use
            temperature: Temperature
            max_tokens: Max tokens

        Returns:
            Response text
        """
        try:
            request = LLMRequest(
                messages=messages,
                provider=LLMProvider.OLLAMA,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            response = await self.client.post(
                "/v1/chat/completions",
                json=request.model_dump(),
            )
            response.raise_for_status()

            data = response.json()
            return data.get("content", "")

        except httpx.HTTPError as e:
            logger.error(f"LLM request failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            raise
