"""World event generator for creating emergent narrative events."""

import asyncio
import random
from typing import Dict, List, Any, Optional
from datetime import datetime
import redis.asyncio as aioredis
import json

import sys
sys.path.append('../../..')
from shared.logging_config import get_logger
from shared.common_types import LLMRequest, LLMMessage, LLMProvider

from src.services.simulation_client import SimulationClient
from src.services.llm_client import LLMClient

logger = get_logger(__name__)


class WorldEventGenerator:
    """
    Generates world events based on simulation state.

    Monitors the simulation and periodically generates narrative events
    that affect multiple agents or the world as a whole.
    """

    def __init__(
        self,
        config: Dict,
        simulation_client: SimulationClient,
        llm_client: LLMClient,
    ):
        self.config = config
        self.simulation_client = simulation_client
        self.llm_client = llm_client

        # Event generation settings
        event_config = config.get("world_events", {})
        self.enabled = event_config.get("enabled", True)
        self.check_interval = event_config.get("check_interval", 60)
        self.min_agents_for_event = event_config.get("min_agents_for_event", 10)
        self.event_probability = event_config.get("event_probability", 0.1)
        self.event_types = event_config.get("event_types", [
            "natural_disaster",
            "resource_discovery",
            "faction_conflict",
            "mysterious_phenomenon",
            "technological_breakthrough",
        ])

        # Redis for event storage
        redis_config = config.get("redis", {})
        self.redis_url = redis_config.get("url", "redis://redis:6379/0")
        self.event_channel = redis_config.get("world_events_channel", "world_events")

        self.redis_client = None
        self.is_running = False
        self.generator_task = None
        self.recent_events = []

    async def initialize(self):
        """Initialize event generator."""
        logger.info("Initializing world event generator")

        # Connect to Redis
        self.redis_client = await aioredis.from_url(self.redis_url)

        logger.info(f"Event generator initialized (enabled: {self.enabled})")

    def start(self):
        """Start event generation loop."""
        if not self.enabled:
            logger.info("Event generator disabled in config")
            return

        if self.is_running:
            logger.warning("Event generator already running")
            return

        logger.info("Starting world event generator")
        self.is_running = True
        self.generator_task = asyncio.create_task(self._event_loop())

    async def stop(self):
        """Stop event generation loop."""
        if not self.is_running:
            return

        logger.info("Stopping world event generator")
        self.is_running = False

        if self.generator_task:
            self.generator_task.cancel()
            try:
                await self.generator_task
            except asyncio.CancelledError:
                pass

        if self.redis_client:
            await self.redis_client.close()

    async def _event_loop(self):
        """Main event generation loop."""
        try:
            while self.is_running:
                await asyncio.sleep(self.check_interval)

                try:
                    await self._check_and_generate_event()
                except Exception as e:
                    logger.error(f"Error in event generation: {e}", exc_info=True)

        except asyncio.CancelledError:
            logger.info("Event generation loop cancelled")

    async def _check_and_generate_event(self):
        """Check if event should be generated and generate it."""
        # Get simulation status
        try:
            sim_status = await self.simulation_client.get_status()
            active_agents = sim_status.get("active_agents", 0)

            # Check if enough agents are active
            if active_agents < self.min_agents_for_event:
                logger.debug(f"Not enough active agents for event: {active_agents}")
                return

            # Random chance to generate event
            if random.random() > self.event_probability:
                return

            # Generate event
            event_type = random.choice(self.event_types)
            await self.generate_event(event_type=event_type)

        except Exception as e:
            logger.error(f"Failed to check/generate event: {e}")

    async def generate_event(
        self,
        event_type: str,
        description: Optional[str] = None,
        agent_ids: Optional[List[str]] = None,
        location: Optional[tuple[int, int]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a world event.

        If description is not provided, uses LLM to generate narrative description.
        """
        logger.info(f"Generating world event: {event_type}")

        # Get simulation context
        sim_status = await self.simulation_client.get_status()
        agents = await self.simulation_client.get_agents(limit=20)

        # Generate description if not provided
        if not description:
            description = await self._generate_event_description(
                event_type=event_type,
                sim_status=sim_status,
                sample_agents=agents,
            )

        # Create event
        event = {
            "type": event_type,
            "description": description,
            "agent_ids": agent_ids or [],
            "location": location,
            "timestamp": datetime.utcnow().isoformat(),
            "simulation_tick": sim_status.get("tick", 0),
        }

        # Store in recent events
        self.recent_events.insert(0, event)
        self.recent_events = self.recent_events[:100]  # Keep last 100 events

        # Publish to Redis
        await self._publish_event(event)

        logger.info(f"World event generated: {event_type} - {description[:100]}")

        return event

    async def _generate_event_description(
        self,
        event_type: str,
        sim_status: Dict[str, Any],
        sample_agents: List[Dict[str, Any]],
    ) -> str:
        """Generate narrative description for event using LLM."""
        system_prompt = """You are a narrative event generator for a simulation world.
Generate vivid, engaging descriptions of world events that feel natural and immersive.
Keep descriptions concise (2-3 sentences) but evocative."""

        user_prompt = f"""Generate a narrative description for this event:

Event Type: {event_type}

Current World State:
- Simulation tick: {sim_status.get('tick', 0)}
- Active agents: {sim_status.get('active_agents', 0)}
- Total agents: {sim_status.get('total_agents', 0)}

Sample agent states:
{self._format_agents(sample_agents[:5])}

Generate a compelling 2-3 sentence description of this {event_type} event."""

        try:
            llm_request = LLMRequest(
                messages=[
                    LLMMessage(role="system", content=system_prompt),
                    LLMMessage(role="user", content=user_prompt),
                ],
                provider=LLMProvider("ollama"),
                model="llama3.2:3b",
                temperature=0.8,
                max_tokens=150,
            )

            response = await self.llm_client.generate(llm_request)
            return response.get("content", f"A {event_type} has occurred in the world.")

        except Exception as e:
            logger.error(f"Failed to generate event description: {e}")
            return f"A {event_type} has occurred in the world."

    def _format_agents(self, agents: List[Dict[str, Any]]) -> str:
        """Format agent list for prompt."""
        lines = []
        for agent in agents:
            attrs = agent.get("attributes", {})
            lines.append(
                f"- {agent.get('name', 'Unknown')} at {agent.get('position', (0, 0))}: "
                f"health={attrs.get('health', 0):.2f}, hunger={attrs.get('hunger', 0):.2f}"
            )
        return "\n".join(lines)

    async def _publish_event(self, event: Dict[str, Any]):
        """Publish event to Redis."""
        try:
            await self.redis_client.publish(
                self.event_channel,
                json.dumps(event),
            )
        except Exception as e:
            logger.error(f"Failed to publish event to Redis: {e}")

    async def get_recent_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent world events."""
        return self.recent_events[:limit]
