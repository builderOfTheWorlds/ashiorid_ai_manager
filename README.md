# 🌍 Ashiorid AI Manager

> A computational mythology engine - an AI-powered world-building system that combines lore, character agents, and world simulation.

[![CI/CD](https://github.com/builderOfTheWorlds/ashiorid_ai_manager/workflows/test/badge.svg)](https://github.com/builderOfTheWorlds/ashiorid_ai_manager/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 📖 Project Vision

Ashiorid AI Manager is a microservices-based system that combines:

- **Lore Foundation**: RAG (Retrieval Augmented Generation) system with knowledge from fictional universes (LOTR, Dune, Halo, Harry Potter, 300, Gears of War)
- **Character Agents**: AI agents with distinct personalities inspired by these universes, serving as collaborative world-building assistants
- **World Simulation**: Conway's Game of Life-inspired simulation with 100+ lightweight AI agents
- **AI Manager**: Master orchestrator coordinating agent activities, managing locale-based processing, and delegating decisions

## 🏗️ Architecture

### Microservices

1. **llm-proxy-service** - LLM request management, batching, cost optimization
2. **lore-rag-service** - Vector database and semantic search for fictional universe knowledge
3. **character-agent-service** - AI character agents for collaborative world-building
4. **simulation-engine** - Lightweight agent simulation (100+ agents)
5. **ai-manager-service** - Master orchestrator coordinating all services
6. **api-gateway** - External-facing API via Traefik

### Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Orchestration** | Kubernetes (K3s) | Container orchestration |
| **Vector Database** | Qdrant | Semantic search & embeddings |
| **Relational Database** | PostgreSQL | Agent state & world history |
| **Cache & Pub/Sub** | Redis | Real-time events & caching |
| **API Gateway** | Traefik | Ingress & routing |
| **LLM Providers** | OpenAI, Anthropic, Ollama | Cloud + local models |
| **API Framework** | FastAPI | Async Python APIs |
| **Monitoring** | Prometheus + Grafana | Metrics & dashboards |
| **Dev Workflow** | Tilt | Hot-reload development |

## 🚀 Quick Start

### Prerequisites

- **WSL2** (Windows Subsystem for Linux) or Linux
- **Docker** 20.10+
- **K3s** (installed via setup script)
- **Python** 3.11+
- **Ollama** (for local LLM models)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/builderOfTheWorlds/ashiorid_ai_manager.git
cd ashiorid_ai_manager
```

2. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

3. **Run bootstrap script**
```bash
chmod +x scripts/bootstrap.sh
./scripts/bootstrap.sh
```

This will:
- Install K3s
- Set up Ollama with required models
- Deploy infrastructure (PostgreSQL, Redis, Qdrant, Prometheus, Grafana, Traefik)
- Build and deploy all microservices

4. **Start development environment with Tilt**
```bash
tilt up
```

Visit http://localhost:10350 to see the Tilt dashboard with live logs and service status.

## 📚 Documentation

- [Architecture Overview](docs/architecture.md) - System design and service interactions
- [Development Guide](docs/development-guide.md) - How to contribute and develop locally
- [Deployment Guide](docs/deployment-guide.md) - Kubernetes deployment instructions
- [API Specifications](docs/api-specs.md) - API documentation and examples

## 🛠️ Development

### Local Development with Tilt

Tilt provides hot-reload for all services:

```bash
# Start all services
tilt up

# View logs
tilt logs llm-proxy-service

# Restart a service
tilt trigger llm-proxy-service

# Stop all services
tilt down
```

### Running Tests

```bash
# Run all tests
./scripts/run_tests.sh

# Run tests for specific service
cd llm-proxy-service
pytest tests/

# Run with coverage
pytest --cov=src tests/
```

### CLI Dashboard

Monitor all services in real-time:

```bash
python cli-dashboard/dashboard.py
```

## 📁 Project Structure

```
ashiorid_ai_manager/
├── .github/workflows/       # GitHub Actions CI/CD
├── docs/                    # Documentation
├── k8s/                     # Kubernetes manifests
│   ├── base/               # Infrastructure (PostgreSQL, Redis, Qdrant)
│   ├── monitoring/         # Prometheus + Grafana
│   └── apps/               # Service-specific manifests
├── scripts/                 # Setup and utility scripts
├── shared/                  # Shared Python utilities
├── llm-proxy-service/      # LLM proxy microservice
├── lore-rag-service/       # RAG service for lore
├── character-agent-service/ # Character agents
├── simulation-engine/      # Agent simulation
├── ai-manager-service/     # Master orchestrator
├── cli-dashboard/          # Monitoring dashboard
├── Tiltfile                # Tilt configuration
├── docker-compose.yml      # Local dev without K8s
└── README.md               # This file
```

## 🎯 Roadmap

### Phase 1: Foundation ✅
- [x] Repository structure
- [x] Infrastructure setup (K3s, PostgreSQL, Redis, Qdrant)
- [x] Shared utilities
- [x] CI/CD pipelines

### Phase 2: Core Services (Current)
- [ ] llm-proxy-service
- [ ] lore-rag-service
- [ ] Ingest initial lore
- [ ] CLI dashboard v1

### Phase 3: Agent Systems
- [ ] character-agent-service
- [ ] First character agents
- [ ] simulation-engine
- [ ] 100-agent simulation

### Phase 4: Orchestration
- [ ] ai-manager-service
- [ ] Locale-based processing
- [ ] Traefik routing
- [ ] End-to-end testing

### Phase 5: Polish & Scale
- [ ] Performance tuning
- [ ] Comprehensive documentation
- [ ] Optional: Kafka event sourcing
- [ ] Web interface

## 🧪 Success Criteria (POC)

The POC is successful when:

- ✅ All 6 microservices deployed to K3s
- ✅ Can query lore database: "What would Gandalf do in this situation?"
- ✅ Character agents respond with distinct personalities
- ✅ 100-agent simulation runs at 10+ ticks/sec
- ✅ AI manager coordinates locale-based processing
- ✅ CLI dashboard shows real-time metrics
- ✅ GitHub Actions CI/CD pipeline working
- ✅ Can collaborate with character agents to build Ashiorid lore

## 🤝 Contributing

We welcome contributions! Please see [Development Guide](docs/development-guide.md) for details.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Inspired by fictional universes: LOTR, Dune, Halo, Harry Potter, 300, Gears of War
- Built with amazing open-source technologies
- Special thanks to the AI and world-building communities

## 📞 Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/builderOfTheWorlds/ashiorid_ai_manager/issues)
- **Discussions**: [GitHub Discussions](https://github.com/builderOfTheWorlds/ashiorid_ai_manager/discussions)

---

**Built with ⚔️ by the Builders of Worlds**
