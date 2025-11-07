"""
API routes for Data Preparation Service.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Depends, File, UploadFile
from fastapi.responses import FileResponse

import sys
sys.path.append('../..')
from shared.logging_config import get_logger

from src.models.requests import BatchProcessRequest, ReprocessRequest
from src.models.responses import (
    JobResponse,
    JobStatusResponse,
    FileListResponse,
    ServiceStatsResponse,
    ProcessedFileInfo,
    ProcessedFileMetadata,
)

logger = get_logger(__name__)

router = APIRouter()


def get_pipeline(request: Request):
    """Dependency to get processing pipeline from app state."""
    return request.app.state.app_state.pipeline


def get_file_manager(request: Request):
    """Dependency to get file manager from app state."""
    return request.app.state.app_state.file_manager


def get_job_manager(request: Request):
    """Dependency to get job manager from app state."""
    return request.app.state.app_state.job_manager


@router.post("/process/batch", response_model=JobResponse)
async def process_batch(
    request_data: BatchProcessRequest,
    pipeline=Depends(get_pipeline),
):
    """
    Process all files in a directory.

    Args:
        request_data: Batch processing request

    Returns:
        Job response with job ID
    """
    try:
        logger.info(
            f"Batch process request: source_dir={request_data.source_dir}, "
            f"output_dir={request_data.output_dir}"
        )

        job_id = await pipeline.process_batch(
            source_dir=request_data.source_dir,
            output_dir=request_data.output_dir,
            config_override=request_data.config_override,
        )

        # Get initial job status
        job_status = pipeline.job_manager.get_job_status(job_id)

        return JobResponse(
            job_id=job_id,
            status=job_status["status"],
            files_found=job_status["files_total"],
            message="Batch processing started",
        )

    except Exception as e:
        logger.error(f"Batch process request failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process/file", response_model=JobResponse)
async def process_file(
    file: UploadFile = File(...),
    pipeline=Depends(get_pipeline),
):
    """
    Upload and process a single file.

    Args:
        file: Uploaded file

    Returns:
        Job response with job ID
    """
    try:
        logger.info(f"File upload request: {file.filename}")

        # Read file content
        content = await file.read()

        job_id = await pipeline.process_uploaded_file(
            content=content,
            filename=file.filename,
        )

        return JobResponse(
            job_id=job_id,
            status="processing",
            files_found=1,
            message=f"Processing file: {file.filename}",
        )

    except Exception as e:
        logger.error(f"File upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    job_manager=Depends(get_job_manager),
):
    """
    Get job status.

    Args:
        job_id: Job ID

    Returns:
        Job status information
    """
    try:
        job_status = job_manager.get_job_status(job_id)

        if not job_status:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        return JobStatusResponse(
            job_id=job_status["job_id"],
            status=job_status["status"],
            files_processed=job_status["files_processed"],
            files_total=job_status["files_total"],
            chunks_created=job_status["chunks_created"],
            progress_percent=job_status.get("progress_percent", 0.0),
            started_at=job_status.get("started_at"),
            completed_at=job_status.get("completed_at"),
            error=job_status.get("error"),
            details=job_status.get("details"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files", response_model=FileListResponse)
async def list_files(
    file_manager=Depends(get_file_manager),
):
    """
    List all processed files.

    Returns:
        List of processed files
    """
    try:
        files = file_manager.list_processed_files()

        file_info_list = [
            ProcessedFileInfo(
                filename=f["filename"],
                source=f["source"],
                chunks=f["chunks"],
                size_mb=f["size_mb"],
                processed_date=f["processed_date"],
                quality_issues=f["quality_issues"],
            )
            for f in files
        ]

        return FileListResponse(
            files=file_info_list,
            total=len(file_info_list),
        )

    except Exception as e:
        logger.error(f"Failed to list files: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/{filename}")
async def download_file(
    filename: str,
    file_manager=Depends(get_file_manager),
):
    """
    Download a processed JSONL file.

    Args:
        filename: Filename to download

    Returns:
        File download
    """
    try:
        from pathlib import Path

        file_path = file_manager.output_dir / filename

        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File {filename} not found")

        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type="application/jsonlines",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/{filename}/metadata", response_model=ProcessedFileMetadata)
async def get_file_metadata(
    filename: str,
    file_manager=Depends(get_file_manager),
):
    """
    Get metadata for a processed file.

    Args:
        filename: Filename (with or without .jsonl extension)

    Returns:
        File metadata
    """
    try:
        from pathlib import Path

        # Remove .jsonl if present
        base_name = Path(filename).stem

        metadata = file_manager.read_metadata(base_name)

        if not metadata:
            raise HTTPException(status_code=404, detail=f"Metadata for {filename} not found")

        return ProcessedFileMetadata(
            source=metadata.get("source", ""),
            processed_date=metadata.get("processed_date", ""),
            chunks=metadata.get("chunks", 0),
            total_tokens=metadata.get("total_tokens", 0),
            quality_issues=metadata.get("quality_issues", []),
            processing_config=metadata.get("processing_config", {}),
            statistics=metadata.get("statistics", {}),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get file metadata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/files/{filename}")
async def delete_file(
    filename: str,
    file_manager=Depends(get_file_manager),
):
    """
    Delete a processed file.

    Args:
        filename: Filename to delete

    Returns:
        Deletion status
    """
    try:
        success = file_manager.delete_processed_file(filename)

        if not success:
            raise HTTPException(status_code=404, detail=f"File {filename} not found")

        return {
            "status": "success",
            "message": f"File {filename} deleted",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reprocess/{filename}", response_model=JobResponse)
async def reprocess_file(
    filename: str,
    request_data: ReprocessRequest,
    file_manager=Depends(get_file_manager),
    pipeline=Depends(get_pipeline),
):
    """
    Reprocess an existing file with new settings.

    Args:
        filename: Filename to reprocess
        request_data: Reprocessing request

    Returns:
        Job response
    """
    try:
        # Find original source file
        metadata = file_manager.read_metadata(filename)

        if not metadata:
            raise HTTPException(status_code=404, detail=f"Metadata for {filename} not found")

        source_file = metadata.get("source")

        if not source_file:
            raise HTTPException(status_code=400, detail="Original source file not found in metadata")

        # Find source file path
        files = file_manager.list_input_files()
        source_path = None

        for file_path in files:
            if file_path.endswith(source_file):
                source_path = file_path
                break

        if not source_path:
            raise HTTPException(status_code=404, detail=f"Source file {source_file} not found")

        # Create job
        job_id = pipeline.job_manager.create_job(
            job_type="reprocess",
            files_total=1,
            metadata={"filename": filename, "source": source_file},
        )

        # Process file
        import asyncio
        asyncio.create_task(
            pipeline._process_batch_background(
                job_id,
                [source_path],
                request_data.config_override,
            )
        )

        return JobResponse(
            job_id=job_id,
            status="processing",
            files_found=1,
            message=f"Reprocessing file: {filename}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reprocess file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=ServiceStatsResponse)
async def get_stats(
    file_manager=Depends(get_file_manager),
):
    """
    Get service statistics.

    Returns:
        Service statistics
    """
    try:
        files = file_manager.list_processed_files()
        size_stats = file_manager.get_file_size_stats()

        total_chunks = sum(f["chunks"] for f in files)

        return ServiceStatsResponse(
            total_files=size_stats["total_files"],
            total_chunks=total_chunks,
            total_size_gb=size_stats["total_size_gb"],
        )

    except Exception as e:
        logger.error(f"Failed to get stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
