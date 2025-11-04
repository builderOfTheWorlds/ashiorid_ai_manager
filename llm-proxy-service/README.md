# LLM Proxy Service

Unified LLM proxy service for Ashiorid AI Manager with multi-provider support, caching, rate limiting, and cost tracking.

## Features

- **Multi-Provider Support**: OpenAI, Anthropic, and Ollama
- **Request Caching**: Redis-based response caching to reduce costs
- **Rate Limiting**: Configurable rate limits per provider
- **Cost Tracking**: Track token usage and costs across providers
- **Request Batching**: Batch similar requests for efficiency
- **Provider Failover**: Automatic failover to backup providers
- **Metrics**: Prometheus metrics for monitoring
- **OpenAI-Compatible API**: Standard `/v1/chat/completions` endpoint

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export OPENAI_API_KEY=your-key-here
export ANTHROPIC_API_KEY=your-key-here
export REDIS_HOST=localhost

# Run the service
uvicorn src.main:app --reload --port 8001
```

### Docker

```bash
# Build image
docker build -t llm-proxy-service .

# Run container
docker run -p 8001:8001 \
  -e OPENAI_API_KEY=your-key \
  -e ANTHROPIC_API_KEY=your-key \
  -e REDIS_HOST=redis \
  llm-proxy-service
```

### Kubernetes

```bash
# Apply manifests
kubectl apply -k k8s/

# Check status
kubectl get pods -n ashiorid -l app=llm-proxy

# View logs
kubectl logs -n ashiorid -l app=llm-proxy -f
```

## API Endpoints

### Chat Completions

OpenAI-compatible endpoint:

```bash
POST /v1/chat/completions
```

Example request:

```json
{
  "messages": [
    {"role": "system", "content": "You are a helpful assistant"},
    {"role": "user", "content": "What is the meaning of life?"}
  ],
  "provider": "ollama",
  "model": "llama3.2:3b",
  "temperature": 0.7,
  "max_tokens": 1000
}
```

### Admin Endpoints

- `GET /providers` - List available providers
- `GET /providers/{provider}/models` - List models for a provider
- `GET /stats` - Service statistics
- `GET /cost/summary` - Cost summary
- `POST /cache/clear` - Clear response cache

### Health & Metrics

- `GET /health` - Basic health check
- `GET /health/detailed` - Detailed health status
- `GET /metrics` - Prometheus metrics

## Configuration

Configuration is managed via `config.yaml` and environment variables.

### Environment Variables

- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic API key
- `OLLAMA_HOST` - Ollama server URL (default: http://host.docker.internal:11434)
- `REDIS_HOST` - Redis host (default: redis)
- `REDIS_PORT` - Redis port (default: 6379)
- `LOG_LEVEL` - Logging level (default: INFO)
- `LOG_FORMAT` - Log format: json or human (default: human)

### Provider Configuration

Edit `config.yaml` to configure providers:

```yaml
providers:
  ollama:
    enabled: true
    base_url: http://localhost:11434
    models:
      - llama3.2:1b
      - llama3.2:3b
    default_model: llama3.2:3b
```

## Cost Tracking

The service tracks token usage and costs for all providers.

View cost summary:

```bash
curl http://localhost:8001/cost/summary
```

Response:

```json
{
  "total_cost_usd": 0.05,
  "by_provider": {
    "openai": 0.03,
    "anthropic": 0.02,
    "ollama": 0.00
  },
  "by_model": [
    {
      "provider": "openai",
      "model": "gpt-3.5-turbo",
      "prompt_tokens": 1000,
      "completion_tokens": 500,
      "total_tokens": 1500,
      "cost_usd": 0.03
    }
  ]
}
```

## Caching

Responses are cached in Redis to reduce costs and latency.

- **TTL**: 1 hour (configurable)
- **Cache Key**: SHA256 hash of request parameters
- **Cache Hit Rate**: Available in `/stats` endpoint

Clear cache:

```bash
curl -X POST http://localhost:8001/cache/clear
```

## Monitoring

Prometheus metrics are exposed at `/metrics`:

- `llm_proxy_requests_total` - Total requests by provider/model/status
- `llm_proxy_request_duration_seconds` - Request latency histogram
- `llm_proxy_tokens_total` - Token usage counter
- `llm_proxy_cost_total` - Cost tracking counter

## Testing

```bash
# Run unit tests
pytest tests/unit/

# Run integration tests (requires running service)
pytest tests/integration/

# Run with coverage
pytest --cov=src tests/
```

## Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       v
┌─────────────────────────────────────┐
│       LLM Proxy Service             │
│                                     │
│  ┌─────────────┐  ┌──────────────┐ │
│  │Rate Limiter │  │    Cache     │ │
│  └─────────────┘  │   (Redis)    │ │
│                   └──────────────┘ │
│  ┌─────────────────────────────┐  │
│  │   Provider Router           │  │
│  └─────────────────────────────┘  │
│    │        │         │            │
│    v        v         v            │
│ ┌─────┐ ┌──────┐ ┌───────┐        │
│ │OpenAI│ │Claude│ │Ollama│        │
│ └─────┘ └──────┘ └───────┘        │
└─────────────────────────────────────┘
```

## Troubleshooting

### Provider Connection Errors

Check provider health:

```bash
curl http://localhost:8001/health/detailed
```

### Cache Issues

Verify Redis connection:

```bash
redis-cli -h localhost ping
```

### High Costs

Monitor cost summary and adjust caching:

```bash
curl http://localhost:8001/cost/summary
```

## License

MIT License - see LICENSE file for details.
