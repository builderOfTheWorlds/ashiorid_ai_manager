# Data Preparation Service Architecture Analysis

## Executive Summary

The Ashiorid AI Manager currently **does not have a dedicated data-prep-service**. File processing is currently handled by the **lore-rag-service** which ingests text documents for semantic search. You are on a feature branch (`claude/add-pdf-support-011CUv7gG3KGUsgUQVA3QLUB`) to add PDF support to the system.

---

## 1. Current File Processing Support

### Supported File Types
The system currently supports:
- **Text files** (`.txt`)
- **Markdown files** (`.md`)

**Configuration Location**: `/home/user/ashiorid_ai_manager/lore-rag-service/config.yaml` (lines 56-61)

```yaml
ingestion:
  max_file_size_mb: 50
  supported_formats:
    - txt
    - md
  batch_size: 100
```

### File Processing Limitation
Currently, the `/ingest/file` endpoint in routes.py (line 174) performs **basic UTF-8 decoding only**:

```python
content = await file.read()
text = content.decode('utf-8')  # ← Only works for text files
```

This approach **cannot handle binary files like PDFs** without additional parsing.

---

## 2. Overall Architecture

### Microservices Architecture

```
┌─────────────────────────────────────────┐
│     User / File Upload Interface        │
└────────────────────┬────────────────────┘
                     │
    ┌────────────────┴────────────────┐
    │   API Gateway / Routes Layer    │
    └────────────────┬────────────────┘
                     │
    ┌────────────────┴────────────────────────────┐
    │      Lore RAG Service (Port: 8002)          │
    │                                             │
    │  Routes → Ingestion → Embeddings → Qdrant   │
    └────────────────┬────────────────────────────┘
                     │
    ┌────────────────┴────────────────┐
    │    Supporting Infrastructure    │
    │  - Qdrant (Vector DB)           │
    │  - Ollama (Embeddings)          │
    │  - PostgreSQL (Metadata)        │
    │  - Redis (Caching)              │
    └────────────────────────────────────┘
```

### Relevant Services

1. **Lore RAG Service** (Port: 8002)
   - **Primary ingestion point for documents**
   - Uses Qdrant for vector storage
   - Generates embeddings via Ollama

2. **Character Agent Service** (Port: 8003)
   - Consumes RAG data for context

3. **AI Manager Service** (Port: 8005)
   - Orchestrates other services

---

## 3. File Processing Logic Location

### Main Entry Points

#### 1. **API Route Handler**
- **File**: `/home/user/ashiorid_ai_manager/lore-rag-service/src/api/routes.py`
- **Lines**: 153-201
- **Function**: `ingest_file()`
- **Current Behavior**: 
  - Accepts file upload
  - Reads file as UTF-8 text
  - Passes to ingestion service

```python
@router.post("/ingest/file")
async def ingest_file(
    file: UploadFile = File(...),
    collection: str = "lore",
    source: str = None,
    ingestion_service=Depends(get_ingestion_service),
):
    content = await file.read()
    text = content.decode('utf-8')  # ← UTF-8 ONLY
```

#### 2. **Ingestion Service**
- **File**: `/home/user/ashiorid_ai_manager/lore-rag-service/src/services/ingestion.py`
- **Classes**:
  - `IngestionService` - Handles document ingestion pipeline
  
- **Key Methods**:
  - `ingest_text()` (lines 159-191) - Processes raw text
  - `_chunk_text()` (lines 39-91) - Splits text into chunks
  - `ingest()` (lines 93-157) - Stores chunks in vector database

#### 3. **Text Chunking Strategy**
- **Token-based chunking** using `tiktoken`
- **Chunk size**: 512 tokens (configurable)
- **Overlap**: 50 tokens
- **Minimum chunk**: 100 tokens

---

## 4. How Files Are Ingested and Parsed

### Current Ingestion Pipeline

```
Upload File
    ↓
[routes.py] Read binary content + decode UTF-8
    ↓
[ingestion.py] ingest_text()
    ↓
[ingestion.py] _chunk_text()
    ├─ Token-based chunking (tiktoken)
    ├─ Create DocumentChunk objects
    └─ Apply metadata (chunk_index, token_count)
    ↓
[embeddings.py] generate_embeddings()
    ├─ Batch processing (32 texts/batch)
    └─ Call Ollama API (/api/embeddings)
    ↓
[qdrant_client.py] upsert_points()
    ├─ Create PointStruct objects
    ├─ Attach embeddings as vectors
    └─ Store in Qdrant with payload (text, source, metadata)
    ↓
Vector Database (Qdrant)
    └─ Indexed by vector similarity
```

### Data Models Used

**DocumentChunk** (shared/common_types.py, lines 138-143):
```python
class DocumentChunk(BaseModel):
    text: str                              # Chunk content
    source: str                            # File source identifier
    metadata: Optional[Dict[str, Any]]     # Custom metadata
```

### Configuration Points

**Text Processing Config** (config.yaml, lines 31-40):
```yaml
text_processing:
  chunk_size: 512              # tokens per chunk
  chunk_overlap: 50            # overlap between chunks
  min_chunk_size: 100          # minimum tokens
  languages:
    - en
```

---

## 5. Output Format

### Output Structure

The ingestion process returns a structured response:

```python
{
    "status": "success",
    "filename": "document.txt",
    "collection": "lore",
    "chunks_created": 42,
    "details": {
        "documents_ingested": 42,
        "embeddings_generated": 42,
        "points_upserted": 42,
    }
}
```

### Vector Storage Format

Data stored in Qdrant with this structure:

```python
PointStruct(
    id=uuid4(),                  # Unique point ID
    vector=embedding,            # 768-dim vector from nomic-embed-text
    payload={
        "text": "chunk text...",
        "source": "filename.txt",
        "metadata": {
            "chunk_index": 0,
            "token_count": 512,
        }
    }
)
```

### Search/Retrieval Format

When data is retrieved via semantic search (SearchResult in common_types.py):

```python
class SearchResult(BaseModel):
    text: str                    # The actual text chunk
    score: float                 # Similarity score (0-1)
    source: str                  # Original file source
    metadata: Optional[Dict]     # Custom metadata
```

---

## 6. Service Dependencies

### Internal Dependencies
- **Qdrant** (Port 6333) - Vector database
- **Ollama** (Port 11434) - Embedding generation
- **Redis** (Port 6379) - Caching
- **PostgreSQL** (Port 5432) - Metadata storage (optional)

### Required Python Packages
```
qdrant-client
httpx (async HTTP client)
tiktoken (tokenizer)
fastapi
pydantic
```

---

## 7. Configuration Files

### Main Configuration
- **File**: `/home/user/ashiorid_ai_manager/lore-rag-service/config.yaml`
- **Sections**:
  - `service` - Port, host, workers
  - `qdrant` - Vector DB connection
  - `ollama` - Embedding model
  - `text_processing` - Chunking parameters
  - `ingestion` - File size limits, formats
  - `search` - Query parameters
  - `cache` - Redis settings

### Docker Compose Configuration
- **File**: `/home/user/ashiorid_ai_manager/docker-compose.yml`
- **Relevant Service**: `lore-rag` (lines 114-139)

---

## 8. Key Code Files Summary

| File | Purpose | Key Functions |
|------|---------|----------------|
| `routes.py` | API endpoints | `ingest_file()`, `ingest_documents()`, `semantic_search()` |
| `ingestion.py` | Document processing | `ingest_text()`, `_chunk_text()`, `ingest()` |
| `embeddings.py` | Vector generation | `generate_embeddings()`, `generate_embedding()` |
| `qdrant_client.py` | Vector storage | `upsert_points()`, `search()`, `create_collection()` |
| `search.py` | Semantic search | `search()` |

---

## 9. Current Limitations & Gaps

### For Adding PDF Support

1. **No PDF Parser**
   - Current code only handles UTF-8 text
   - Binary files need specialized parsing (e.g., PyPDF2, pdfplumber)

2. **No File Format Detection**
   - No MIME type checking
   - No magic number validation

3. **No OCR Capability**
   - Cannot extract text from image-based PDFs
   - Would need Tesseract or similar

4. **Metadata Extraction Not Implemented**
   - PDF metadata (title, author, creation date) not extracted
   - Could enhance search with document-level metadata

5. **No Data-Prep Service**
   - Currently no separate preprocessing microservice
   - Could benefit from dedicated service for file handling

---

## 10. Recommendations for PDF Support

### Phase 1: Add PDF Parsing to Lore RAG Service
- Add PyPDF2 or pdfplumber dependency
- Update routes.py to detect file type
- Update ingestion.py to handle PDF extraction
- Enhance config.yaml to include "pdf" in supported_formats

### Phase 2: Create Dedicated Data-Prep Service (Optional)
- Separate microservice for file preprocessing
- Handle multiple formats (PDF, DOCX, etc.)
- Implement OCR for image-based PDFs
- Extract and enrich metadata
- Return standardized DocumentChunk format

### Phase 3: Enhanced Metadata
- Extract PDF metadata (title, author, creation date)
- Store in DocumentChunk.metadata
- Enable filtering by document properties

---

## Architecture Diagram: Proposed Data-Prep Service

```
                    User/Client
                        │
        ┌───────────────┼───────────────┐
        │               │               │
    [Text]          [PDF]           [DOCX]
        │               │               │
        └───────────────┼───────────────┘
                        │
            ┌───────────▼──────────┐
            │  Data-Prep Service   │
            │  (NEW - Optional)    │
            │                      │
            │  • Format Detection  │
            │  • PDF Parsing       │
            │  • Text Extraction   │
            │  • Metadata Extract  │
            │  • Chunking          │
            └───────────┬──────────┘
                        │
          ┌─────────────▼──────────────┐
          │  Normalized DocumentChunk  │
          │  + Metadata                │
          └─────────────┬──────────────┘
                        │
            ┌───────────▼──────────┐
            │  Lore RAG Service    │
            │                      │
            │  • Embedding Gen     │
            │  • Vector Storage    │
            │  • Search            │
            └───────────┬──────────┘
                        │
            ┌───────────▼──────────┐
            │  Qdrant Vector DB    │
            └──────────────────────┘
```

