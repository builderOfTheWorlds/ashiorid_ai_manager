# Tiltfile for Ashiorid AI Manager
# Development workflow with hot-reload

# Allow K8s contexts (configure for your setup)
allow_k8s_contexts('k3d-ashiorid')

# Load environment variables
load('ext://dotenv', 'dotenv')
dotenv()

# =================================================================
# Infrastructure Services
# =================================================================

# Deploy base infrastructure
k8s_yaml([
    'k8s/base/namespace.yaml',
    'k8s/base/postgres.yaml',
    'k8s/base/redis.yaml',
    'k8s/base/qdrant.yaml',
    'k8s/base/traefik.yaml',
])

# Deploy monitoring stack
k8s_yaml([
    'k8s/monitoring/prometheus.yaml',
    'k8s/monitoring/grafana.yaml',
])

# Wait for infrastructure to be ready
k8s_resource('postgres', port_forwards='5432:5432')
k8s_resource('redis', port_forwards='6379:6379')
k8s_resource('qdrant', port_forwards=['6333:6333', '6334:6334'])
k8s_resource('prometheus', port_forwards='9090:9090')
k8s_resource('grafana', port_forwards='3000:3000')
k8s_resource('traefik', port_forwards=['80:80', '8080:8080'])

# =================================================================
# LLM Proxy Service
# =================================================================

# Build Docker image
docker_build(
    'ghcr.io/builderoftheworlds/llm-proxy-service',
    'llm-proxy-service',
    live_update=[
        sync('llm-proxy-service/src', '/app/src'),
        sync('llm-proxy-service/config.yaml', '/app/config.yaml'),
        run('pip install -r requirements.txt', trigger='llm-proxy-service/requirements.txt'),
    ],
)

# Deploy to K8s
k8s_yaml('llm-proxy-service/k8s/')
k8s_resource(
    'llm-proxy',
    port_forwards='8001:8001',
    resource_deps=['redis'],
    labels=['services'],
)

# =================================================================
# Lore RAG Service
# =================================================================

docker_build(
    'ghcr.io/builderoftheworlds/lore-rag-service',
    'lore-rag-service',
    live_update=[
        sync('lore-rag-service/src', '/app/src'),
        sync('lore-rag-service/config.yaml', '/app/config.yaml'),
        run('pip install -r requirements.txt', trigger='lore-rag-service/requirements.txt'),
    ],
)

k8s_yaml('lore-rag-service/k8s/')
k8s_resource(
    'lore-rag',
    port_forwards='8002:8002',
    resource_deps=['qdrant', 'redis'],
    labels=['services'],
)

# =================================================================
# Character Agent Service
# =================================================================

docker_build(
    'ghcr.io/builderoftheworlds/character-agent-service',
    'character-agent-service',
    live_update=[
        sync('character-agent-service/src', '/app/src'),
        sync('character-agent-service/config.yaml', '/app/config.yaml'),
        run('pip install -r requirements.txt', trigger='character-agent-service/requirements.txt'),
    ],
)

k8s_yaml('character-agent-service/k8s/')
k8s_resource(
    'character-agent',
    port_forwards='8003:8003',
    resource_deps=['postgres', 'llm-proxy', 'lore-rag'],
    labels=['services'],
)

# =================================================================
# Simulation Engine
# =================================================================

docker_build(
    'ghcr.io/builderoftheworlds/simulation-engine',
    'simulation-engine',
    live_update=[
        sync('simulation-engine/src', '/app/src'),
        sync('simulation-engine/config.yaml', '/app/config.yaml'),
        run('pip install -r requirements.txt', trigger='simulation-engine/requirements.txt'),
    ],
)

k8s_yaml('simulation-engine/k8s/')
k8s_resource(
    'simulation-engine',
    port_forwards='8004:8004',
    resource_deps=['postgres', 'redis'],
    labels=['services'],
)

# =================================================================
# AI Manager Service
# =================================================================

docker_build(
    'ghcr.io/builderoftheworlds/ai-manager-service',
    'ai-manager-service',
    live_update=[
        sync('ai-manager-service/src', '/app/src'),
        sync('ai-manager-service/config.yaml', '/app/config.yaml'),
        run('pip install -r requirements.txt', trigger='ai-manager-service/requirements.txt'),
    ],
)

k8s_yaml('ai-manager-service/k8s/')
k8s_resource(
    'ai-manager',
    port_forwards='8005:8005',
    resource_deps=['redis', 'llm-proxy', 'lore-rag', 'character-agent', 'simulation-engine'],
    labels=['services'],
)

# =================================================================
# Local Scripts and Tools
# =================================================================

# CLI Dashboard (run locally, not in K8s)
local_resource(
    'cli-dashboard',
    serve_cmd='python cli-dashboard/dashboard.py',
    deps=['cli-dashboard/dashboard.py'],
    labels=['tools'],
)

# =================================================================
# Development Helpers
# =================================================================

# Print helpful URLs
print("""
🌍 Ashiorid AI Manager - Tilt Development Environment

📊 Dashboards:
  • Tilt UI:       http://localhost:10350
  • Grafana:       http://localhost:3000 (admin/admin)
  • Prometheus:    http://localhost:9090
  • Traefik:       http://localhost:8080
  • Qdrant UI:     http://localhost:6333/dashboard

🚀 Services:
  • LLM Proxy:        http://localhost:8001
  • Lore RAG:         http://localhost:8002
  • Character Agent:  http://localhost:8003
  • Simulation:       http://localhost:8004
  • AI Manager:       http://localhost:8005

💾 Databases:
  • PostgreSQL:    localhost:5432
  • Redis:         localhost:6379
  • Qdrant:        localhost:6333

⚡ Hot-reload is enabled for all services!
Press 'space' in Tilt UI to trigger manual builds
""")
