# AI Manager Service

Master orchestrator for Ashiorid AI Manager - coordinates all microservices for comprehensive world-building queries.

## Features

- **Full Orchestration**: Coordinates all services (LLM Proxy, Lore RAG, Character Agent, Simulation Engine)
- **Multi-Locale Support**: Process queries in 7+ languages
- **World Event Generation**: Automatic narrative event creation based on simulation state
- **Context-Aware Responses**: Combines lore, simulation data, and character personalities
- **Health Monitoring**: Real-time health checks for all dependent services
- **Event Streaming**: Redis pub/sub for world events
- **Prometheus Metrics**: Comprehensive observability

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment
export REDIS_URL=redis://localhost:6379/0

# Run service
uvicorn src.main:app --reload --port 8005
```

## API Endpoints

### Process Query

```bash
POST /api/v1/query
{
  "query": "What's happening in the world?",
  "locale": "en-US",
  "include_simulation": true,
  "include_lore": true
}
```

Orchestrates a comprehensive response:
1. Searches lore database for relevant context
2. Retrieves current simulation state
3. Generates response with full context

Response:
```json
{
  "response": "The world is bustling with activity...",
  "sources": ["Lore excerpt 1", "Lore excerpt 2"],
  "simulation_snapshot": {
    "tick": 12345,
    "active_agents": 98,
    "total_agents": 100
  },
  "metadata": {
    "locale": "en-US",
    "lore_items": 5,
    "model": "llama3.2:3b",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### Query Character

```bash
POST /api/v1/character/query
{
  "character_name": "gandalf",
  "message": "What should we do?",
  "locale": "en-US",
  "include_simulation": true
}
```

Queries a character with simulation context for contextually-aware responses.

### Trigger World Event

```bash
POST /api/v1/events/trigger
{
  "event_type": "natural_disaster",
  "description": "A massive earthquake shakes the land",
  "agent_ids": ["agent-1", "agent-2"],
  "location": [42, 73]
}
```

Manually trigger a world event. If description is not provided, uses LLM to generate narrative.

### Get Recent Events

```bash
GET /api/v1/events/recent?limit=20
```

Returns recent world events with narrative descriptions.

### System Status

```bash
GET /api/v1/status
```

Returns comprehensive system status:
```json
{
  "status": "healthy",
  "services": {
    "llm_proxy": {
      "healthy": true,
      "status": "healthy",
      "latency_ms": 45
    },
    "lore_rag": {...},
    "character_agent": {...},
    "simulation_engine": {...}
  },
  "simulation": {
    "tick": 12345,
    "active_agents": 98
  },
  "world_events": [...]
}
```

### Service Health

```bash
GET /api/v1/services/health
```

Check health of all dependent services.

## Architecture

### Orchestration Flow

```
┌─────────────────────────────────────────────┐
│          User Query                          │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│       AI Manager (Orchestrator)             │
├─────────────────────────────────────────────┤
│  1. Parse query and locale                  │
│  2. Search lore database ────────┐          │
│  3. Get simulation state ─────┐  │          │
│  4. Build context            │  │          │
│  5. Generate response        │  │          │
└──────────────────────────────┼──┼──────────┘
                               │  │
               ┌───────────────┘  └────────────┐
               ▼                                ▼
      ┌────────────────┐              ┌────────────────┐
      │ Simulation     │              │ Lore RAG       │
      │ Engine         │              │ Service        │
      └────────────────┘              └────────────────┘
               │
               ▼
      ┌────────────────┐
      │ LLM Proxy      │
      │ Service        │
      └────────────────┘
```

### World Event Generation

The AI Manager automatically generates narrative world events based on simulation state:

```
┌──────────────────────────────────────┐
│     World Event Generator            │
├──────────────────────────────────────┤
│  Every 60 seconds:                   │
│  1. Check simulation state           │
│  2. If enough agents active          │
│  3. Random chance (10%) for event    │
│  4. Select event type                │
│  5. Generate narrative with LLM      │
│  6. Publish to Redis channel         │
│  7. Store in recent events           │
└──────────────────────────────────────┘
```

## Configuration

Edit `config.yaml` to customize:

```yaml
orchestration:
  default_provider: "ollama"      # LLM provider
  default_model: "llama3.2:3b"    # Default model
  temperature: 0.7                # Response creativity
  max_tokens: 2048                # Max response length
  max_lore_results: 5             # Lore context items
  lore_score_threshold: 0.7       # Minimum relevance

world_events:
  enabled: true                   # Enable event generation
  check_interval: 60              # Seconds between checks
  min_agents_for_event: 10        # Min agents for events
  event_probability: 0.1          # Chance per check (10%)
  event_types:
    - natural_disaster
    - resource_discovery
    - faction_conflict
    - mysterious_phenomenon
    - technological_breakthrough

locales:
  default: "en-US"
  supported:
    - "en-US"    # English (US)
    - "en-GB"    # English (UK)
    - "es-ES"    # Spanish
    - "fr-FR"    # French
    - "de-DE"    # German
    - "ja-JP"    # Japanese
    - "zh-CN"    # Chinese
```

## Multi-Locale Support

The AI Manager adapts responses based on user locale:

```python
# English
POST /api/v1/query
{"query": "What's happening?", "locale": "en-US"}
# Response in English

# Spanish
POST /api/v1/query
{"query": "¿Qué está pasando?", "locale": "es-ES"}
# Response in Spanish

# Japanese
POST /api/v1/query
{"query": "何が起こっているの？", "locale": "ja-JP"}
# Response in Japanese
```

## Event Types

### Natural Disaster
Environmental catastrophes affecting multiple agents:
- Earthquakes
- Floods
- Storms
- Wildfires

### Resource Discovery
Finding valuable resources:
- Food sources
- Water springs
- Minerals
- Artifacts

### Faction Conflict
Inter-agent conflicts:
- Territory disputes
- Resource competition
- Ideological differences

### Mysterious Phenomenon
Unexplained occurrences:
- Strange lights
- Anomalies
- Cosmic events

### Technological Breakthrough
Advances in agent society:
- Tool creation
- Agriculture
- Construction
- Communication

## Monitoring

### Prometheus Metrics

- `ai_manager_requests_total{endpoint, method}` - Total requests by endpoint
- `ai_manager_request_latency_seconds{endpoint}` - Request latency
- `ai_manager_active_sessions` - Active user sessions
- `ai_manager_world_events_total{event_type}` - Events generated by type
- `ai_manager_service_health{service}` - Dependent service health

### Redis Events

Subscribe to world events:

```python
import redis
r = redis.Redis()
pubsub = r.pubsub()
pubsub.subscribe('world_events')

for message in pubsub.listen():
    event = json.loads(message['data'])
    print(f"Event: {event['type']} - {event['description']}")
```

## Development

### Running Tests

```bash
# Unit tests
pytest tests/unit -v

# Integration tests
pytest tests/integration -v

# With coverage
pytest --cov=src --cov-report=html
```

### Hot Reload Development

```bash
# Using Tilt
tilt up ai-manager

# Using Docker Compose
docker-compose up ai-manager
```

## Example Workflows

### Complete World Query

```bash
# User asks about the world
POST /api/v1/query
{
  "query": "Tell me about the current state of the world and recent events",
  "include_simulation": true,
  "include_lore": true
}

# AI Manager:
# 1. Searches lore for "world state" context
# 2. Gets simulation: 98 agents active, tick 12345
# 3. Gets recent events: 5 events in last hour
# 4. Generates comprehensive response combining all context
```

### Character Interaction

```bash
# User asks Gandalf for advice
POST /api/v1/character/query
{
  "character_name": "gandalf",
  "message": "The simulation shows many agents are struggling. What should we do?",
  "include_simulation": true
}

# AI Manager:
# 1. Gets simulation state
# 2. Formats as context for Gandalf
# 3. Queries character-agent-service
# 4. Returns in-character response with simulation awareness
```

## Dependencies

- **llm-proxy-service**: Multi-provider LLM access
- **lore-rag-service**: Semantic lore search
- **character-agent-service**: Character personalities
- **simulation-engine**: Agent simulation
- **Redis**: Event streaming
- **Prometheus**: Metrics collection

## Future Enhancements

- **User Sessions**: Maintain conversation history per user
- **Custom Event Rules**: User-defined event triggers
- **Multi-Agent Narratives**: Events involving agent interactions
- **Temporal Queries**: "What happened yesterday in the simulation?"
- **Predictive Analytics**: Forecast simulation trends
- **Voice Interface**: Audio query/response support
- **Visual Dashboard**: Web UI for system status
- **Plugin System**: Custom orchestration strategies

## License

MIT License
