# LLM Proxy Service Testing Instructions

## Service Overview

**Port**: 8001
**Purpose**: Proxies requests to multiple LLM providers (OpenAI, Anthropic, local models)
**Dependencies**: Redis (for caching)

## Prerequisites

```bash
# Ensure service is running
kubectl get pods -n ashiorid | grep llm-proxy

# Check logs
kubectl logs -n ashiorid -l app=llm-proxy --tail=50

# Verify Redis connection
kubectl get pods -n ashiorid | grep redis
```

## Test 1: Health Check

**Purpose**: Verify service is up and responding

```bash
curl http://localhost:8001/health
```

**Expected Response**:
```json
{
  "status": "healthy",
  "service": "llm-proxy",
  "version": "1.0.0"
}
```

## Test 2: List Available Models

**Purpose**: Verify LLM provider configuration

```bash
curl http://localhost:8001/v1/models
```

**Expected Response**:
```json
{
  "data": [
    {
      "id": "gpt-4",
      "provider": "openai",
      "available": true
    },
    {
      "id": "claude-3-opus",
      "provider": "anthropic",
      "available": true
    }
  ]
}
```

## Test 3: Simple Completion Request

**Purpose**: Test basic LLM interaction

```bash
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {
        "role": "user",
        "content": "Say hello world"
      }
    ],
    "max_tokens": 50
  }'
```

**Expected Response**:
```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "gpt-3.5-turbo",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello, World!"
      },
      "finish_reason": "stop"
    }
  ]
}
```

## Test 4: Caching Behavior

**Purpose**: Verify Redis caching works

```bash
# First request (cache miss - slower)
time curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Test caching"}],
    "max_tokens": 20
  }'

# Second identical request (cache hit - faster)
time curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Test caching"}],
    "max_tokens": 20
  }'
```

**Expected Behavior**: Second request should be significantly faster

## Test 5: Streaming Response

**Purpose**: Test streaming completions

```bash
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Count to 5"}],
    "stream": true
  }'
```

**Expected Response**: Stream of SSE events

## Test 6: Error Handling - Invalid Model

**Purpose**: Verify proper error responses

```bash
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "invalid-model",
    "messages": [{"role": "user", "content": "test"}]
  }'
```

**Expected Response**:
```json
{
  "error": {
    "message": "Model not found: invalid-model",
    "type": "invalid_request_error",
    "code": "model_not_found"
  }
}
```

## Test 7: Rate Limiting

**Purpose**: Verify rate limiting works

```bash
# Send multiple rapid requests
for i in {1..10}; do
  curl -X POST http://localhost:8001/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": "test"}]}'
  echo "Request $i"
done
```

**Expected Behavior**: Should eventually get 429 Too Many Requests

## Test 8: Metrics Endpoint

**Purpose**: Verify Prometheus metrics

```bash
curl http://localhost:8001/metrics
```

**Expected Response**: Prometheus-formatted metrics including:
- `llm_proxy_requests_total`
- `llm_proxy_cache_hits`
- `llm_proxy_cache_misses`
- `llm_proxy_latency_seconds`

## Test 9: Provider Fallback

**Purpose**: Test automatic fallback to secondary provider

```bash
# This requires configuring primary provider to fail
# Test instructions depend on your configuration
```

## Integration Tests

### Test with Character Agent Service

```bash
# This will be tested in 03-character-agent-service.md
# The character agent should successfully call LLM proxy
```

## Performance Benchmarks

**Baseline Performance Targets**:
- Health check: < 10ms
- Cached response: < 50ms
- Uncached response: < 2000ms (depends on LLM provider)
- Throughput: > 100 requests/second (cached)

**Load Testing**:
```bash
# Install hey if not available: go install github.com/rakyll/hey@latest
hey -n 1000 -c 10 -m POST \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": "test"}]}' \
  http://localhost:8001/v1/chat/completions
```

## Common Issues

### Issue: Service won't start
**Check**:
- Redis is running
- API keys are configured in secrets
- No module import errors

### Issue: Slow responses
**Check**:
- Redis connection
- LLM provider API status
- Network connectivity

### Issue: Cache not working
**Check**:
- Redis connection
- Cache key generation
- TTL configuration

## Success Criteria

- ✅ All health checks pass
- ✅ Can list available models
- ✅ Successful completion requests
- ✅ Caching reduces latency on repeated requests
- ✅ Streaming works properly
- ✅ Proper error handling
- ✅ Metrics are exposed
- ✅ Rate limiting functions correctly
