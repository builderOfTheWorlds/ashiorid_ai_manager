# Lore RAG Service Testing Instructions

## Service Overview

**Port**: 8002
**Purpose**: Manages lore retrieval using RAG (Retrieval Augmented Generation) with vector embeddings
**Dependencies**: Qdrant (vector database), Redis (caching)

## Prerequisites

```bash
# Ensure service is running
kubectl get pods -n ashiorid | grep lore-rag

# Check logs
kubectl logs -n ashiorid -l app=lore-rag --tail=50

# Verify Qdrant connection
kubectl get pods -n ashiorid | grep qdrant

# Check Qdrant UI
open http://localhost:6333/dashboard
```

## Test 1: Health Check

**Purpose**: Verify service is up and responding

```bash
curl http://localhost:8002/health
```

**Expected Response**:
```json
{
  "status": "healthy",
  "service": "lore-rag",
  "qdrant_connected": true,
  "collections": ["lore_embeddings"]
}
```

## Test 2: List Collections

**Purpose**: Verify Qdrant collections are initialized

```bash
curl http://localhost:8002/v1/collections
```

**Expected Response**:
```json
{
  "collections": [
    {
      "name": "lore_embeddings",
      "vectors_count": 0,
      "status": "green"
    }
  ]
}
```

## Test 3: Ingest Lore Document

**Purpose**: Test document ingestion and embedding

```bash
curl -X POST http://localhost:8002/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "document": {
      "id": "lore_001",
      "title": "The Ancient Kingdom",
      "content": "Long ago, in the kingdom of Eldoria, there lived a wise king who ruled with justice and compassion. The kingdom was known for its magical forests and crystal rivers.",
      "category": "history",
      "tags": ["eldoria", "kingdom", "magic"],
      "metadata": {
        "author": "Elder Scribe",
        "date": "Age of Legends"
      }
    }
  }'
```

**Expected Response**:
```json
{
  "status": "success",
  "document_id": "lore_001",
  "vectors_created": 3,
  "chunks": 1
}
```

## Test 4: Search Lore by Query

**Purpose**: Test semantic search functionality

```bash
curl -X POST http://localhost:8002/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Tell me about magical kingdoms",
    "limit": 5,
    "threshold": 0.7
  }'
```

**Expected Response**:
```json
{
  "results": [
    {
      "id": "lore_001",
      "title": "The Ancient Kingdom",
      "content": "Long ago, in the kingdom of Eldoria...",
      "score": 0.89,
      "metadata": {
        "category": "history",
        "tags": ["eldoria", "kingdom", "magic"]
      }
    }
  ],
  "query_time_ms": 45
}
```

## Test 5: Contextual Retrieval for Character

**Purpose**: Get relevant lore for a specific character context

```bash
curl -X POST http://localhost:8002/v1/context \
  -H "Content-Type: application/json" \
  -d '{
    "character_id": "char_warrior_001",
    "current_location": "Eldoria Castle",
    "recent_events": ["entered_throne_room", "met_king"],
    "max_results": 3
  }'
```

**Expected Response**:
```json
{
  "context": [
    {
      "relevance": "location",
      "content": "Eldoria Castle stands as a symbol...",
      "score": 0.92
    },
    {
      "relevance": "character",
      "content": "The king of Eldoria is known for...",
      "score": 0.87
    }
  ]
}
```

## Test 6: Batch Ingestion

**Purpose**: Test bulk lore import

```bash
curl -X POST http://localhost:8002/v1/ingest/batch \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {
        "id": "lore_002",
        "title": "The Dark Forest",
        "content": "Beyond the kingdom lies the Dark Forest...",
        "category": "location"
      },
      {
        "id": "lore_003",
        "title": "The Crystal Caves",
        "content": "Deep beneath the mountains...",
        "category": "location"
      }
    ]
  }'
```

**Expected Response**:
```json
{
  "status": "success",
  "total": 2,
  "succeeded": 2,
  "failed": 0,
  "processing_time_ms": 234
}
```

## Test 7: Update Lore Document

**Purpose**: Test document updates

```bash
curl -X PUT http://localhost:8002/v1/lore/lore_001 \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Updated content about Eldoria...",
    "metadata": {
      "last_updated": "2024-11-07"
    }
  }'
```

**Expected Response**:
```json
{
  "status": "updated",
  "document_id": "lore_001",
  "vectors_updated": 3
}
```

## Test 8: Delete Lore Document

**Purpose**: Test document deletion

```bash
curl -X DELETE http://localhost:8002/v1/lore/lore_001
```

**Expected Response**:
```json
{
  "status": "deleted",
  "document_id": "lore_001"
}
```

## Test 9: Filter by Category

**Purpose**: Test category-based filtering

```bash
curl -X POST http://localhost:8002/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "ancient places",
    "filters": {
      "category": ["location", "history"]
    },
    "limit": 10
  }'
```

## Test 10: Embedding Quality Check

**Purpose**: Verify embeddings are semantically meaningful

```bash
# Test that semantically similar queries return similar results
curl -X POST http://localhost:8002/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "magical realm"}'

curl -X POST http://localhost:8002/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "enchanted kingdom"}'
```

**Expected**: Both should return similar top results

## Test 11: NLTK Functionality

**Purpose**: Verify text processing works

```bash
curl -X POST http://localhost:8002/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "text": "The brave knight ventured into the dark forest seeking the legendary sword."
  }'
```

**Expected Response**:
```json
{
  "tokens": 12,
  "sentences": 1,
  "keywords": ["brave", "knight", "dark", "forest", "legendary", "sword"],
  "entities": ["knight", "forest", "sword"]
}
```

## Integration Tests

### Test with Character Agent

```bash
# Verify character agent can retrieve lore context
# This will be tested in 03-character-agent-service.md
```

## Performance Benchmarks

**Baseline Performance Targets**:
- Health check: < 10ms
- Single search: < 100ms
- Batch ingestion (10 docs): < 1000ms
- Embedding generation: < 200ms per document

**Load Testing**:
```bash
# Search load test
hey -n 100 -c 5 -m POST \
  -H "Content-Type: application/json" \
  -d '{"query": "test search", "limit": 5}' \
  http://localhost:8002/v1/search
```

## Common Issues

### Issue: Qdrant connection failed
**Check**:
- Qdrant pod is running
- Network connectivity
- Collection initialization

### Issue: Slow search responses
**Check**:
- Index status in Qdrant
- Vector dimension configuration
- Number of vectors in collection

### Issue: Poor search relevance
**Check**:
- Embedding model configuration
- Query preprocessing
- Similarity threshold settings

### Issue: NLTK data not found
**Check**:
- NLTK data downloaded in Docker image
- Python import errors
- File permissions

## Success Criteria

- ✅ Health check passes with Qdrant connection
- ✅ Can create collections
- ✅ Successfully ingest documents
- ✅ Semantic search returns relevant results
- ✅ Batch operations work efficiently
- ✅ Context retrieval works for characters
- ✅ NLTK processing works correctly
- ✅ Update and delete operations function
- ✅ Performance meets targets
- ✅ No memory leaks during extended operation
