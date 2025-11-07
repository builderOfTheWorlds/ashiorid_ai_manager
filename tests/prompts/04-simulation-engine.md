# Simulation Engine Testing Instructions

## Service Overview

**Port**: 8004
**Purpose**: Manages game world simulation, time progression, and world state
**Dependencies**: PostgreSQL (world state), Redis (event queue)

## Prerequisites

```bash
# Ensure service is running
kubectl get pods -n ashiorid | grep simulation-engine

# Check logs
kubectl logs -n ashiorid -l app=simulation-engine --tail=50

# Verify dependencies
kubectl get pods -n ashiorid | grep -E "postgres|redis"
```

## Test 1: Health Check

**Purpose**: Verify service is up with dependencies

```bash
curl http://localhost:8004/health
```

**Expected Response**:
```json
{
  "status": "healthy",
  "service": "simulation-engine",
  "database_connected": true,
  "redis_connected": true,
  "active_simulations": 0
}
```

## Test 2: Create Simulation World

**Purpose**: Initialize a new game world

```bash
curl -X POST http://localhost:8004/v1/worlds \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Eldoria Prime",
    "seed": 12345,
    "settings": {
      "time_scale": 1.0,
      "weather_enabled": true,
      "npc_spawning": true,
      "day_length_minutes": 24
    },
    "starting_date": "Year 1, Day 1"
  }'
```

**Expected Response**:
```json
{
  "world_id": "world_001",
  "name": "Eldoria Prime",
  "status": "created",
  "simulation_state": "paused",
  "created_at": "2024-11-07T12:00:00Z"
}
```

## Test 3: Get World State

**Purpose**: Retrieve current world state

```bash
curl http://localhost:8004/v1/worlds/world_001
```

**Expected Response**:
```json
{
  "world_id": "world_001",
  "name": "Eldoria Prime",
  "current_date": "Year 1, Day 1",
  "current_time": "08:00",
  "weather": {
    "condition": "clear",
    "temperature": 72,
    "wind_speed": 5
  },
  "active_regions": 5,
  "total_npcs": 0,
  "simulation_state": "paused"
}
```

## Test 4: Start Simulation

**Purpose**: Begin time progression

```bash
curl -X POST http://localhost:8004/v1/worlds/world_001/start
```

**Expected Response**:
```json
{
  "world_id": "world_001",
  "simulation_state": "running",
  "tick_rate": "1 second = 1 minute in-game"
}
```

## Test 5: Advance Time

**Purpose**: Manually advance simulation time

```bash
curl -X POST http://localhost:8004/v1/worlds/world_001/advance \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 60,
    "unit": "minutes"
  }'
```

**Expected Response**:
```json
{
  "world_id": "world_001",
  "previous_time": "08:00",
  "current_time": "09:00",
  "events_triggered": 3
}
```

## Test 6: Register Game Entity

**Purpose**: Add entity to simulation

```bash
curl -X POST http://localhost:8004/v1/worlds/world_001/entities \
  -H "Content-Type: application/json" \
  -d '{
    "entity_id": "char_001",
    "entity_type": "character",
    "location": {
      "region": "Eldoria",
      "zone": "Castle",
      "coordinates": {"x": 100, "y": 200}
    },
    "properties": {
      "needs_simulation": true,
      "affects_world": true
    }
  }'
```

**Expected Response**:
```json
{
  "entity_id": "char_001",
  "registered": true,
  "simulation_tracking": true
}
```

## Test 7: Query Entities in Region

**Purpose**: Get all entities in a specific region

```bash
curl "http://localhost:8004/v1/worlds/world_001/entities?region=Eldoria&limit=50"
```

**Expected Response**:
```json
{
  "region": "Eldoria",
  "entities": [
    {
      "entity_id": "char_001",
      "entity_type": "character",
      "location": {"region": "Eldoria", "zone": "Castle"},
      "state": "active"
    }
  ],
  "total": 1
}
```

## Test 8: Trigger World Event

**Purpose**: Manually trigger a world event

```bash
curl -X POST http://localhost:8004/v1/worlds/world_001/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "weather_change",
    "region": "Eldoria",
    "parameters": {
      "new_condition": "rain",
      "duration_minutes": 120
    }
  }'
```

**Expected Response**:
```json
{
  "event_id": "evt_001",
  "event_type": "weather_change",
  "status": "triggered",
  "affected_regions": ["Eldoria"],
  "duration": "120 minutes"
}
```

## Test 9: Get Active Events

**Purpose**: List all currently active events

```bash
curl http://localhost:8004/v1/worlds/world_001/events/active
```

**Expected Response**:
```json
{
  "active_events": [
    {
      "event_id": "evt_001",
      "event_type": "weather_change",
      "started_at": "09:00",
      "ends_at": "11:00",
      "region": "Eldoria"
    }
  ]
}
```

## Test 10: Update Entity State

**Purpose**: Update an entity's state in simulation

```bash
curl -X PATCH http://localhost:8004/v1/worlds/world_001/entities/char_001 \
  -H "Content-Type: application/json" \
  -d '{
    "location": {
      "region": "Dark Forest",
      "zone": "Entrance",
      "coordinates": {"x": 150, "y": 250}
    },
    "state": "moving"
  }'
```

**Expected Response**:
```json
{
  "entity_id": "char_001",
  "updated": true,
  "previous_location": {"region": "Eldoria", "zone": "Castle"},
  "current_location": {"region": "Dark Forest", "zone": "Entrance"}
}
```

## Test 11: Pause Simulation

**Purpose**: Pause time progression

```bash
curl -X POST http://localhost:8004/v1/worlds/world_001/pause
```

**Expected Response**:
```json
{
  "world_id": "world_001",
  "simulation_state": "paused",
  "paused_at": "09:30"
}
```

## Test 12: Get Simulation Statistics

**Purpose**: Retrieve simulation performance metrics

```bash
curl http://localhost:8004/v1/worlds/world_001/stats
```

**Expected Response**:
```json
{
  "world_id": "world_001",
  "uptime_seconds": 3600,
  "total_ticks": 3600,
  "average_tick_duration_ms": 15,
  "entities_tracked": 1,
  "events_processed": 156,
  "errors": 0
}
```

## Test 13: World History Query

**Purpose**: Get historical events

```bash
curl "http://localhost:8004/v1/worlds/world_001/history?from=Year%201,%20Day%201&limit=100"
```

**Expected Response**:
```json
{
  "history": [
    {
      "timestamp": "Year 1, Day 1 - 09:00",
      "event_type": "weather_change",
      "description": "Weather changed to rain in Eldoria",
      "importance": "low"
    },
    {
      "timestamp": "Year 1, Day 1 - 09:15",
      "event_type": "entity_moved",
      "description": "char_001 moved from Eldoria to Dark Forest",
      "importance": "medium"
    }
  ],
  "total": 2
}
```

## Test 14: Save World State

**Purpose**: Create a snapshot of world state

```bash
curl -X POST http://localhost:8004/v1/worlds/world_001/save \
  -H "Content-Type: application/json" \
  -d '{
    "name": "After First Hour",
    "description": "World state after initial simulation"
  }'
```

**Expected Response**:
```json
{
  "save_id": "save_001",
  "world_id": "world_001",
  "saved_at": "Year 1, Day 1 - 09:30",
  "size_bytes": 45678
}
```

## Test 15: Delete World

**Purpose**: Clean up simulation world

```bash
curl -X DELETE http://localhost:8004/v1/worlds/world_001
```

**Expected Response**:
```json
{
  "world_id": "world_001",
  "status": "deleted",
  "entities_removed": 1
}
```

## Integration Tests

### Test with Character Agent Service

```bash
# Create character in character service
curl -X POST http://localhost:8003/v1/characters -d '{...}'

# Register in simulation
curl -X POST http://localhost:8004/v1/worlds/world_001/entities \
  -d '{"entity_id": "char_001", ...}'

# Update character location in character service
curl -X PATCH http://localhost:8003/v1/characters/char_001/state \
  -d '{"location": "Dark Forest"}'

# Verify simulation reflects the change
curl http://localhost:8004/v1/worlds/world_001/entities/char_001
```

## Performance Benchmarks

**Baseline Performance Targets**:
- Tick processing: < 20ms per tick
- Entity update: < 10ms
- Event triggering: < 50ms
- State queries: < 100ms
- World creation: < 500ms
- Support 1000+ concurrent entities

**Load Testing**:
```bash
# Test with multiple entities
for i in {1..100}; do
  curl -X POST http://localhost:8004/v1/worlds/world_001/entities \
    -H "Content-Type: application/json" \
    -d "{\"entity_id\": \"entity_$i\", \"entity_type\": \"npc\"}" &
done
wait

# Measure tick performance
curl http://localhost:8004/v1/worlds/world_001/stats
```

## Common Issues

### Issue: Simulation runs too fast/slow
**Check**:
- time_scale setting
- Server CPU usage
- Tick rate configuration

### Issue: Entity state desync
**Check**:
- Redis connection
- Database transaction handling
- Race conditions

### Issue: Memory leaks
**Check**:
- Entity cleanup on delete
- Event queue pruning
- Historical data retention

### Issue: Events not triggering
**Check**:
- Event conditions
- Simulation running state
- Redis event queue

## Success Criteria

- ✅ Health check passes
- ✅ Can create and manage worlds
- ✅ Time progression works correctly
- ✅ Entities track and update properly
- ✅ Events trigger and resolve
- ✅ World state persists to database
- ✅ Performance meets targets with 100+ entities
- ✅ History tracking works
- ✅ Save/load functionality works
- ✅ Integration with character service works
- ✅ No memory leaks during extended simulation
