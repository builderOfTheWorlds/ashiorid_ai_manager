# Development Guide

Complete guide for developing on the Ashiorid AI Manager project.

## Prerequisites

- **WSL2** or Linux
- **Docker** 20.10+
- **Python** 3.11+
- **K3s** (installed via setup script)
- **Ollama** (for local LLM models)
- **Git**

## Quick Start

### 1. Clone and Bootstrap

```bash
git clone https://github.com/builderOfTheWorlds/ashiorid_ai_manager.git
cd ashiorid_ai_manager

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env

# Run bootstrap script
chmod +x scripts/bootstrap.sh
./scripts/bootstrap.sh
```

### 2. Start Development Environment

**Option A: With Tilt (Recommended)**

```bash
tilt up
```

Visit http://localhost:10350 for the Tilt dashboard.

**Option B: With Docker Compose**

```bash
docker-compose up -d
```

**Option C: Local Services**

```bash
# Start infrastructure
docker-compose up postgres redis qdrant -d

# Run service locally
cd llm-proxy-service
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8001
```

### 3. Monitor with CLI Dashboard

```bash
python cli-dashboard/dashboard.py
```

## Project Structure

```
ashiorid_ai_manager/
├── .github/workflows/     # CI/CD pipelines
├── docs/                  # Documentation
├── k8s/                   # Kubernetes manifests
│   ├── base/             # Infrastructure
│   ├── monitoring/       # Prometheus + Grafana
│   └── apps/             # Service manifests
├── scripts/               # Setup and utility scripts
├── shared/                # Shared Python utilities
├── llm-proxy-service/    # LLM proxy microservice
├── lore-rag-service/     # RAG service (TODO)
├── character-agent-service/ # Character agents (TODO)
├── simulation-engine/    # Agent simulation (TODO)
├── ai-manager-service/   # Master orchestrator (TODO)
└── cli-dashboard/        # Monitoring dashboard
```

## Development Workflow

### Creating a New Service

1. **Create service directory**:
```bash
mkdir my-service
cd my-service
```

2. **Create structure**:
```bash
mkdir -p {src/{api,models,services,utils},k8s,tests/{unit,integration}}
```

3. **Add required files**:
- `requirements.txt` - Dependencies
- `Dockerfile` - Container image
- `config.yaml` - Configuration
- `README.md` - Documentation
- `k8s/deployment.yaml` - K8s deployment
- `k8s/service.yaml` - K8s service
- `k8s/configmap.yaml` - Configuration

4. **Implement service**:
```python
# src/main.py
from fastapi import FastAPI
from shared.logging_config import setup_logging, get_logger
from shared.base_config import load_service_config

app = FastAPI(title="My Service")

@app.on_event("startup")
async def startup():
    config = load_service_config("my-service")
    setup_logging("my-service")
    logger = get_logger("my-service")
    logger.info("Service starting")

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "my-service"}
```

5. **Add to Tiltfile**:
```python
docker_build(
    'ghcr.io/builderoftheworlds/my-service',
    'my-service',
    live_update=[
        sync('my-service/src', '/app/src'),
    ],
)
k8s_yaml('my-service/k8s/')
k8s_resource('my-service', port_forwards='8006:8006')
```

6. **Test**:
```bash
cd my-service
pytest tests/
```

### Making Changes

1. **Create feature branch**:
```bash
git checkout -b feature/my-feature
```

2. **Make changes** with hot-reload via Tilt

3. **Run tests**:
```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# With coverage
pytest --cov=src tests/
```

4. **Lint code**:
```bash
black .
flake8 .
isort .
```

5. **Commit and push**:
```bash
git add .
git commit -m "Add my feature"
git push origin feature/my-feature
```

6. **Create Pull Request** on GitHub

### Testing Strategy

**Unit Tests**
- Test individual functions and classes
- Mock external dependencies
- Fast execution

**Integration Tests**
- Test service APIs
- Use test containers or mocks
- Verify inter-service communication

**End-to-End Tests**
- Full workflow testing
- All services running
- Real dependencies

Example test:
```python
import pytest
from httpx import AsyncClient
from src.main import app

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
```

## Debugging

### View Logs

**Tilt UI**: http://localhost:10350 - Click on service for logs

**Kubernetes**:
```bash
kubectl logs -n ashiorid -l app=llm-proxy -f
```

**Docker Compose**:
```bash
docker-compose logs -f llm-proxy
```

### Access Services

**Port Forwarding**:
```bash
kubectl port-forward -n ashiorid svc/llm-proxy 8001:8001
```

**Exec into Pod**:
```bash
kubectl exec -it -n ashiorid deployment/llm-proxy -- /bin/bash
```

### Check Service Health

```bash
# LLM Proxy
curl http://localhost:8001/health

# Detailed health
curl http://localhost:8001/health/detailed

# Service stats
curl http://localhost:8001/stats
```

### Database Access

**PostgreSQL**:
```bash
kubectl exec -it -n ashiorid deployment/postgres -- psql -U ashiorid_user -d ashiorid
```

**Redis**:
```bash
kubectl exec -it -n ashiorid deployment/redis -- redis-cli
```

**Qdrant**:
```bash
curl http://localhost:6333/collections
```

## Common Tasks

### Update Dependencies

```bash
cd my-service
pip install -r requirements.txt
pip freeze > requirements.txt
```

### Reset Database

```bash
kubectl delete pvc -n ashiorid postgres-pvc
kubectl delete pod -n ashiorid -l app=postgres
```

### Clear Redis Cache

```bash
kubectl exec -n ashiorid deployment/redis -- redis-cli FLUSHALL
```

### View Prometheus Metrics

```bash
curl http://localhost:8001/metrics
```

### Backup Data

```bash
./scripts/backup.sh
```

### Deploy to K8s

```bash
# Apply infrastructure
kubectl apply -k k8s/base/

# Apply monitoring
kubectl apply -k k8s/monitoring/

# Apply services
kubectl apply -k llm-proxy-service/k8s/
```

## Configuration

### Environment Variables

All services support environment-based configuration:

```bash
export LOG_LEVEL=DEBUG
export LOG_FORMAT=json
export REDIS_HOST=localhost
export POSTGRES_HOST=localhost
```

### YAML Configuration

Each service has a `config.yaml`:

```yaml
service:
  name: my-service
  port: 8000

database:
  host: postgres
  port: 5432
```

### Kubernetes ConfigMaps

Configuration via ConfigMaps:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-service-config
data:
  config.yaml: |
    service:
      port: 8000
```

## CI/CD Pipeline

GitHub Actions automatically:

1. **On Push to `main`/`develop`**:
   - Run linters (black, flake8)
   - Run tests for all services
   - Build Docker images
   - Push to ghcr.io
   - Deploy to dev environment

2. **On Pull Request**:
   - Run tests
   - Build images (no push)
   - Report coverage

3. **On Tag (`v*`)**:
   - Create GitHub release
   - Build production images
   - Tag as `latest`

## Best Practices

### Code Style

- **Black** for formatting
- **Type hints** for function signatures
- **Docstrings** for public functions
- **Async/await** for I/O operations

### Error Handling

```python
from shared.logging_config import get_logger

logger = get_logger(__name__)

try:
    result = await some_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail=str(e))
```

### Logging

```python
logger.debug("Detailed information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred", exc_info=True)
```

### Configuration

```python
from shared.base_config import load_service_config, get_env

config = load_service_config("my-service")
api_key = get_env("API_KEY", required=True)
port = get_env("PORT", default=8000, value_type=int)
```

### API Endpoints

```python
@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/items", response_model=Item)
async def create_item(item: ItemCreate):
    # Implementation
    return created_item
```

## Troubleshooting

### Service Won't Start

1. Check logs: `kubectl logs -n ashiorid deployment/my-service`
2. Verify environment variables
3. Check dependencies are running
4. Verify port not in use

### Database Connection Error

1. Check database is running: `kubectl get pods -n ashiorid`
2. Verify connection string
3. Check network policies
4. Test connection: `pg_isready -h localhost -p 5432`

### High Memory Usage

1. Check resource limits in deployment
2. Review memory leaks in code
3. Monitor with Prometheus
4. Adjust limits if needed

### Slow Performance

1. Check Prometheus metrics
2. Review database queries
3. Verify cache hit rates
4. Check network latency

## Getting Help

- **Documentation**: https://github.com/builderOfTheWorlds/ashiorid_ai_manager/docs
- **Issues**: https://github.com/builderOfTheWorlds/ashiorid_ai_manager/issues
- **Discussions**: https://github.com/builderOfTheWorlds/ashiorid_ai_manager/discussions

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed contribution guidelines.

Quick checklist:
- [ ] Tests pass
- [ ] Code is linted
- [ ] Documentation updated
- [ ] Commit messages are clear
- [ ] PR description explains changes
