# Data Preparation Service

The Data Preparation Service processes raw text files (books and movie scripts) into ML-ready training data in JSONL format for the Ashiorid AI Manager.

## Features

- **Text Normalization**: Unicode normalization, smart quote standardization, OCR error correction
- **Quality Checking**: Detects encoding corruption, duplicate paragraphs, incomplete text
- **Intelligent Chunking**: Token-based, chapter-based, or scene-based strategies
- **LLM Enhancement**: Automatic summaries, character extraction, theme tagging, narrative arc detection
- **Async Processing**: Background job processing with progress tracking
- **RESTful API**: Complete API for batch processing, file upload, and job management

## Architecture

```
data-prep-service/
├── src/
│   ├── api/              # FastAPI routes
│   ├── models/           # Pydantic request/response models
│   ├── services/         # Core processing services
│   │   ├── normalizer.py          # Text normalization
│   │   ├── quality_checker.py     # Quality validation
│   │   ├── chunker.py             # Text chunking
│   │   ├── llm_enhancer.py        # LLM-powered enhancement
│   │   ├── file_manager.py        # File I/O operations
│   │   ├── job_manager.py         # Async job tracking
│   │   └── processing_pipeline.py # Main orchestrator
│   └── utils/            # Utility functions
│       ├── text_utils.py          # Text processing utilities
│       └── llm_client.py          # LLM proxy client
├── tests/                # Unit tests
├── config.yaml           # Service configuration
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Configuration

Edit `config.yaml` to customize processing:

```yaml
processing:
  normalization:
    unicode_form: "NFKC"
    standardize_quotes: true
    correct_ocr_errors: true

  chunking:
    strategy: "token_count"  # Options: token_count, chapter, scene
    chunk_size_tokens: 2048
    chunk_overlap_tokens: 200

  llm_enhancement:
    enabled: true
    model: "llama3.2"
    features:
      generate_summaries: true
      extract_characters: true
      tag_themes: true
```

## API Endpoints

### Processing

- `POST /process/batch` - Process all files in a directory
- `POST /process/file` - Upload and process a single file
- `POST /reprocess/{filename}` - Reprocess with new settings

### Job Management

- `GET /jobs/{job_id}` - Check job status and progress

### File Management

- `GET /files` - List all processed files
- `GET /files/{filename}` - Download processed JSONL file
- `GET /files/{filename}/metadata` - Get processing metadata
- `DELETE /files/{filename}` - Delete processed file

### Statistics

- `GET /stats` - Service statistics
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics

## Usage

### Docker Compose (Recommended)

```bash
# Start the service
docker-compose up -d data-prep

# View logs
docker-compose logs -f data-prep

# Stop the service
docker-compose down
```

### Standalone

```bash
# Install dependencies
pip install -r requirements.txt

# Run the service
python src/main.py
```

### Environment Variables

```bash
# Source files directory (optional, defaults to config.yaml)
#export SOURCE_FILES_DIR=/path/to/source/files
export SOURCE_FILES_DIR=/path/to/source/files="C:\Users\matt\PycharmProjects\ashiorid\sourceWorks\txt"

# Log level
export LOG_LEVEL=INFO

# Log format
export LOG_FORMAT=json
```

## Processing Pipeline

1. **Normalization**: Clean and standardize text
   - Unicode normalization (NFKC)
   - Smart quote standardization
   - OCR error correction
   - Page artifact removal
   - Screenplay format flattening

2. **Quality Check**: Validate text quality
   - Minimum length validation
   - Encoding corruption detection
   - Duplicate paragraph detection
   - Incomplete text detection

3. **Chunking**: Split into manageable pieces
   - Token-based: Fixed size with overlap
   - Chapter-based: One chunk per chapter
   - Scene-based: Natural scene boundaries

4. **LLM Enhancement**: Add metadata (optional)
   - Section summaries
   - Character extraction
   - Theme/trope tagging
   - Narrative arc classification
   - POV identification

5. **Output**: Generate JSONL files
   - One JSON object per line
   - Includes text, metadata, and embedding hints

## Output Format

Each chunk is a JSON object with the following structure:

```json
{
  "source": "book1.txt",
  "chunk_id": 0,
  "type": "prose",
  "text": "The story begins...",
  "metadata": {
    "summary": "Introduction to the protagonist",
    "characters": ["John Doe", "Jane Smith"],
    "themes": ["worldbuilding", "character_development"],
    "narrative_arc": "exposition",
    "pov": "third_person_limited",
    "tokens": 512,
    "embedding_hint": "worldbuilding",
    "enhanced": true
  }
}
```

## Example API Usage

### Process a batch of files

```bash
curl -X POST http://localhost:8006/process/batch \
  -H "Content-Type: application/json" \
  -d '{
    "source_dir": "/path/to/books",
    "output_dir": "/path/to/output"
  }'
```

Response:
```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "processing",
  "files_found": 10,
  "message": "Batch processing started"
}
```

### Check job status

```bash
curl http://localhost:8006/jobs/123e4567-e89b-12d3-a456-426614174000
```

Response:
```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "files_processed": 10,
  "files_total": 10,
  "chunks_created": 1500,
  "progress_percent": 100.0
}
```

### List processed files

```bash
curl http://localhost:8006/files
```

### Download a processed file

```bash
curl http://localhost:8006/files/book1.jsonl -o book1.jsonl
```

## Testing

Run the test suite:

```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python tests/test_normalizer.py
```

## Performance

- **Chunking**: ~1000 chunks/second
- **LLM Enhancement**: ~5-10 chunks/second (depends on LLM service)
- **File I/O**: Streaming for large files to minimize memory usage

## Dependencies

- **FastAPI**: Web framework
- **Pydantic**: Data validation
- **tiktoken**: Accurate token counting
- **chardet**: Encoding detection
- **httpx**: Async HTTP client for LLM proxy

## Troubleshooting

### LLM Enhancement Not Working

- Check that `llm-proxy-service` is running: `docker-compose ps llm-proxy`
- Verify configuration: `llm_enhancement.enabled: true`
- Check logs: `docker-compose logs data-prep`

### Files Not Found

- Verify `SOURCE_FILES_DIR` environment variable
- Check file permissions
- Ensure files are .txt format

### Out of Memory

- Reduce `chunk_size_tokens` in config
- Process files individually instead of batch
- Increase Docker memory limit

## Integration

The service integrates with:

- **llm-proxy-service**: For LLM-powered enhancements
- **Prometheus**: For metrics collection
- **File System**: For input/output operations

## License

Part of the Ashiorid AI Manager project.
