"""Main orchestration service."""

from typing import Dict, List, Any, Optional
from datetime import datetime

import sys
sys.path.append('../../..')
from shared.logging_config import get_logger
from shared.common_types import LLMProvider, LLMRequest, LLMMessage

from src.services.llm_client import LLMClient
from src.services.character_client import CharacterClient
from src.services.lore_client import LoreClient
from src.services.simulation_client import SimulationClient

logger = get_logger(__name__)


class OrchestratorService:
    """
    Main orchestration service for AI Manager.

    Coordinates all microservices to provide comprehensive responses
    to user queries, manage system state, and generate world events.
    """

    def __init__(
        self,
        config: Dict,
        llm_client: LLMClient,
        character_client: CharacterClient,
        lore_client: LoreClient,
        simulation_client: SimulationClient,
    ):
        self.config = config
        self.llm_client = llm_client
        self.character_client = character_client
        self.lore_client = lore_client
        self.simulation_client = simulation_client

        # Orchestration settings
        orch_config = config.get("orchestration", {})
        self.default_provider = orch_config.get("default_provider", "ollama")
        self.default_model = orch_config.get("default_model", "llama3.2:3b")
        self.temperature = orch_config.get("temperature", 0.7)
        self.max_tokens = orch_config.get("max_tokens", 2048)
        self.max_lore_results = orch_config.get("max_lore_results", 5)
        self.lore_score_threshold = orch_config.get("lore_score_threshold", 0.7)

        # Locale settings
        locale_config = config.get("locales", {})
        self.default_locale = locale_config.get("default", "en-US")
        self.supported_locales = locale_config.get("supported", ["en-US"])

    async def initialize(self):
        """Initialize orchestrator service."""
        logger.info("Initializing orchestrator service")

        # Test service connectivity
        health = await self.check_service_health()
        logger.info(f"Service health: {health}")

    async def process_query(
        self,
        query: str,
        locale: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        include_simulation: bool = True,
        include_lore: bool = True,
    ) -> Dict[str, Any]:
        """
        Process a user query with full orchestration.

        Steps:
        1. Validate locale
        2. Search lore database for relevant context (if enabled)
        3. Get simulation state (if enabled)
        4. Build comprehensive prompt with context
        5. Generate response using LLM
        6. Return response with metadata
        """
        locale = locale or self.default_locale
        context = context or {}

        logger.info(f"Processing query: {query[:50]}... (locale: {locale})")

        # Build context
        lore_context = []
        simulation_snapshot = None

        if include_lore:
            try:
                lore_results = await self.lore_client.search(
                    query=query,
                    limit=self.max_lore_results,
                    score_threshold=self.lore_score_threshold,
                )
                lore_context = lore_results.get("results", [])
                logger.info(f"Retrieved {len(lore_context)} lore results")
            except Exception as e:
                logger.warning(f"Failed to retrieve lore context: {e}")

        if include_simulation:
            try:
                simulation_snapshot = await self.simulation_client.get_status()
                logger.info(f"Retrieved simulation state: {simulation_snapshot.get('tick', 0)} ticks")
            except Exception as e:
                logger.warning(f"Failed to retrieve simulation state: {e}")

        # Build prompt with context
        system_prompt = self._build_system_prompt(locale)
        user_prompt = self._build_user_prompt(
            query=query,
            lore_context=lore_context,
            simulation_snapshot=simulation_snapshot,
            additional_context=context,
        )

        # Generate response
        llm_request = LLMRequest(
            messages=[
                LLMMessage(role="system", content=system_prompt),
                LLMMessage(role="user", content=user_prompt),
            ],
            provider=LLMProvider(self.default_provider),
            model=self.default_model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        llm_response = await self.llm_client.generate(llm_request)

        # Build response
        response = {
            "response": llm_response.get("content", ""),
            "sources": [item.get("text", "")[:100] for item in lore_context],
            "simulation_snapshot": simulation_snapshot,
            "metadata": {
                "locale": locale,
                "lore_items": len(lore_context),
                "model": llm_response.get("model"),
                "timestamp": datetime.utcnow().isoformat(),
            }
        }

        return response

    async def query_character(
        self,
        character_name: str,
        message: str,
        locale: Optional[str] = None,
        include_simulation: bool = True,
    ) -> Dict[str, Any]:
        """
        Query a character with simulation context.

        Combines character personality with current simulation state.
        """
        locale = locale or self.default_locale

        logger.info(f"Querying character {character_name}: {message[:50]}...")

        # Get simulation context if enabled
        simulation_context = []
        simulation_snapshot = None

        if include_simulation:
            try:
                simulation_snapshot = await self.simulation_client.get_status()
                # Get recent events
                events = await self.simulation_client.get_recent_events(limit=10)

                simulation_context = [
                    f"Current simulation tick: {simulation_snapshot.get('tick', 0)}",
                    f"Active agents: {simulation_snapshot.get('active_agents', 0)}",
                    f"Recent events: {len(events)} events",
                ]

                # Add event summaries
                for event in events[:5]:
                    simulation_context.append(
                        f"- {event.get('type')}: {event.get('description', 'No description')}"
                    )

            except Exception as e:
                logger.warning(f"Failed to retrieve simulation context: {e}")

        # Query character with context
        character_message = {
            "character_name": character_name,
            "message": message,
            "context": simulation_context,
        }

        try:
            character_response = await self.character_client.chat(
                character_name=character_name,
                message=message,
                context=simulation_context,
            )

            return {
                "response": character_response.get("response", ""),
                "sources": character_response.get("lore_sources", []),
                "simulation_snapshot": simulation_snapshot,
                "metadata": {
                    "character": character_name,
                    "locale": locale,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            }

        except Exception as e:
            logger.error(f"Failed to query character {character_name}: {e}")
            raise

    async def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status."""
        logger.info("Retrieving system status")

        # Check service health
        service_health = await self.check_service_health()

        # Get simulation status
        simulation_status = {}
        try:
            simulation_status = await self.simulation_client.get_status()
        except Exception as e:
            logger.warning(f"Failed to get simulation status: {e}")

        return {
            "status": "healthy" if all(
                s.get("healthy", False) for s in service_health.get("services", {}).values()
            ) else "degraded",
            "services": service_health.get("services", {}),
            "simulation": simulation_status,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def check_service_health(self) -> Dict[str, Any]:
        """Check health of all dependent services."""
        health = {
            "services": {
                "llm_proxy": await self._check_service("llm_proxy", self.llm_client.check_health),
                "lore_rag": await self._check_service("lore_rag", self.lore_client.check_health),
                "character_agent": await self._check_service("character_agent", self.character_client.check_health),
                "simulation_engine": await self._check_service("simulation_engine", self.simulation_client.check_health),
            }
        }

        return health

    async def _check_service(self, service_name: str, health_func) -> Dict[str, Any]:
        """Check health of a single service."""
        try:
            result = await health_func()
            return {
                "healthy": True,
                "status": result.get("status", "unknown"),
                "latency_ms": result.get("latency_ms", 0),
            }
        except Exception as e:
            logger.warning(f"Health check failed for {service_name}: {e}")
            return {
                "healthy": False,
                "error": str(e),
            }

    def _build_system_prompt(self, locale: str) -> str:
        """Build system prompt based on locale."""
        base_prompt = """You are the AI Manager for Ashiorid, a computational mythology engine.

You coordinate multiple AI services to provide comprehensive, contextually-aware responses about fictional worlds and their inhabitants.

You have access to:
- A lore database with detailed information about fictional universes
- A live simulation of 100+ autonomous agents
- AI characters with distinct personalities
- Real-time world events

Provide helpful, engaging responses that draw on all available context."""

        # Add locale-specific instructions
        locale_prompts = {
            "es-ES": "\n\nResponde en español de manera clara y natural.",
            "fr-FR": "\n\nRépondez en français de manière claire et naturelle.",
            "de-DE": "\n\nAntworten Sie auf Deutsch klar und natürlich.",
            "ja-JP": "\n\n日本語で明確かつ自然に回答してください。",
            "zh-CN": "\n\n请用中文清晰自然地回答。",
        }

        return base_prompt + locale_prompts.get(locale, "")

    def _build_user_prompt(
        self,
        query: str,
        lore_context: List[Dict],
        simulation_snapshot: Optional[Dict],
        additional_context: Dict[str, Any],
    ) -> str:
        """Build user prompt with all context."""
        prompt_parts = [f"User Query: {query}\n"]

        # Add lore context
        if lore_context:
            prompt_parts.append("\nRelevant Lore Context:")
            for i, item in enumerate(lore_context, 1):
                text = item.get("text", "")[:200]
                score = item.get("score", 0)
                prompt_parts.append(f"{i}. (relevance: {score:.2f}) {text}")

        # Add simulation context
        if simulation_snapshot:
            prompt_parts.append(f"\nCurrent Simulation State:")
            prompt_parts.append(f"- Tick: {simulation_snapshot.get('tick', 0)}")
            prompt_parts.append(f"- Active Agents: {simulation_snapshot.get('active_agents', 0)}/{simulation_snapshot.get('total_agents', 0)}")
            prompt_parts.append(f"- Ticks per second: {simulation_snapshot.get('ticks_per_second', 0)}")

        # Add additional context
        if additional_context:
            prompt_parts.append(f"\nAdditional Context: {additional_context}")

        return "\n".join(prompt_parts)
