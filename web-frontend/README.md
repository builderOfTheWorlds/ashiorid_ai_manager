# Web Frontend Service

Streamlit-based web interface for the Ashiorid AI Manager.

## Features

- **World Query Chat**: Interactive chat interface for asking questions about the world
- **Character Query**: Talk to specific characters with simulation context
- **World Events**: View recent events and trigger new ones
- **System Status**: Real-time monitoring of all services and simulation state
- **Data Preparation**: Complete GUI for processing source text files into ML-ready data
  - File upload with drag-and-drop
  - Batch processing with configurable presets
  - Real-time job monitoring with progress tracking
  - File browser with download/delete
  - Statistics dashboard with visualizations
  - Service health monitoring
- **Multi-locale Support**: Query in multiple languages (EN, ES, FR, DE, JA, ZH)

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set service URLs (optional, defaults to localhost)
export AI_MANAGER_URL=http://localhost:8005
export DATA_PREP_URL=http://localhost:8006

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
  -e DATA_PREP_URL=http://data-prep:8006 \
  web-frontend:latest
```

### Docker Compose

```bash
# Start all services including web frontend
docker-compose up -d web-frontend

# View logs
docker-compose logs -f web-frontend
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
  base_url: "http://ai-manager:8005"
  timeout: 30

data_prep:
  base_url: "http://data-prep:8006"
  timeout: 60
  upload_max_size_mb: 50

features:
  enable_world_query: true
  enable_character_query: true
  enable_events: true
  enable_system_status: true
  enable_data_prep: true

locales:
  - "en-US"
  - "es-ES"
  - "fr-FR"
  - "de-DE"
  - "ja-JP"
  - "zh-CN"
```

## Environment Variables

- `AI_MANAGER_URL`: Base URL for AI Manager service (default: `http://localhost:8005`)
- `DATA_PREP_URL`: Base URL for Data Prep service (default: `http://localhost:8006`)

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

### Data Prep Tab

Process source text files into ML-ready training data:

**Upload Sub-tab**:
- Drag-and-drop file upload (supports multiple .txt files)
- Select processing preset:
  - **Fast Processing**: Quick processing without LLM enhancement
  - **Balanced**: Moderate settings with selective LLM enhancement
  - **High Quality**: Full LLM enhancement for maximum metadata
  - **Chapter-based**: Chunk by chapter boundaries
- Instant processing with automatic job creation

**Batch Sub-tab**:
- Configure source and output directories
- Choose processing preset
- Start batch jobs for entire directories
- Automatic file discovery and processing

**Jobs Sub-tab**:
- Real-time monitoring of all active jobs
- Progress bars showing completion percentage
- File and chunk counts per job
- Status indicators:
  - ⏳ Pending
  - ⚙️ Processing
  - ✅ Completed
  - ❌ Failed
- Manual refresh or auto-update
- Detailed error messages for failed jobs

**Files Sub-tab**:
- Browse all processed JSONL files
- View file metadata:
  - Chunks count
  - File size (MB)
  - Quality issues found
- Actions per file:
  - 📥 Download: Get processed JSONL file
  - 🔍 View Metadata: See full processing details
  - 🗑️ Delete: Remove processed file
- Quality reports showing detected issues

**Stats Sub-tab**:
- Overall metrics:
  - Total files processed
  - Total chunks created
  - Total storage used (GB)
- Interactive visualizations:
  - **Chunks per File**: Bar chart showing distribution
  - **Storage Distribution**: Pie chart of file sizes
- Real-time statistics updates

**Health Sub-tab**:
- Data prep service status (healthy/degraded/unhealthy)
- Component health checks:
  - ✓ LLM Proxy connectivity
  - ✓ File system access
- Service uptime tracking
- Detailed error information

## Development

### Project Structure

```
web-frontend/
├── app.py              # Main Streamlit application
├── config.yaml         # Configuration
├── requirements.txt    # Python dependencies (now includes plotly, pandas)
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
- `render_data_prep_tab()`: Data preparation interface
  - `render_data_prep_upload()`: File upload
  - `render_data_prep_batch()`: Batch processing
  - `render_data_prep_jobs()`: Job monitoring
  - `render_data_prep_files()`: File browser
  - `render_data_prep_stats()`: Statistics dashboard
  - `render_data_prep_health()`: Service health

Add new tabs by creating new render functions and adding to `main()`.

### API Clients

Two client classes handle communication:

**AIManagerClient**:
- World queries
- Character queries
- Event management
- System status

**DataPrepClient**:
- Batch processing
- File upload
- Job monitoring
- File management
- Statistics
- Health checks

### Configuration Presets

Four presets available for data processing:

1. **Fast Processing**: No LLM, smaller chunks (1024 tokens)
2. **Balanced**: Selective LLM features, standard chunks (2048 tokens)
3. **High Quality**: Full LLM enhancement, all features enabled
4. **Chapter-based**: Chapter boundary detection for natural splits

## Troubleshooting

### Cannot connect to AI Manager

1. Check `AI_MANAGER_URL` environment variable
2. Verify AI Manager service is running
3. Check network connectivity between services
4. Review logs: `docker-compose logs web-frontend`

### Cannot connect to Data Prep Service

1. Check `DATA_PREP_URL` environment variable
2. Verify data-prep service is running: `docker-compose ps data-prep`
3. Check service health: Navigate to Health sub-tab
4. Review data-prep logs: `docker-compose logs data-prep`

### File Upload Errors

1. Verify file format is .txt
2. Check file size (default max: 50MB)
3. Ensure data-prep service is healthy
4. Check llm-proxy service if using LLM enhancement

### Streamlit errors

1. Check Python version (requires 3.11+)
2. Reinstall dependencies: `pip install -r requirements.txt`
3. Clear Streamlit cache: Delete `.streamlit/` directory
4. Check for port conflicts on 8501

### Job Not Progressing

1. Check job status in Jobs sub-tab
2. View error message if status is "failed"
3. Verify source directory path is correct
4. Check data-prep service logs for details
5. Ensure LLM proxy is running if enhancement enabled

## License

MIT License
