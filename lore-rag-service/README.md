# Lore RAG Service

Semantic search service for Ashiorid AI Manager providing retrieval-augmented generation over fictional universe knowledge.

## Features

- **Vector Database**: Qdrant integration for efficient similarity search
- **Embeddings**: Ollama nomic-embed-text for generating embeddings
- **Document Ingestion**: Automatic text chunking and vectorization
- **Semantic Search**: Find relevant lore passages by semantic similarity
- **Collection Management**: Organize knowledge by universe/topic
- **Prometheus Metrics**: Track search performance and usage

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Ensure Qdrant and Ollama are running
docker run -p 6333:6333 qdrant/qdrant
ollama serve

# Pull embedding model
ollama pull nomic-embed-text

# Set environment variables
export QDRANT_HOST=localhost
export OLLAMA_HOST=http://localhost:11434

# Run the service
uvicorn src.main:app --reload --port 8002
```

### Docker

```bash
# Build image
docker build -t lore-rag-service .

# Run container
docker run -p 8002:8002 \
  -e QDRANT_HOST=qdrant \
  -e OLLAMA_HOST=http://host.docker.internal:11434 \
  lore-rag-service
```

### Kubernetes

```bash
# Apply manifests
kubectl apply -k k8s/

# Check status
kubectl get pods -n ashiorid -l app=lore-rag

# View logs
kubectl logs -n ashiorid -l app=lore-rag -f
```

## API Endpoints

### Search

Perform semantic search over lore:

```bash
POST /search
```

Example:

```json
{
  "query": "What would Gandalf do in this situation?",
  "collection": "lotr",
  "limit": 5,
  "threshold": 0.7
}
```

Response:

```json
{
  "results": [
    {
      "text": "Gandalf the Grey was a wizard...",
      "score": 0.92,
      "source": "fellowship_of_the_ring.txt",
      "metadata": {"chapter": 1}
    }
  ],
  "query": "What would Gandalf do...",
  "total_results": 5,
  "latency_ms": 123.45
}
```

### Ingestion

Ingest documents:

```bash
POST /ingest
```

Example:

```json
{
  "documents": [
    {
      "text": "In a hole in the ground there lived a hobbit...",
      "source": "the_hobbit.txt",
      "metadata": {"chapter": 1}
    }
  ],
  "collection": "lotr"
}
```

Upload file:

```bash
POST /ingest/file
```

Example:

```bash
curl -X POST http://localhost:8002/ingest/file \
  -F "file=@lotr_fellowship.txt" \
  -F "collection=lotr" \
  -F "source=fellowship_of_the_ring"
```

### Collection Management

List collections:

```bash
GET /collections
```

Get collection info:

```bash
GET /collections/{collection_name}
```

Create collection:

```bash
POST /collections/{collection_name}?vector_size=768
```

Delete collection:

```bash
DELETE /collections/{collection_name}
```

### Admin Endpoints

- `GET /health` - Basic health check
- `GET /health/detailed` - Detailed component status
- `GET /metrics` - Prometheus metrics
- `GET /stats` - Service statistics

## Configuration

Configuration via `config.yaml` and environment variables:

```yaml
qdrant:
  host: qdrant
  port: 6333
  collections:
    default: lore
    vector_size: 768  # nomic-embed-text dimension
    distance: Cosine

ollama:
  host: http://localhost:11434
  model: nomic-embed-text
  batch_size: 32

text_processing:
  chunk_size: 512  # tokens per chunk
  chunk_overlap: 50
  min_chunk_size: 100

search:
  default_limit: 5
  max_limit: 100
  default_threshold: 0.7
```

### Environment Variables

- `QDRANT_HOST` - Qdrant server host (default: qdrant)
- `QDRANT_PORT` - Qdrant port (default: 6333)
- `OLLAMA_HOST` - Ollama server URL (default: http://localhost:11434)
- `REDIS_HOST` - Redis host for caching (default: redis)
- `LOG_LEVEL` - Logging level (default: INFO)
- `LOG_FORMAT` - Log format: json or human (default: human)

## Text Processing

### Chunking Strategy

Documents are automatically split into chunks for better retrieval:

1. **Token-based Chunking**: Uses tiktoken for precise token counting
2. **Configurable Size**: Default 512 tokens per chunk
3. **Overlap**: 50 tokens overlap between chunks for context
4. **Minimum Size**: Chunks below 100 tokens are filtered out

### Embedding Generation

- **Model**: nomic-embed-text (768 dimensions)
- **Batching**: Process up to 32 texts per batch
- **Caching**: Embeddings can be cached in Redis

## Collection Organization

Recommended collection structure:

```
lotr/          # Lord of the Rings lore
dune/          # Dune universe
halo/          # Halo franchise
harry_potter/  # Harry Potter world
custom/        # User-created lore
```

Each collection can have metadata filters for:
- Source (book, movie, game)
- Chapter/Episode
- Character mentions
- Location
- Time period

## Performance

### Search Performance

- **Latency**: ~50-200ms for typical searches
- **Throughput**: ~50 searches/second (single replica)
- **Scale**: Horizontal scaling via K8s replicas

### Ingestion Performance

- **Embedding Generation**: ~100 documents/minute (Ollama local)
- **Vector Upload**: ~1000 points/second to Qdrant
- **Chunking**: ~10MB text/second

## Monitoring

Prometheus metrics:

- `lore_rag_searches_total` - Total searches by collection/status
- `lore_rag_search_duration_seconds` - Search latency histogram
- `lore_rag_ingestions_total` - Total ingestions by collection/status
- `lore_rag_embeddings_total` - Total embeddings generated

View metrics:

```bash
curl http://localhost:8002/metrics
```

## Example: Building a LOTR Knowledge Base

### 1. Prepare Text Files

```bash
# Download or prepare LOTR texts
mkdir lotr_texts
# fellowship_of_the_ring.txt
# two_towers.txt
# return_of_the_king.txt
```

### 2. Ingest Documents

```bash
# Create collection
curl -X POST http://localhost:8002/collections/lotr

# Ingest files
for file in lotr_texts/*.txt; do
  curl -X POST http://localhost:8002/ingest/file \
    -F "file=@$file" \
    -F "collection=lotr" \
    -F "source=$(basename $file)"
done
```

### 3. Search

```bash
curl -X POST http://localhost:8002/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Tell me about the ring of power",
    "collection": "lotr",
    "limit": 5
  }'
```

### 4. Use in Character Agents

```python
# In character-agent-service
async def get_context(query: str) -> str:
    response = await http_client.post(
        "http://lore-rag:8002/search",
        json={"query": query, "collection": "lotr", "limit": 3}
    )
    results = response.json()["results"]
    return "\n\n".join([r["text"] for r in results])
```

## Testing

```bash
# Run unit tests
pytest tests/unit/

# Run integration tests (requires Qdrant and Ollama)
pytest tests/integration/

# Run with coverage
pytest --cov=src tests/
```

## Troubleshooting

### Qdrant Connection Issues

Check Qdrant is running:

```bash
curl http://localhost:6333/collections
```

### Ollama Embedding Errors

Verify model is pulled:

```bash
ollama list | grep nomic-embed-text
```

Pull if missing:

```bash
ollama pull nomic-embed-text
```

### Slow Search Performance

1. Check Qdrant index size: `GET /collections/{name}`
2. Reduce search limit
3. Increase threshold to reduce results
4. Add horizontal replicas

### Memory Issues

- Reduce batch size in config
- Lower chunk size
- Use pagination for large ingestions

## License

MIT License - see LICENSE file for details.
