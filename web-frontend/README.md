# Web Frontend Service

Streamlit-based web interface for the Ashiorid AI Manager.

## Features

- **World Query Chat**: Interactive chat interface for asking questions about the world
- **Character Query**: Talk to specific characters with simulation context
- **World Events**: View recent events and trigger new ones
- **System Status**: Real-time monitoring of all services and simulation state
- **Multi-locale Support**: Query in multiple languages (EN, ES, FR, DE, JA, ZH)

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set AI Manager URL (optional, defaults to localhost)
export AI_MANAGER_URL=http://localhost:8005

# Run Streamlit
streamlit run app.py
```

The interface will be available at http://localhost:8501

### Docker

```bash
# Build
docker build -t web-frontend:latest .

# Run
docker run -p 8501:8501 \
  -e AI_MANAGER_URL=http://ai-manager-service:8005 \
  web-frontend:latest
```

### Kubernetes

```bash
# Deploy
kubectl apply -k k8s/

# Port forward
kubectl port-forward -n ashiorid svc/web-frontend 8501:8501
```

## Configuration

Edit `config.yaml` to customize:

```yaml
web_frontend:
  title: "Ashiorid AI Manager"
  host: "0.0.0.0"
  port: 8501

ai_manager:
  base_url: "http://ai-manager-service:8005"
  timeout: 30

features:
  enable_world_query: true
  enable_character_query: true
  enable_events: true
  enable_system_status: true

locales:
  - "en-US"
  - "es-ES"
  - "fr-FR"
```

## Environment Variables

- `AI_MANAGER_URL`: Base URL for AI Manager service (default: `http://localhost:8005`)

## Usage

### World Query Tab

Ask questions about your world:
- "What's happening in the world right now?"
- "Tell me about recent events"
- "Describe the current state of the simulation"

Toggle options in sidebar:
- Include Simulation Data
- Include Lore Context
- Change locale/language

### Character Query Tab

Talk to specific characters:
1. Enter character name (e.g., "gandalf")
2. Type your message
3. Get character response with simulation context

### Events Tab

**Recent Events**: View recent world events with descriptions

**Trigger Event**: Manually create new events
- Choose event type (natural disaster, resource discovery, etc.)
- Optional: Add custom description
- Optional: Specify agent IDs and location

### System Status Tab

Monitor system health:
- Overall status indicator
- Individual service health and latency
- Current simulation state (tick, agents)
- Recent world events

## Development

### Project Structure

```
web-frontend/
├── app.py              # Main Streamlit application
├── config.yaml         # Configuration
├── requirements.txt    # Python dependencies
├── Dockerfile          # Container image
├── README.md          # This file
└── k8s/               # Kubernetes manifests
    ├── deployment.yaml
    ├── service.yaml
    ├── configmap.yaml
    └── kustomization.yaml
```

### Adding New Features

The app is organized into render functions:
- `render_world_query_tab()`: Chat interface
- `render_character_query_tab()`: Character queries
- `render_events_tab()`: Event management
- `render_status_tab()`: System monitoring

Add new tabs by creating new render functions and adding to `main()`.

## Troubleshooting

### Cannot connect to AI Manager

1. Check AI_MANAGER_URL environment variable
2. Verify AI Manager service is running
3. Check network connectivity between services
4. Review logs: `kubectl logs -n ashiorid deployment/web-frontend`

### Streamlit errors

1. Check Python version (requires 3.11+)
2. Reinstall dependencies: `pip install -r requirements.txt`
3. Clear Streamlit cache: Delete `.streamlit/` directory

## License

MIT License
