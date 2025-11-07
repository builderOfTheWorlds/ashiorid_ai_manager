"""Core simulation service."""

import asyncio
import uuid
import random
import time
from typing import Dict, List
from sqlalchemy import select, func, delete

import sys
sys.path.append('../..')
from shared.common_types import SimulationAgent, AgentAttributes, AgentState, SimulationState
from shared.logging_config import get_logger

from src.db.models import Agent, SimulationEvent
from src.db.database import DatabaseManager

logger = get_logger(__name__)

class SimulationService:
    """Main simulation service."""

    def __init__(self, config: Dict, db_manager: DatabaseManager):
        self.config = config
        self.db_manager = db_manager

        sim_config = config.get("simulation", {})
        self.grid_size = sim_config.get("grid_size", 100)
        self.tick_rate = sim_config.get("tick_rate", 10)
        self.max_agents = sim_config.get("max_agents", 1000)

        self.hunger_decay = sim_config.get("hunger_decay", 0.001)
        self.thirst_decay = sim_config.get("thirst_decay", 0.002)
        self.energy_decay = sim_config.get("energy_decay", 0.0015)

        self.is_running = False
        self.tick_count = 0
        self.simulation_task = None
        self.agents_cache = {}

    async def initialize(self):
        """Initialize simulation service."""
        logger.info("Initializing simulation service")

    async def start(self, num_agents: int = 100):
        """Start the simulation."""
        if self.is_running:
            raise ValueError("Simulation already running")

        logger.info(f"Starting simulation with {num_agents} agents")

        # Clear existing agents
        async with self.db_manager.get_session() as session:
            await session.execute(delete(Agent))
            await session.commit()

        # Spawn initial agents
        for _ in range(min(num_agents, self.max_agents)):
            await self._spawn_agent()

        self.is_running = True
        self.tick_count = 0
        self.simulation_task = asyncio.create_task(self._run_simulation_loop())

    async def stop(self):
        """Stop the simulation."""
        if not self.is_running:
            return

        logger.info("Stopping simulation")
        self.is_running = False

        if self.simulation_task:
            self.simulation_task.cancel()
            try:
                await self.simulation_task
            except asyncio.CancelledError:
                pass

    async def _run_simulation_loop(self):
        """Main simulation loop."""
        try:
            while self.is_running:
                tick_start = time.time()

                await self._process_tick()

                # Sleep to maintain tick rate
                tick_duration = time.time() - tick_start
                sleep_time = max(0, (1.0 / self.tick_rate) - tick_duration)
                await asyncio.sleep(sleep_time)

        except asyncio.CancelledError:
            logger.info("Simulation loop cancelled")
        except Exception as e:
            logger.error(f"Simulation loop error: {e}", exc_info=True)
            self.is_running = False

    async def _process_tick(self):
        """Process a single simulation tick."""
        self.tick_count += 1

        async with self.db_manager.get_session() as session:
            # Get all active agents
            result = await session.execute(
                select(Agent).where(Agent.state == "active")
            )
            agents = result.scalars().all()

            # Update each agent
            for agent in agents:
                await self._update_agent(agent, session)

            await session.commit()

        if self.tick_count % 100 == 0:
            logger.debug(f"Tick {self.tick_count}: {len(agents)} active agents")

    async def _update_agent(self, agent: Agent, session):
        """Update a single agent."""
        # Update needs
        agent.hunger = min(1.0, agent.hunger + self.hunger_decay)
        agent.thirst = min(1.0, agent.thirst + self.thirst_decay)
        agent.energy = max(0.0, agent.energy - self.energy_decay)
        agent.age += 1

        # Health degradation from unmet needs
        if agent.hunger > 0.7:
            agent.health = max(0.0, agent.health - 0.005)
        if agent.thirst > 0.8:
            agent.health = max(0.0, agent.health - 0.01)

        # Check for death
        if agent.health <= 0.1 or agent.age > 1000:
            agent.state = "dead"
            return

        # Simple rule-based behavior
        action = await self._decide_action(agent)
        await self._execute_action(agent, action, session)

    async def _decide_action(self, agent: Agent) -> str:
        """Decide agent's next action."""
        # Critical needs take priority
        if agent.thirst > 0.8:
            return "seek_water"
        if agent.hunger > 0.7:
            return "seek_food"
        if agent.energy < 0.3:
            return "rest"

        # Random movement
        return random.choice(["move", "idle"])

    async def _execute_action(self, agent: Agent, action: str, session):
        """Execute an agent action."""
        if action == "seek_food":
            agent.hunger = max(0.0, agent.hunger - 0.3)
        elif action == "seek_water":
            agent.thirst = max(0.0, agent.thirst - 0.4)
        elif action == "rest":
            agent.energy = min(1.0, agent.energy + 0.5)
        elif action == "move":
            # Random movement
            agent.position_x = max(0, min(self.grid_size - 1, agent.position_x + random.choice([-1, 0, 1])))
            agent.position_y = max(0, min(self.grid_size - 1, agent.position_y + random.choice([-1, 0, 1])))
            agent.energy = max(0.0, agent.energy - 0.01)

    async def _spawn_agent(self):
        """Spawn a new agent."""
        agent_id = str(uuid.uuid4())

        async with self.db_manager.get_session() as session:
            agent = Agent(
                id=agent_id,
                name=f"Agent-{agent_id[:8]}",
                state="active",
                position_x=random.randint(0, self.grid_size - 1),
                position_y=random.randint(0, self.grid_size - 1),
                hunger=random.uniform(0.3, 0.7),
                thirst=random.uniform(0.3, 0.7),
                energy=random.uniform(0.7, 1.0),
                health=1.0,
                age=0,
                inventory=[],
                metadata={},
            )
            session.add(agent)
            await session.commit()

    async def get_status(self) -> SimulationState:
        """Get current simulation status."""
        async with self.db_manager.get_session() as session:
            total = await session.execute(select(func.count(Agent.id)))
            active = await session.execute(
                select(func.count(Agent.id)).where(Agent.state == "active")
            )

            return SimulationState(
                tick=self.tick_count,
                active_agents=active.scalar(),
                total_agents=total.scalar(),
                ticks_per_second=self.tick_rate if self.is_running else 0,
                world_events=[],
            )

    async def get_agents(self, limit: int = 100, offset: int = 0) -> List[SimulationAgent]:
        """Get all agents."""
        async with self.db_manager.get_session() as session:
            result = await session.execute(
                select(Agent).limit(limit).offset(offset)
            )
            agents = result.scalars().all()

            return [self._model_to_agent(agent) for agent in agents]

    async def get_agent(self, agent_id: str) -> SimulationAgent:
        """Get a specific agent."""
        async with self.db_manager.get_session() as session:
            result = await session.execute(
                select(Agent).where(Agent.id == agent_id)
            )
            agent = result.scalar_one_or_none()
            return self._model_to_agent(agent) if agent else None

    async def manual_action(self, agent_id: str, action: str) -> Dict:
        """Manually trigger agent action."""
        async with self.db_manager.get_session() as session:
            result = await session.execute(
                select(Agent).where(Agent.id == agent_id)
            )
            agent = result.scalar_one_or_none()

            if not agent:
                raise ValueError(f"Agent {agent_id} not found")

            await self._execute_action(agent, action, session)
            await session.commit()

            return {"status": "success", "action": action}

    async def get_recent_events(self, limit: int = 50) -> List[Dict]:
        """Get recent events."""
        async with self.db_manager.get_session() as session:
            result = await session.execute(
                select(SimulationEvent).order_by(SimulationEvent.created_at.desc()).limit(limit)
            )
            events = result.scalars().all()

            return [
                {
                    "type": e.event_type,
                    "description": e.description,
                    "agent_ids": e.agent_ids or [],
                    "location": (e.location_x, e.location_y) if e.location_x else None,
                }
                for e in events
            ]

    def _model_to_agent(self, agent: Agent) -> SimulationAgent:
        """Convert database model to Pydantic model."""
        return SimulationAgent(
            id=agent.id,
            name=agent.name,
            state=AgentState(agent.state),
            position=(agent.position_x, agent.position_y),
            attributes=AgentAttributes(
                hunger=agent.hunger,
                thirst=agent.thirst,
                energy=agent.energy,
                health=agent.health,
            ),
            inventory=agent.inventory or [],
            metadata=agent.metadata or {},
        )
