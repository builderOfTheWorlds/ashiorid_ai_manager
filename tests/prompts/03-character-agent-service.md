# Character Agent Service Testing Instructions

## Service Overview

**Port**: 8003
**Purpose**: Manages AI-driven character agents with personality, memory, and decision-making
**Dependencies**: PostgreSQL (persistence), LLM Proxy (AI), Lore RAG (context)

## Prerequisites

```bash
# Ensure service is running
kubectl get pods -n ashiorid | grep character-agent

# Check logs
kubectl logs -n ashiorid -l app=character-agent --tail=50

# Verify dependencies
kubectl get pods -n ashiorid | grep -E "postgres|llm-proxy|lore-rag"

# Check database
kubectl exec -it -n ashiorid $(kubectl get pod -n ashiorid -l app=postgres -o name) -- psql -U ashiorid_user -d ashiorid -c "\dt"
```

## Test 1: Health Check

**Purpose**: Verify service is up with all dependencies

```bash
curl http://localhost:8003/health
```

**Expected Response**:
```json
{
  "status": "healthy",
  "service": "character-agent",
  "database_connected": true,
  "llm_proxy_available": true,
  "lore_rag_available": true
}
```

## Test 2: Create Character

**Purpose**: Test character creation with personality

```bash
curl -X POST http://localhost:8003/v1/characters \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Aldric the Brave",
    "race": "Human",
    "class": "Warrior",
    "personality": {
      "traits": ["brave", "honorable", "loyal"],
      "voice_style": "formal and respectful",
      "motivations": ["protect the innocent", "uphold justice"],
      "fears": ["betrayal", "failing his duty"]
    },
    "backstory": "A knight sworn to protect the realm of Eldoria",
    "current_location": "Eldoria Castle",
    "level": 5
  }'
```

**Expected Response**:
```json
{
  "character_id": "char_001",
  "name": "Aldric the Brave",
  "status": "created",
  "agent_initialized": true
}
```

## Test 3: Get Character Details

**Purpose**: Retrieve character information

```bash
curl http://localhost:8003/v1/characters/char_001
```

**Expected Response**:
```json
{
  "character_id": "char_001",
  "name": "Aldric the Brave",
  "race": "Human",
  "class": "Warrior",
  "level": 5,
  "personality": {
    "traits": ["brave", "honorable", "loyal"],
    "voice_style": "formal and respectful"
  },
  "current_location": "Eldoria Castle",
  "state": "idle",
  "created_at": "2024-11-07T12:00:00Z"
}
```

## Test 4: Character Dialogue

**Purpose**: Test AI-driven conversation

```bash
curl -X POST http://localhost:8003/v1/characters/char_001/dialogue \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Tell me about your duties as a knight.",
    "context": {
      "location": "Eldoria Castle",
      "time": "afternoon"
    }
  }'
```

**Expected Response**:
```json
{
  "character_id": "char_001",
  "response": "It is my sacred duty to protect the citizens of Eldoria and uphold the laws of our kingdom. I have sworn an oath to serve with honor and courage, no matter the peril.",
  "emotion": "proud",
  "action": null
}
```

## Test 5: Character Decision Making

**Purpose**: Test AI-driven decisions based on situation

```bash
curl -X POST http://localhost:8003/v1/characters/char_001/decide \
  -H "Content-Type: application/json" \
  -d '{
    "situation": "You encounter a group of bandits threatening a merchant.",
    "options": [
      {
        "id": "option_1",
        "action": "Attack the bandits immediately",
        "risk": "high"
      },
      {
        "id": "option_2",
        "action": "Try to negotiate with the bandits",
        "risk": "medium"
      },
      {
        "id": "option_3",
        "action": "Call for backup",
        "risk": "low"
      }
    ],
    "lore_context": true
  }'
```

**Expected Response**:
```json
{
  "character_id": "char_001",
  "chosen_option": "option_1",
  "reasoning": "As a sworn protector, I cannot stand idle while innocents are threatened. My duty and honor demand immediate action.",
  "confidence": 0.85
}
```

## Test 6: Update Character State

**Purpose**: Update character's current state

```bash
curl -X PATCH http://localhost:8003/v1/characters/char_001/state \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Dark Forest",
    "state": "in_combat",
    "health": 75,
    "conditions": ["wounded"]
  }'
```

**Expected Response**:
```json
{
  "character_id": "char_001",
  "state_updated": true,
  "current_state": {
    "location": "Dark Forest",
    "state": "in_combat",
    "health": 75,
    "conditions": ["wounded"]
  }
}
```

## Test 7: Character Memory System

**Purpose**: Test memory storage and recall

```bash
# Add memory
curl -X POST http://localhost:8003/v1/characters/char_001/memory \
  -H "Content-Type: application/json" \
  -d '{
    "event": "Defeated bandits in the Dark Forest",
    "importance": "high",
    "emotions": ["satisfaction", "relief"],
    "participants": ["bandits", "merchant"]
  }'

# Recall memories
curl http://localhost:8003/v1/characters/char_001/memory?limit=10
```

**Expected Response**:
```json
{
  "memories": [
    {
      "id": "mem_001",
      "event": "Defeated bandits in the Dark Forest",
      "timestamp": "2024-11-07T12:30:00Z",
      "importance": "high",
      "emotions": ["satisfaction", "relief"]
    }
  ]
}
```

## Test 8: Conversation History

**Purpose**: Retrieve conversation history

```bash
curl http://localhost:8003/v1/characters/char_001/conversations?limit=5
```

**Expected Response**:
```json
{
  "conversations": [
    {
      "id": "conv_001",
      "timestamp": "2024-11-07T12:00:00Z",
      "message": "Tell me about your duties as a knight.",
      "response": "It is my sacred duty...",
      "context": {"location": "Eldoria Castle"}
    }
  ]
}
```

## Test 9: List All Characters

**Purpose**: Get all characters in system

```bash
curl http://localhost:8003/v1/characters?limit=20
```

**Expected Response**:
```json
{
  "characters": [
    {
      "character_id": "char_001",
      "name": "Aldric the Brave",
      "race": "Human",
      "class": "Warrior",
      "level": 5
    }
  ],
  "total": 1
}
```

## Test 10: Character Action Planning

**Purpose**: Test multi-step action planning

```bash
curl -X POST http://localhost:8003/v1/characters/char_001/plan \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "Investigate reports of monsters in the Dark Forest",
    "constraints": ["must return by nightfall", "low on supplies"],
    "available_resources": ["sword", "basic armor", "healing potion"]
  }'
```

**Expected Response**:
```json
{
  "plan": {
    "steps": [
      {"order": 1, "action": "Gather information from local villagers", "estimated_time": "30 minutes"},
      {"order": 2, "action": "Travel to Dark Forest entrance", "estimated_time": "1 hour"},
      {"order": 3, "action": "Scout the forest perimeter", "estimated_time": "2 hours"},
      {"order": 4, "action": "Return to report findings", "estimated_time": "1 hour"}
    ],
    "total_estimated_time": "4.5 hours",
    "risk_assessment": "medium",
    "success_probability": 0.75
  }
}
```

## Test 11: Delete Character

**Purpose**: Test character deletion

```bash
curl -X DELETE http://localhost:8003/v1/characters/char_001
```

**Expected Response**:
```json
{
  "status": "deleted",
  "character_id": "char_001"
}
```

## Integration Tests

### Test with LLM Proxy

```bash
# Verify dialogue uses LLM proxy
# Check llm-proxy logs while making dialogue request
kubectl logs -n ashiorid -l app=llm-proxy --tail=20 -f &
curl -X POST http://localhost:8003/v1/characters/char_001/dialogue \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'
```

### Test with Lore RAG

```bash
# Verify decisions use lore context
# Check lore-rag logs while making decision
kubectl logs -n ashiorid -l app=lore-rag --tail=20 -f &
curl -X POST http://localhost:8003/v1/characters/char_001/decide \
  -H "Content-Type: application/json" \
  -d '{"situation": "test", "options": [...], "lore_context": true}'
```

## Performance Benchmarks

**Baseline Performance Targets**:
- Character creation: < 500ms
- Dialogue response (without LLM): < 100ms
- Dialogue response (with LLM): < 2000ms
- Decision making: < 3000ms
- State updates: < 50ms
- Memory queries: < 100ms

## Common Issues

### Issue: Database connection errors
**Check**:
- PostgreSQL is running
- Database migrations completed
- Connection credentials correct

### Issue: LLM responses timeout
**Check**:
- LLM proxy service status
- API key configuration
- Network connectivity

### Issue: Poor character consistency
**Check**:
- Personality configuration
- Memory system working
- Lore context retrieval

### Issue: Slow response times
**Check**:
- Database query optimization
- LLM caching in proxy
- Connection pooling

## Success Criteria

- ✅ Health check passes with all dependencies
- ✅ Can create characters with personalities
- ✅ Characters respond in-character
- ✅ Decision-making reflects personality
- ✅ Memory system stores and recalls events
- ✅ Conversation history persists
- ✅ Integration with LLM proxy works
- ✅ Integration with lore RAG works
- ✅ Performance meets targets
- ✅ Database persistence works correctly
