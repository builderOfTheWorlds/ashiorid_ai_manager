# Testing Prompts for Ashiorid AI Manager Services

This directory contains comprehensive testing instructions for each microservice in the Ashiorid AI Manager system.

## Purpose

These prompts provide step-by-step instructions for:
- Manual testing of each service
- Integration testing scenarios
- Performance testing guidelines
- API endpoint validation
- Error handling verification

## Services

1. **LLM Proxy Service** (`01-llm-proxy-service.md`) - Manages LLM interactions
2. **Lore RAG Service** (`02-lore-rag-service.md`) - Handles lore retrieval and embeddings
3. **Character Agent Service** (`03-character-agent-service.md`) - Manages character AI agents
4. **Simulation Engine** (`04-simulation-engine.md`) - Orchestrates game world simulation
5. **AI Manager Service** (`05-ai-manager-service.md`) - Coordinates all AI services

## How to Use

1. Start your services using `tilt up`
2. Open the relevant testing prompt file for the service you want to test
3. Follow the step-by-step instructions
4. Record results and any issues found

## Quick Health Check

```bash
# Check all services are running
kubectl get pods -n ashiorid

# Test all health endpoints
curl http://localhost:8001/health  # LLM Proxy
curl http://localhost:8002/health  # Lore RAG
curl http://localhost:8003/health  # Character Agent
curl http://localhost:8004/health  # Simulation Engine
curl http://localhost:8005/health  # AI Manager
```

## Testing Order

For comprehensive system testing, test in this order:
1. Infrastructure services (postgres, redis, qdrant)
2. LLM Proxy Service (dependency for others)
3. Lore RAG Service (provides context)
4. Character Agent Service (uses LLM and Lore)
5. Simulation Engine (manages game state)
6. AI Manager Service (orchestrates everything)

## Environment

- **Development**: localhost ports 8001-8005
- **Tilt UI**: http://localhost:10350
- **Grafana**: http://localhost:3000
- **Prometheus**: http://localhost:9090
