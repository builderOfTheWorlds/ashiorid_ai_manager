"""
Request models for Data Preparation Service.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class BatchProcessRequest(BaseModel):
    """Request to process all files in a directory."""

    source_dir: Optional[str] = Field(
        default=None,
        description="Source directory path (uses config default if not provided)"
    )
    output_dir: Optional[str] = Field(
        default=None,
        description="Output directory path (uses config default if not provided)"
    )
    config_override: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Override configuration parameters"
    )


class FileProcessRequest(BaseModel):
    """Request to process a single uploaded file."""

    filename: str = Field(description="Name of the file")
    config_override: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Override configuration parameters"
    )


class ReprocessRequest(BaseModel):
    """Request to reprocess an existing file with new settings."""

    config_override: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Override configuration parameters"
    )
