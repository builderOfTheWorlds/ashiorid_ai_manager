# Simulation Engine

Tick-based agent simulation with 100+ autonomous agents for Ashiorid AI Manager.

## Features

- **Tick-Based Engine**: Runs at 10 ticks/second with consistent timing
- **Agent Simulation**: Support for 1000+ concurrent agents
- **Need System**: Hunger, thirst, energy, and health tracking
- **Rule-Based AI**: Priority-based decision making for agent actions
- **Event System**: Redis pub/sub for real-time simulation events
- **Spatial Grid**: 100x100 grid world with agent movement
- **PostgreSQL Storage**: Persistent agent state and simulation history
- **REST API**: Full control over simulation lifecycle

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment
export DATABASE_URL=postgresql+asyncpg://user:pass@localhost/ashiorid
export REDIS_URL=redis://localhost:6379/0

# Run service
uvicorn src.main:app --reload --port 8004
```

## API Endpoints

### Start Simulation
```bash
POST /simulation/start?num_agents=100
```

Starts simulation with specified number of agents (default: 100, max: 1000).

### Get Simulation Status
```bash
GET /simulation/status
```

Returns current simulation state:
```json
{
  "tick": 12345,
  "active_agents": 98,
  "total_agents": 100,
  "ticks_per_second": 10,
  "world_events": []
}
```

### Stop Simulation
```bash
POST /simulation/stop
```

Gracefully stops the simulation loop.

### List Agents
```bash
GET /agents?limit=100&offset=0
```

Returns paginated list of agents with their current state.

### Get Agent Details
```bash
GET /agents/{agent_id}
```

Returns detailed information for a specific agent:
```json
{
  "id": "agent-uuid",
  "name": "Agent-12345678",
  "state": "active",
  "position": [42, 73],
  "attributes": {
    "hunger": 0.45,
    "thirst": 0.62,
    "energy": 0.78,
    "health": 0.95
  },
  "inventory": [],
  "metadata": {}
}
```

### Manual Agent Action
```bash
POST /agents/{agent_id}/action
{
  "action": "seek_food"
}
```

Available actions:
- `seek_food` - Reduces hunger by 0.3
- `seek_water` - Reduces thirst by 0.4
- `rest` - Increases energy by 0.5
- `move` - Random movement in grid (consumes energy)
- `idle` - No action

### Get Recent Events
```bash
GET /simulation/events?limit=50
```

Returns recent simulation events (agent births, deaths, interactions).

## Architecture

### Simulation Loop

```
┌─────────────────────────────────────┐
│     Simulation Loop (10 TPS)        │
├─────────────────────────────────────┤
│  1. Process Tick                    │
│     - Get all active agents         │
│     - Update agent needs            │
│     - Check health/death            │
│     - Decide actions                │
│     - Execute actions               │
│  2. Save to Database                │
│  3. Publish Events to Redis         │
│  4. Sleep to maintain tick rate     │
└─────────────────────────────────────┘
```

### Agent State Machine

```
                  ┌─────────┐
                  │  active │
                  └────┬────┘
                       │
          health <= 0.1 or age > 1000
                       │
                  ┌────▼────┐
                  │  dead   │
                  └─────────┘
```

### Decision Priority

Agents make decisions based on need priorities:

1. **Critical Thirst** (thirst > 0.8) → `seek_water`
2. **High Hunger** (hunger > 0.7) → `seek_food`
3. **Low Energy** (energy < 0.3) → `rest`
4. **Default** → Random (`move` or `idle`)

### Need Decay Rates (per tick)

- **Hunger**: +0.001/tick (reaches critical in ~700 ticks / 70 seconds)
- **Thirst**: +0.002/tick (reaches critical in ~400 ticks / 40 seconds)
- **Energy**: -0.0015/tick (depletes in ~666 ticks / 67 seconds)

### Health Degradation

- Hunger > 0.7: -0.005 health/tick
- Thirst > 0.8: -0.01 health/tick
- Health <= 0.1: Agent dies

## Configuration

Edit `config.yaml` to customize:

```yaml
simulation:
  grid_size: 100           # World grid dimensions
  tick_rate: 10            # Ticks per second
  max_agents: 1000         # Maximum concurrent agents

  hunger_decay: 0.001      # Hunger increase per tick
  thirst_decay: 0.002      # Thirst increase per tick
  energy_decay: 0.0015     # Energy decrease per tick

  llm_decision_probability: 0.05    # % of decisions using LLM
  llm_decision_interval: 50         # Ticks between LLM decisions
```

## Monitoring

### Prometheus Metrics

- `simulation_agent_count{state}` - Number of agents by state
- `simulation_tick_count` - Total simulation ticks
- `simulation_tick_latency_seconds` - Time to process each tick
- `simulation_event_count{type}` - Events by type

### Redis Events

Subscribe to `simulation_events` channel for real-time updates:

```python
import redis
r = redis.Redis()
pubsub = r.pubsub()
pubsub.subscribe('simulation_events')

for message in pubsub.listen():
    print(message['data'])
```

Event types:
- `agent_spawned`
- `agent_died`
- `agent_action`
- `simulation_tick` (every 100 ticks)

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

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Hot Reload Development

```bash
# Using Tilt
tilt up simulation-engine

# Using Docker Compose
docker-compose up simulation-engine
```

## Future Enhancements

- **LLM-Driven Decisions**: Periodic AI decision-making for complex scenarios
- **Agent Interactions**: Social behaviors (conversation, trade, cooperation)
- **Resource System**: Food and water sources in the world
- **Agent Memory**: Long-term memory for persistent behaviors
- **Emergent Behaviors**: Complex patterns from simple rules
- **World Events**: Random events affecting multiple agents
- **Agent Reproduction**: Population dynamics
- **Skill System**: Agent abilities that improve over time

## Performance

- **Throughput**: 1000 agents at 10 TPS = 10,000 agent updates/second
- **Latency**: Average tick processing <50ms for 1000 agents
- **Database**: Connection pooling with 20 connections
- **Memory**: ~1MB per 1000 agents

## License

MIT License
