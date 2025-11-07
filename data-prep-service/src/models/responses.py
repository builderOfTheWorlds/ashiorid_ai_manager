"""
Response models for Data Preparation Service.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class JobResponse(BaseModel):
    """Response for job creation."""

    job_id: str
    status: str  # "processing", "completed", "failed"
    files_found: Optional[int] = None
    message: Optional[str] = None


class JobStatusResponse(BaseModel):
    """Response for job status check."""

    job_id: str
    status: str  # "processing", "completed", "failed"
    files_processed: int = 0
    files_total: int = 0
    chunks_created: int = 0
    progress_percent: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ProcessedFileInfo(BaseModel):
    """Information about a processed file."""

    filename: str
    source: str
    chunks: int
    size_mb: float
    processed_date: datetime
    quality_issues: List[str] = Field(default_factory=list)


class ProcessedFileMetadata(BaseModel):
    """Detailed metadata for a processed file."""

    source: str
    processed_date: datetime
    chunks: int
    total_tokens: int
    quality_issues: List[str] = Field(default_factory=list)
    processing_config: Dict[str, Any] = Field(default_factory=dict)
    statistics: Dict[str, Any] = Field(default_factory=dict)


class FileListResponse(BaseModel):
    """Response for listing processed files."""

    files: List[ProcessedFileInfo]
    total: int


class ServiceStatsResponse(BaseModel):
    """Service statistics response."""

    total_files: int
    total_chunks: int
    total_size_gb: float
    files_by_status: Dict[str, int] = Field(default_factory=dict)


class ChunkData(BaseModel):
    """Individual chunk data structure."""

    source: str
    chunk_id: int
    type: str  # "prose", "dialogue", "mixed"
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
