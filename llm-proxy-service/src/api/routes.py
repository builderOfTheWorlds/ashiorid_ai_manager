"""
API routes for LLM Proxy Service.
"""

import time
from typing import List

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse

import sys
sys.path.append('../..')
from shared.common_types import LLMRequest, LLMResponse, LLMProvider
from shared.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()
admin_router = APIRouter()


def get_proxy_service(request: Request):
    """Dependency to get proxy service from app state."""
    return request.app.state.app_state.proxy_service


def get_metrics(request: Request):
    """Dependency to get metrics from app state."""
    return request.app.state.metrics


@router.post("/chat/completions", response_model=LLMResponse)
async def chat_completions(
    llm_request: LLMRequest,
    request: Request,
    proxy_service = Depends(get_proxy_service),
    metrics = Depends(get_metrics),
):
    """
    OpenAI-compatible chat completions endpoint.

    Accepts LLM requests and routes them to the appropriate provider.
    Supports caching, batching, and cost tracking.
    """
    start_time = time.time()

    try:
        # Log request
        logger.info(
            f"LLM request: provider={llm_request.provider}, "
            f"model={llm_request.model}, messages={len(llm_request.messages)}"
        )

        # Process request through proxy service
        response = await proxy_service.process_request(llm_request)

        # Update metrics
        latency = time.time() - start_time
        response.latency_ms = latency * 1000

        metrics["request_count"].labels(
            provider=response.provider,
            model=response.model,
            status="success",
        ).inc()

        metrics["request_latency"].labels(
            provider=response.provider,
            model=response.model,
        ).observe(latency)

        metrics["token_usage"].labels(
            provider=response.provider,
            model=response.model,
            type="prompt",
        ).inc(response.usage.get("prompt_tokens", 0))

        metrics["token_usage"].labels(
            provider=response.provider,
            model=response.model,
            type="completion",
        ).inc(response.usage.get("completion_tokens", 0))

        logger.info(
            f"LLM response: provider={response.provider}, model={response.model}, "
            f"tokens={response.usage.get('total_tokens', 0)}, latency_ms={response.latency_ms:.2f}"
        )

        return response

    except Exception as e:
        # Update error metrics
        metrics["request_count"].labels(
            provider=llm_request.provider,
            model=llm_request.model or "unknown",
            status="error",
        ).inc()

        logger.error(f"LLM request failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.get("/providers")
async def list_providers(proxy_service = Depends(get_proxy_service)):
    """
    List available LLM providers and their models.
    """
    try:
        providers_info = await proxy_service.get_providers_info()
        return {
            "providers": providers_info,
            "default_provider": proxy_service.config.get("default_provider", "ollama"),
        }
    except Exception as e:
        logger.error(f"Failed to get providers info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.get("/providers/{provider}/models")
async def list_provider_models(
    provider: str,
    proxy_service = Depends(get_proxy_service),
):
    """
    List available models for a specific provider.
    """
    try:
        models = await proxy_service.get_provider_models(provider)
        return {
            "provider": provider,
            "models": models,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get models for provider {provider}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.get("/stats")
async def get_stats(proxy_service = Depends(get_proxy_service)):
    """
    Get service statistics including cache hit rate, cost tracking, etc.
    """
    try:
        stats = await proxy_service.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.post("/cache/clear")
async def clear_cache(proxy_service = Depends(get_proxy_service)):
    """
    Clear the response cache.
    """
    try:
        await proxy_service.clear_cache()
        return {"status": "success", "message": "Cache cleared"}
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.get("/cost/summary")
async def cost_summary(proxy_service = Depends(get_proxy_service)):
    """
    Get cost summary across all providers.
    """
    try:
        cost_data = await proxy_service.get_cost_summary()
        return cost_data
    except Exception as e:
        logger.error(f"Failed to get cost summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))
