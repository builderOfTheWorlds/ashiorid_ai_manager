"""Unit tests for orchestrator service."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.services.orchestrator import OrchestratorService


class TestOrchestratorService:
    """Unit tests for OrchestratorService."""

    @pytest.fixture
    def mock_clients(self):
        """Create mock service clients."""
        return {
            "llm_client": Mock(
                generate=AsyncMock(return_value={"content": "Test response", "model": "test"}),
                check_health=AsyncMock(return_value={"status": "healthy"}),
            ),
            "character_client": Mock(
                chat=AsyncMock(return_value={"response": "Character response"}),
                check_health=AsyncMock(return_value={"status": "healthy"}),
            ),
            "lore_client": Mock(
                search=AsyncMock(return_value={"results": []}),
                check_health=AsyncMock(return_value={"status": "healthy"}),
            ),
            "simulation_client": Mock(
                get_status=AsyncMock(return_value={"tick": 100, "active_agents": 50}),
                check_health=AsyncMock(return_value={"status": "healthy"}),
            ),
        }

    @pytest.fixture
    def orchestrator(self, mock_clients):
        """Create orchestrator service with mock dependencies."""
        config = {
            "orchestration": {
                "default_provider": "ollama",
                "default_model": "test-model",
                "temperature": 0.7,
                "max_tokens": 2048,
                "max_lore_results": 5,
                "lore_score_threshold": 0.7,
            },
            "locales": {
                "default": "en-US",
                "supported": ["en-US", "es-ES"],
            },
        }

        return OrchestratorService(
            config=config,
            llm_client=mock_clients["llm_client"],
            character_client=mock_clients["character_client"],
            lore_client=mock_clients["lore_client"],
            simulation_client=mock_clients["simulation_client"],
        )

    @pytest.mark.asyncio
    async def test_initialize(self, orchestrator):
        """Test service initialization."""
        await orchestrator.initialize()
        assert orchestrator.default_provider == "ollama"
        assert orchestrator.default_model == "test-model"

    @pytest.mark.asyncio
    async def test_process_query_basic(self, orchestrator, mock_clients):
        """Test basic query processing."""
        response = await orchestrator.process_query(
            query="Test query",
            include_simulation=False,
            include_lore=False,
        )

        assert "response" in response
        assert response["response"] == "Test response"
        assert "metadata" in response
        assert mock_clients["llm_client"].generate.called

    @pytest.mark.asyncio
    async def test_process_query_with_lore(self, orchestrator, mock_clients):
        """Test query processing with lore context."""
        mock_clients["lore_client"].search.return_value = {
            "results": [
                {"text": "Lore item 1", "score": 0.9},
                {"text": "Lore item 2", "score": 0.8},
            ]
        }

        response = await orchestrator.process_query(
            query="Test query",
            include_lore=True,
            include_simulation=False,
        )

        assert mock_clients["lore_client"].search.called
        assert len(response["sources"]) == 2

    @pytest.mark.asyncio
    async def test_process_query_with_simulation(self, orchestrator, mock_clients):
        """Test query processing with simulation context."""
        response = await orchestrator.process_query(
            query="Test query",
            include_simulation=True,
            include_lore=False,
        )

        assert mock_clients["simulation_client"].get_status.called
        assert response["simulation_snapshot"]["tick"] == 100

    @pytest.mark.asyncio
    async def test_query_character(self, orchestrator, mock_clients):
        """Test character querying."""
        response = await orchestrator.query_character(
            character_name="test-character",
            message="Hello",
            include_simulation=False,
        )

        assert mock_clients["character_client"].chat.called
        assert response["response"] == "Character response"

    @pytest.mark.asyncio
    async def test_check_service_health(self, orchestrator):
        """Test service health checking."""
        health = await orchestrator.check_service_health()

        assert "services" in health
        assert all(
            service in health["services"]
            for service in ["llm_proxy", "lore_rag", "character_agent", "simulation_engine"]
        )

    @pytest.mark.asyncio
    async def test_locale_support(self, orchestrator):
        """Test locale-based prompt building."""
        system_prompt_en = orchestrator._build_system_prompt("en-US")
        system_prompt_es = orchestrator._build_system_prompt("es-ES")

        assert "AI Manager" in system_prompt_en
        assert "español" in system_prompt_es

    def test_build_user_prompt(self, orchestrator):
        """Test user prompt building."""
        prompt = orchestrator._build_user_prompt(
            query="Test query",
            lore_context=[{"text": "Lore item", "score": 0.9}],
            simulation_snapshot={"tick": 100, "active_agents": 50},
            additional_context={"key": "value"},
        )

        assert "Test query" in prompt
        assert "Lore item" in prompt
        assert "100" in prompt  # tick count
        assert "50" in prompt   # active agents
