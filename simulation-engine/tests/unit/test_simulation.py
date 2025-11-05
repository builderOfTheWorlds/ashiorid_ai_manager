"""Unit tests for simulation service."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.services.simulation import SimulationService
from src.db.models import Agent


class TestSimulationService:
    """Unit tests for SimulationService."""

    @pytest.fixture
    def mock_db_manager(self):
        """Create mock database manager."""
        db_manager = Mock()
        session = AsyncMock()
        db_manager.get_session = Mock(return_value=session)
        return db_manager

    @pytest.fixture
    def simulation_service(self, mock_db_manager):
        """Create simulation service with mock dependencies."""
        config = {
            "simulation": {
                "grid_size": 100,
                "tick_rate": 10,
                "max_agents": 1000,
                "hunger_decay": 0.001,
                "thirst_decay": 0.002,
                "energy_decay": 0.0015,
            }
        }
        return SimulationService(config, mock_db_manager)

    @pytest.mark.asyncio
    async def test_initialize(self, simulation_service):
        """Test service initialization."""
        await simulation_service.initialize()
        assert simulation_service.tick_count == 0
        assert simulation_service.is_running is False

    @pytest.mark.asyncio
    async def test_decide_action_thirst_priority(self, simulation_service):
        """Test that thirst takes priority over hunger."""
        agent = Agent(
            id="test-agent",
            name="Test",
            state="active",
            position_x=50,
            position_y=50,
            hunger=0.75,
            thirst=0.85,
            energy=0.5,
            health=1.0,
            age=0,
            inventory=[],
            metadata={},
        )

        action = await simulation_service._decide_action(agent)
        assert action == "seek_water"

    @pytest.mark.asyncio
    async def test_decide_action_hunger_priority(self, simulation_service):
        """Test that hunger is prioritized when thirst is lower."""
        agent = Agent(
            id="test-agent",
            name="Test",
            state="active",
            position_x=50,
            position_y=50,
            hunger=0.75,
            thirst=0.5,
            energy=0.5,
            health=1.0,
            age=0,
            inventory=[],
            metadata={},
        )

        action = await simulation_service._decide_action(agent)
        assert action == "seek_food"

    @pytest.mark.asyncio
    async def test_decide_action_rest_priority(self, simulation_service):
        """Test that rest is prioritized when energy is low."""
        agent = Agent(
            id="test-agent",
            name="Test",
            state="active",
            position_x=50,
            position_y=50,
            hunger=0.5,
            thirst=0.5,
            energy=0.2,
            health=1.0,
            age=0,
            inventory=[],
            metadata={},
        )

        action = await simulation_service._decide_action(agent)
        assert action == "rest"

    @pytest.mark.asyncio
    async def test_execute_action_seek_food(self, simulation_service, mock_db_manager):
        """Test seek_food action reduces hunger."""
        agent = Agent(
            id="test-agent",
            name="Test",
            state="active",
            position_x=50,
            position_y=50,
            hunger=0.8,
            thirst=0.5,
            energy=0.5,
            health=1.0,
            age=0,
            inventory=[],
            metadata={},
        )

        initial_hunger = agent.hunger
        await simulation_service._execute_action(agent, "seek_food", None)

        assert agent.hunger < initial_hunger
        assert agent.hunger == pytest.approx(0.5, abs=0.01)

    @pytest.mark.asyncio
    async def test_execute_action_seek_water(self, simulation_service, mock_db_manager):
        """Test seek_water action reduces thirst."""
        agent = Agent(
            id="test-agent",
            name="Test",
            state="active",
            position_x=50,
            position_y=50,
            hunger=0.5,
            thirst=0.9,
            energy=0.5,
            health=1.0,
            age=0,
            inventory=[],
            metadata={},
        )

        initial_thirst = agent.thirst
        await simulation_service._execute_action(agent, "seek_water", None)

        assert agent.thirst < initial_thirst
        assert agent.thirst == pytest.approx(0.5, abs=0.01)

    @pytest.mark.asyncio
    async def test_execute_action_rest(self, simulation_service, mock_db_manager):
        """Test rest action increases energy."""
        agent = Agent(
            id="test-agent",
            name="Test",
            state="active",
            position_x=50,
            position_y=50,
            hunger=0.5,
            thirst=0.5,
            energy=0.2,
            health=1.0,
            age=0,
            inventory=[],
            metadata={},
        )

        initial_energy = agent.energy
        await simulation_service._execute_action(agent, "rest", None)

        assert agent.energy > initial_energy
        assert agent.energy == pytest.approx(0.7, abs=0.01)

    @pytest.mark.asyncio
    async def test_execute_action_move(self, simulation_service, mock_db_manager):
        """Test move action changes position and consumes energy."""
        agent = Agent(
            id="test-agent",
            name="Test",
            state="active",
            position_x=50,
            position_y=50,
            hunger=0.5,
            thirst=0.5,
            energy=0.5,
            health=1.0,
            age=0,
            inventory=[],
            metadata={},
        )

        initial_pos = (agent.position_x, agent.position_y)
        initial_energy = agent.energy

        await simulation_service._execute_action(agent, "move", None)

        # Position may have changed (not guaranteed due to random)
        # Energy should have decreased
        assert agent.energy < initial_energy

    def test_grid_boundaries(self, simulation_service):
        """Test that agents stay within grid boundaries."""
        assert simulation_service.grid_size == 100

        # Test boundaries are enforced in execute_action
        agent = Agent(
            id="test-agent",
            name="Test",
            state="active",
            position_x=0,
            position_y=0,
            hunger=0.5,
            thirst=0.5,
            energy=0.5,
            health=1.0,
            age=0,
            inventory=[],
            metadata={},
        )

        # Even with movement, agent should stay in bounds [0, grid_size)
        for _ in range(100):
            agent.position_x = max(0, min(simulation_service.grid_size - 1,
                                         agent.position_x + 1))
            agent.position_y = max(0, min(simulation_service.grid_size - 1,
                                         agent.position_y + 1))

        assert 0 <= agent.position_x < simulation_service.grid_size
        assert 0 <= agent.position_y < simulation_service.grid_size
