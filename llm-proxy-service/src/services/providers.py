"""
LLM Provider implementations.

Supports OpenAI, Anthropic, and Ollama.
"""

import os
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

import httpx
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

import sys
sys.path.append('../..')
from shared.common_types import LLMRequest, LLMResponse, LLMProvider, LLMMessage
from shared.logging_config import get_logger

logger = get_logger(__name__)


class BaseLLMProvider(ABC):
    """Base class for LLM providers."""

    def __init__(self, config: Dict):
        self.config = config
        self.name = config.get("name", "unknown")
        self.enabled = config.get("enabled", True)
        self.base_url = config.get("base_url")
        self.models = config.get("models", [])
        self.default_model = config.get("default_model")
        self.timeout = config.get("timeout", 120)
        self.max_retries = config.get("max_retries", 3)

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a response from the LLM."""
        pass

    @abstractmethod
    async def check_health(self) -> bool:
        """Check if the provider is healthy."""
        pass

    def get_model(self, requested_model: Optional[str]) -> str:
        """Get the model to use, defaulting if necessary."""
        if requested_model and requested_model in self.models:
            return requested_model
        return self.default_model


class OpenAIProvider(BaseLLMProvider):
    """OpenAI provider implementation."""

    def __init__(self, config: Dict):
        super().__init__(config)
        api_key = os.getenv(config.get("api_key_env", "OPENAI_API_KEY"))
        if not api_key:
            logger.warning("OpenAI API key not found, provider will be disabled")
            self.enabled = False
        else:
            self.client = AsyncOpenAI(
                api_key=api_key,
                base_url=self.base_url,
                timeout=self.timeout,
                max_retries=self.max_retries,
            )

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate response using OpenAI API."""
        if not self.enabled:
            raise ValueError("OpenAI provider is not enabled")

        model = self.get_model(request.model)

        # Convert messages to OpenAI format
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in request.messages
        ]

        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )

            return LLMResponse(
                content=response.choices[0].message.content,
                provider=LLMProvider.OPENAI,
                model=model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
                latency_ms=0,  # Will be set by caller
            )
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    async def check_health(self) -> bool:
        """Check OpenAI API health."""
        if not self.enabled:
            return False

        try:
            # Simple API call to check connectivity
            models = await self.client.models.list()
            return True
        except Exception as e:
            logger.error(f"OpenAI health check failed: {e}")
            return False


class AnthropicProvider(BaseLLMProvider):
    """Anthropic (Claude) provider implementation."""

    def __init__(self, config: Dict):
        super().__init__(config)
        api_key = os.getenv(config.get("api_key_env", "ANTHROPIC_API_KEY"))
        if not api_key:
            logger.warning("Anthropic API key not found, provider will be disabled")
            self.enabled = False
        else:
            self.client = AsyncAnthropic(
                api_key=api_key,
                base_url=self.base_url,
                timeout=self.timeout,
                max_retries=self.max_retries,
            )

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate response using Anthropic API."""
        if not self.enabled:
            raise ValueError("Anthropic provider is not enabled")

        model = self.get_model(request.model)

        # Convert messages to Anthropic format
        # Anthropic requires system message separate from messages array
        system_message = None
        messages = []

        for msg in request.messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                messages.append({"role": msg.role, "content": msg.content})

        try:
            response = await self.client.messages.create(
                model=model,
                system=system_message,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens or 1024,
            )

            return LLMResponse(
                content=response.content[0].text,
                provider=LLMProvider.ANTHROPIC,
                model=model,
                usage={
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
                },
                latency_ms=0,  # Will be set by caller
            )
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise

    async def check_health(self) -> bool:
        """Check Anthropic API health."""
        if not self.enabled:
            return False

        try:
            # Simple API call to check connectivity
            # Anthropic doesn't have a dedicated health endpoint, so we'll just return True if client exists
            return self.client is not None
        except Exception as e:
            logger.error(f"Anthropic health check failed: {e}")
            return False


class OllamaProvider(BaseLLMProvider):
    """Ollama provider implementation."""

    def __init__(self, config: Dict):
        super().__init__(config)
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
        )

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate response using Ollama API."""
        if not self.enabled:
            raise ValueError("Ollama provider is not enabled")

        model = self.get_model(request.model)

        # Convert messages to Ollama format
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in request.messages
        ]

        try:
            response = await self.client.post(
                "/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": request.temperature,
                        "num_predict": request.max_tokens or -1,
                    },
                },
            )
            response.raise_for_status()
            data = response.json()

            # Ollama doesn't always provide token counts
            prompt_tokens = data.get("prompt_eval_count", 0)
            completion_tokens = data.get("eval_count", 0)

            return LLMResponse(
                content=data["message"]["content"],
                provider=LLMProvider.OLLAMA,
                model=model,
                usage={
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                },
                latency_ms=0,  # Will be set by caller
            )
        except httpx.HTTPError as e:
            logger.error(f"Ollama API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            raise

    async def check_health(self) -> bool:
        """Check Ollama API health."""
        if not self.enabled:
            return False

        try:
            response = await self.client.get("/api/tags")
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


def create_provider(provider_type: str, config: Dict) -> BaseLLMProvider:
    """
    Factory function to create a provider instance.

    Args:
        provider_type: Type of provider (openai, anthropic, ollama)
        config: Provider configuration

    Returns:
        Provider instance

    Raises:
        ValueError: If provider type is unknown
    """
    providers = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "ollama": OllamaProvider,
    }

    provider_class = providers.get(provider_type.lower())
    if not provider_class:
        raise ValueError(f"Unknown provider type: {provider_type}")

    config["name"] = provider_type
    return provider_class(config)
