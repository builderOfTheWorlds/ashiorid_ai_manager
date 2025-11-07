# AI Manager Service Testing Instructions

## Service Overview

**Port**: 8005
**Purpose**: Orchestrates all AI services, manages event generation, and coordinates the AI system
**Dependencies**: All other services (LLM Proxy, Lore RAG, Character Agent, Simulation Engine)

## Prerequisites

```bash
# Ensure ALL services are running
kubectl get pods -n ashiorid

# Verify all dependencies are healthy
curl http://localhost:8001/health  # LLM Proxy
curl http://localhost:8002/health  # Lore RAG
curl http://localhost:8003/health  # Character Agent
curl http://localhost:8004/health  # Simulation Engine

# Check AI Manager logs
kubectl logs -n ashiorid -l app=ai-manager --tail=50
```

## Test 1: Health Check

**Purpose**: Verify service and all dependencies

```bash
curl http://localhost:8005/health
```

**Expected Response**:
```json
{
  "status": "healthy",
  "service": "ai-manager",
  "dependencies": {
    "llm_proxy": "healthy",
    "lore_rag": "healthy",
    "character_agent": "healthy",
    "simulation_engine": "healthy"
  },
  "redis_connected": true
}
```

## Test 2: Initialize Game Session

**Purpose**: Create a complete game session with all services

```bash
curl -X POST http://localhost:8005/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "game_name": "Test Adventure",
    "world_settings": {
      "name": "Eldoria Prime",
      "seed": 12345
    },
    "initial_characters": [
      {
        "name": "Aldric",
        "class": "Warrior",
        "personality": {"traits": ["brave", "loyal"]}
      }
    ]
  }'
```

**Expected Response**:
```json
{
  "session_id": "session_001",
  "world_id": "world_001",
  "characters": [
    {"character_id": "char_001", "name": "Aldric"}
  ],
  "status": "initialized",
  "services_ready": true
}
```

## Test 3: Generate Dynamic Event

**Purpose**: Test AI-driven event generation

```bash
curl -X POST http://localhost:8005/v1/sessions/session_001/generate-event \
  -H "Content-Type: application/json" \
  -d '{
    "context": {
      "location": "Eldoria Castle",
      "characters_present": ["char_001"],
      "time_of_day": "morning",
      "recent_events": []
    },
    "event_type": "encounter",
    "difficulty": "medium"
  }'
```

**Expected Response**:
```json
{
  "event_id": "evt_001",
  "event_type": "encounter",
  "title": "A Plea for Help",
  "description": "A distressed merchant approaches Aldric, claiming bandits have stolen his goods in the Dark Forest.",
  "participants": ["char_001", "npc_merchant_001"],
  "options": [
    {
      "id": "opt_1",
      "action": "Offer to help recover the goods",
      "consequences": ["combat_likely", "reputation_gain"]
    },
    {
      "id": "opt_2",
      "action": "Direct him to the guards",
      "consequences": ["no_combat", "reputation_neutral"]
    }
  ],
  "lore_context": [
    "The Dark Forest is known for bandit activity"
  ]
}
```

## Test 4: Process Character Action

**Purpose**: Coordinate action across all services

```bash
curl -X POST http://localhost:8005/v1/sessions/session_001/action \
  -H "Content-Type: application/json" \
  -d '{
    "character_id": "char_001",
    "action": "accept_quest",
    "event_id": "evt_001",
    "option_id": "opt_1",
    "dialogue": "I will help you recover your goods."
  }'
```

**Expected Response**:
```json
{
  "action_id": "action_001",
  "character_response": {
    "dialogue": "Fear not, good merchant. I shall venture into the Dark Forest and return your goods. It is my duty.",
    "emotion": "determined"
  },
  "world_updates": {
    "character_location": "traveling_to_dark_forest",
    "quest_added": "quest_001",
    "time_advanced": "30 minutes"
  },
  "new_events": [
    {
      "event_id": "evt_002",
      "type": "travel",
      "description": "Aldric begins his journey to the Dark Forest"
    }
  ]
}
```

## Test 5: Get Session State

**Purpose**: Retrieve complete session state

```bash
curl http://localhost:8005/v1/sessions/session_001
```

**Expected Response**:
```json
{
  "session_id": "session_001",
  "world_state": {
    "world_id": "world_001",
    "current_time": "09:30",
    "active_events": 2
  },
  "characters": [
    {
      "character_id": "char_001",
      "name": "Aldric",
      "location": "traveling_to_dark_forest",
      "state": "in_quest",
      "health": 100
    }
  ],
  "active_quests": [
    {
      "quest_id": "quest_001",
      "title": "Recover Merchant's Goods",
      "status": "in_progress"
    }
  ],
  "session_duration": "30 minutes"
}
```

## Test 6: Batch Event Generation

**Purpose**: Generate multiple contextual events

```bash
curl -X POST http://localhost:8005/v1/sessions/session_001/generate-events/batch \
  -H "Content-Type: application/json" \
  -d '{
    "count": 5,
    "timeframe": "next_hour",
    "event_types": ["encounter", "discovery", "dialogue"]
  }'
```

**Expected Response**:
```json
{
  "events_generated": 5,
  "events": [
    {
      "event_id": "evt_003",
      "type": "encounter",
      "scheduled_time": "09:45",
      "title": "Wolves in the Forest"
    },
    {
      "event_id": "evt_004",
      "type": "discovery",
      "scheduled_time": "10:00",
      "title": "Abandoned Camp"
    }
  ]
}
```

## Test 7: Query Available Actions

**Purpose**: Get AI-suggested actions for character

```bash
curl -X POST http://localhost:8005/v1/sessions/session_001/actions/suggest \
  -H "Content-Type: application/json" \
  -d '{
    "character_id": "char_001",
    "context": "current"
  }'
```

**Expected Response**:
```json
{
  "suggestions": [
    {
      "action": "investigate_camp",
      "reasoning": "The abandoned camp might contain clues about the bandits",
      "priority": "high",
      "estimated_time": "15 minutes"
    },
    {
      "action": "rest_and_recover",
      "reasoning": "Your health is low after the wolf encounter",
      "priority": "medium",
      "estimated_time": "30 minutes"
    }
  ]
}
```

## Test 8: Process Parallel Actions

**Purpose**: Test concurrent character actions

```bash
curl -X POST http://localhost:8005/v1/sessions/session_001/actions/parallel \
  -H "Content-Type: application/json" \
  -d '{
    "actions": [
      {
        "character_id": "char_001",
        "action": "search_area",
        "target": "abandoned_camp"
      },
      {
        "character_id": "char_002",
        "action": "stand_guard",
        "location": "camp_perimeter"
      }
    ]
  }'
```

**Expected Response**:
```json
{
  "processed": 2,
  "results": [
    {
      "character_id": "char_001",
      "success": true,
      "discoveries": ["bandit_map", "stolen_goods"]
    },
    {
      "character_id": "char_002",
      "success": true,
      "status": "alert",
      "spotted": []
    }
  ],
  "time_elapsed": "15 minutes"
}
```

## Test 9: Session Analytics

**Purpose**: Get AI system performance metrics

```bash
curl http://localhost:8005/v1/sessions/session_001/analytics
```

**Expected Response**:
```json
{
  "session_id": "session_001",
  "analytics": {
    "total_events": 5,
    "total_actions": 3,
    "ai_decisions": 8,
    "average_response_time_ms": 345,
    "character_interactions": 12,
    "lore_retrievals": 15,
    "llm_calls": 20,
    "cache_hit_rate": 0.65
  },
  "performance": {
    "events_per_hour": 10,
    "actions_per_hour": 6,
    "avg_event_quality_score": 0.85
  }
}
```

## Test 10: Export Session Data

**Purpose**: Export complete session for analysis

```bash
curl http://localhost:8005/v1/sessions/session_001/export
```

**Expected Response**: JSON file with complete session data

## Test 11: Pause/Resume Session

**Purpose**: Test session state management

```bash
# Pause
curl -X POST http://localhost:8005/v1/sessions/session_001/pause

# Resume
curl -X POST http://localhost:8005/v1/sessions/session_001/resume
```

## Test 12: End Session

**Purpose**: Properly clean up session

```bash
curl -X POST http://localhost:8005/v1/sessions/session_001/end \
  -H "Content-Type: application/json" \
  -d '{
    "save_state": true,
    "cleanup": true
  }'
```

**Expected Response**:
```json
{
  "session_id": "session_001",
  "status": "ended",
  "final_state_saved": true,
  "duration": "2 hours",
  "summary": {
    "quests_completed": 1,
    "events_experienced": 5,
    "characters_involved": 1
  }
}
```

## Integration Tests

### Full System Integration

```bash
# Create session
SESSION_ID=$(curl -X POST http://localhost:8005/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{"game_name": "Integration Test"}' | jq -r '.session_id')

# Generate event
EVENT_ID=$(curl -X POST http://localhost:8005/v1/sessions/$SESSION_ID/generate-event \
  -H "Content-Type: application/json" \
  -d '{"context": {...}}' | jq -r '.event_id')

# Process action
curl -X POST http://localhost:8005/v1/sessions/$SESSION_ID/action \
  -H "Content-Type: application/json" \
  -d "{\"event_id\": \"$EVENT_ID\", ...}"

# Verify all services updated correctly
curl http://localhost:8003/v1/characters/char_001  # Character state
curl http://localhost:8004/v1/worlds/world_001     # World state
curl http://localhost:8005/v1/sessions/$SESSION_ID # Session state

# End session
curl -X POST http://localhost:8005/v1/sessions/$SESSION_ID/end
```

## Performance Benchmarks

**Baseline Performance Targets**:
- Session initialization: < 2000ms
- Event generation: < 1000ms
- Action processing: < 1500ms
- Parallel action processing (2 actions): < 2000ms
- Session state query: < 200ms

**Load Testing**:
```bash
# Test concurrent sessions
for i in {1..5}; do
  curl -X POST http://localhost:8005/v1/sessions \
    -H "Content-Type: application/json" \
    -d "{\"game_name\": \"Session $i\"}" &
done
wait

# Measure event generation throughput
hey -n 50 -c 5 -m POST \
  -H "Content-Type: application/json" \
  -d '{"context": {...}}' \
  http://localhost:8005/v1/sessions/session_001/generate-event
```

## Common Issues

### Issue: Service orchestration failures
**Check**:
- All dependent services healthy
- Network connectivity between services
- Timeout configurations

### Issue: Event generation quality
**Check**:
- LLM proxy responses
- Lore context retrieval
- Event generation prompts

### Issue: State synchronization
**Check**:
- Redis connectivity
- Service update order
- Transaction handling

### Issue: Performance degradation
**Check**:
- Service response times
- Cache hit rates
- Database query performance

## Success Criteria

- ✅ Health check shows all dependencies healthy
- ✅ Can create and manage sessions
- ✅ Event generation creates contextual, quality events
- ✅ Actions coordinate across all services correctly
- ✅ State remains synchronized across services
- ✅ Parallel actions process correctly
- ✅ Analytics provide meaningful insights
- ✅ Session management (pause/resume/end) works
- ✅ Performance meets targets
- ✅ System handles multiple concurrent sessions
- ✅ Complete integration flow works end-to-end
