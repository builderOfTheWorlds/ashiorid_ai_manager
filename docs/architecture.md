# Ashiorid AI Manager - Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Interface                          │
│                    (CLI Dashboard / Web UI)                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────┴────────────────────────────────────┐
│                     API Gateway (Traefik)                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
┌─────────▼────────┐ ┌──────▼──────┐ ┌────────▼─────────┐
│  LLM Proxy       │ │  Lore RAG   │ │  Character       │
│  Service         │ │  Service    │ │  Agent Service   │
│                  │ │             │ │                  │
│ • Multi-provider │ │ • Vector DB │ │ • AI Characters  │
│ • Caching        │ │ • Search    │ │ • Personalities  │
│ • Cost tracking  │ │ • Embeddings│ │ • Conversations  │
└─────────┬────────┘ └──────┬──────┘ └────────┬─────────┘
          │                  │                  │
          └──────────────────┼──────────────────┘
                             │
          ┌──────────────────┴──────────────────┐
          │                                     │
┌─────────▼────────┐                  ┌────────▼─────────┐
│  Simulation      │                  │  AI Manager      │
│  Engine          │◄─────────────────┤  Service         │
│                  │                  │                  │
│ • Agent sim      │                  │ • Orchestration  │
│ • World state    │                  │ • Coordination   │
│ • Events         │                  │ • World events   │
└─────────┬────────┘                  └────────┬─────────┘
          │                                     │
          └─────────────────┬───────────────────┘
                            │
┌───────────────────────────┴──────────────────────────────────┐
│                   Infrastructure Layer                        │
│                                                               │
│  ┌──────────┐  ┌────────┐  ┌──────────┐  ┌──────────────┐  │
│  │PostgreSQL│  │ Redis  │  │  Qdrant  │  │ Prometheus   │  │
│  │          │  │        │  │          │  │  + Grafana   │  │
│  └──────────┘  └────────┘  └──────────┘  └──────────────┘  │
└───────────────────────────────────────────────────────────────┘
```

## Microservices

### 1. LLM Proxy Service (Port: 8001)
**Purpose**: Unified interface for multiple LLM providers

**Responsibilities**:
- Route requests to OpenAI, Anthropic, or Ollama
- Cache responses in Redis
- Track token usage and costs
- Rate limiting
- Provider failover

**Dependencies**: Redis

**Endpoints**:
- `POST /v1/chat/completions` - OpenAI-compatible chat
- `GET /providers` - List providers
- `GET /stats` - Service statistics
- `GET /cost/summary` - Cost tracking

### 2. Lore RAG Service (Port: 8002)
**Purpose**: Semantic search over fictional universe knowledge

**Responsibilities**:
- Ingest lore from various sources (LOTR, Dune, Halo, etc.)
- Generate embeddings using Ollama
- Semantic search via Qdrant
- Context retrieval for character agents

**Dependencies**: Qdrant, Ollama

**Endpoints**:
- `POST /ingest` - Upload lore documents
- `POST /search` - Semantic search
- `GET /collections` - List knowledge bases

### 3. Character Agent Service (Port: 8003)
**Purpose**: AI characters with distinct personalities

**Responsibilities**:
- Manage character personalities and traits
- Handle multi-turn conversations
- Query lore for context
- Track conversation history

**Dependencies**: PostgreSQL, LLM Proxy, Lore RAG

**Endpoints**:
- `POST /characters/{name}/chat` - Chat with character
- `GET /characters` - List characters
- `POST /characters` - Create character

### 4. Simulation Engine (Port: 8004)
**Purpose**: Lightweight agent simulation

**Responsibilities**:
- Simulate 100+ agents with basic needs (hunger, thirst, energy)
- Fast tick-based simulation (10+ ticks/sec)
- Selective LLM invocation for complex decisions
- Real-time events via Redis pub/sub

**Dependencies**: PostgreSQL, Redis, LLM Proxy

**Endpoints**:
- `POST /simulation/start` - Start simulation
- `GET /simulation/status` - Current state
- `GET /agents` - List agents
- `POST /agents/{id}/action` - Control agent

### 5. AI Manager Service (Port: 8005)
**Purpose**: Master orchestrator

**Responsibilities**:
- Coordinate all services
- Generate world events
- Locale-based processing
- Global world state management

**Dependencies**: All other services

**Endpoints**:
- `POST /world/event` - Trigger event
- `GET /world/status` - Global state
- `POST /locales/{id}/process` - Process locale

## Infrastructure Components

### PostgreSQL
- **Purpose**: Relational data (agent state, conversations, world history)
- **Storage**: 20GB persistent volume
- **Backup**: Daily via backup script

### Redis
- **Purpose**: Caching, pub/sub, rate limiting
- **Storage**: 5GB persistent volume with AOF persistence
- **Features**: Response cache, real-time events

### Qdrant
- **Purpose**: Vector database for semantic search
- **Storage**: 10GB persistent volume
- **Features**: Collections for different universes, gRPC + HTTP

### Prometheus + Grafana
- **Purpose**: Metrics and monitoring
- **Metrics**: Request rates, latency, costs, agent counts
- **Dashboards**: Pre-configured for each service

### Traefik
- **Purpose**: API gateway and ingress
- **Features**: Auto-discovery, load balancing, dashboard

## Data Flow Examples

### Example 1: Character Chat with Lore Context

```
1. User → API Gateway → Character Agent Service
   POST /characters/gandalf/chat
   {"message": "What should we do about the ring?"}

2. Character Agent → Lore RAG Service
   POST /search
   {"query": "ring of power", "collection": "lotr"}

3. Lore RAG → Qdrant
   Semantic search returns relevant passages

4. Character Agent → LLM Proxy Service
   POST /v1/chat/completions
   {
     "messages": [
       {"role": "system", "content": "You are Gandalf... [context from lore]"},
       {"role": "user", "content": "What should we do about the ring?"}
     ]
   }

5. LLM Proxy → Ollama/OpenAI/Anthropic
   Generate response

6. Response flows back to user
```

### Example 2: Agent Simulation Decision

```
1. Simulation Engine: Tick 1000
   Agent-042 is hungry (hunger: 0.9)

2. Simulation Engine checks rules:
   - Simple decision: Go to nearest food source
   - Complex decision (low probability): Ask LLM

3. If complex decision triggered:
   Simulation Engine → LLM Proxy
   POST /v1/chat/completions
   {
     "messages": [
       {"role": "system", "content": "You are Agent-042 in a survival sim..."},
       {"role": "user", "content": "You're very hungry. Food nearby but guarded. What do you do?"}
     ],
     "provider": "ollama",
     "model": "llama3.2:1b"  // Fast, cheap model
   }

4. LLM response influences agent behavior

5. State updated in PostgreSQL
   Event published to Redis pub/sub
```

## Deployment Architecture

### Kubernetes Deployment

```
Namespace: ashiorid
├── Infrastructure
│   ├── postgres (StatefulSet)
│   ├── redis (Deployment)
│   ├── qdrant (Deployment)
│   └── traefik (Deployment)
├── Monitoring
│   ├── prometheus (Deployment)
│   └── grafana (Deployment)
└── Services
    ├── llm-proxy (Deployment, 2 replicas)
    ├── lore-rag (Deployment, 1 replica)
    ├── character-agent (Deployment, 2 replicas)
    ├── simulation-engine (Deployment, 1 replica)
    └── ai-manager (Deployment, 1 replica)
```

### Resource Allocation

| Component | CPU Request | CPU Limit | Memory Request | Memory Limit |
|-----------|-------------|-----------|----------------|--------------|
| postgres | 250m | 1000m | 512Mi | 2Gi |
| redis | 100m | 500m | 256Mi | 2Gi |
| qdrant | 250m | 2000m | 512Mi | 4Gi |
| prometheus | 250m | 1000m | 512Mi | 2Gi |
| grafana | 100m | 500m | 256Mi | 1Gi |
| llm-proxy | 100m | 1000m | 256Mi | 1Gi |
| lore-rag | 250m | 1000m | 512Mi | 2Gi |
| character-agent | 100m | 500m | 256Mi | 1Gi |
| simulation-engine | 500m | 2000m | 512Mi | 2Gi |
| ai-manager | 100m | 500m | 256Mi | 1Gi |

## Technology Stack

### Backend
- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Async**: asyncio, httpx
- **Validation**: Pydantic

### Databases
- **Relational**: PostgreSQL 16
- **Cache**: Redis 7
- **Vector**: Qdrant

### LLM Providers
- **Cloud**: OpenAI, Anthropic
- **Local**: Ollama (llama3.2, phi3)

### Infrastructure
- **Container**: Docker
- **Orchestration**: Kubernetes (K3s)
- **Ingress**: Traefik
- **Monitoring**: Prometheus, Grafana
- **Dev Tools**: Tilt

### Development
- **Testing**: pytest, pytest-asyncio
- **Linting**: black, flake8, isort
- **CI/CD**: GitHub Actions

## Security Considerations

### Current (POC)
- No authentication between services (trust-based)
- API keys via environment variables
- Secrets in ConfigMaps (development only)

### Production Roadmap
- mTLS between services
- OAuth2/JWT for API authentication
- HashiCorp Vault for secrets
- Network policies in Kubernetes
- RBAC for service accounts

## Scalability

### Horizontal Scaling
- **Stateless services**: llm-proxy, character-agent, lore-rag
- **Load balancing**: Via Kubernetes Service
- **Session affinity**: Redis-backed sessions

### Vertical Scaling
- **Resource limits**: Configured per service
- **Auto-scaling**: HPA based on CPU/memory

### Database Scaling
- **PostgreSQL**: Read replicas for queries
- **Redis**: Redis Cluster for high availability
- **Qdrant**: Sharding for large collections

## Monitoring and Observability

### Metrics (Prometheus)
- Request rates, latency, error rates
- Token usage, LLM costs
- Agent counts, simulation tick rate
- Cache hit rates

### Logs (Structured JSON)
- Service-level logs
- Request/response tracing
- Error tracking

### Dashboards (Grafana)
- Service health overview
- LLM cost tracking
- Simulation statistics
- Infrastructure metrics

### CLI Dashboard
- Real-time service health
- Request rates
- Cost summary
- Agent states

## Future Enhancements

1. **Event Sourcing**: Add Kafka for complete event history
2. **Web UI**: React dashboard for world visualization
3. **Distributed Tracing**: OpenTelemetry for request tracing
4. **Advanced RAG**: Multi-stage retrieval, reranking
5. **Agent Learning**: Persistent agent memory and evolution
6. **Multi-Region**: Deploy across regions for redundancy
