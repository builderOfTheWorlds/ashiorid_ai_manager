"""
Job management service for async processing tracking.
"""

import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum
import sys
sys.path.append('../..')
from shared.logging_config import get_logger

logger = get_logger(__name__)


class JobStatus(str, Enum):
    """Job status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobManagerService:
    """Service for managing processing jobs."""

    def __init__(self):
        """Initialize job manager service."""
        self.jobs: Dict[str, Dict[str, Any]] = {}
        logger.info("Job manager initialized")

    def create_job(
        self,
        job_type: str,
        files_total: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a new processing job.

        Args:
            job_type: Type of job (e.g., "batch", "single_file")
            files_total: Total number of files to process
            metadata: Additional metadata

        Returns:
            Job ID
        """
        job_id = str(uuid.uuid4())

        job = {
            "job_id": job_id,
            "job_type": job_type,
            "status": JobStatus.PENDING,
            "files_total": files_total,
            "files_processed": 0,
            "chunks_created": 0,
            "started_at": None,
            "completed_at": None,
            "error": None,
            "metadata": metadata or {},
            "details": {},
        }

        self.jobs[job_id] = job
        logger.info(f"Created job {job_id} (type: {job_type}, files: {files_total})")

        return job_id

    def start_job(self, job_id: str):
        """
        Mark job as started.

        Args:
            job_id: Job ID
        """
        if job_id in self.jobs:
            self.jobs[job_id]["status"] = JobStatus.PROCESSING
            self.jobs[job_id]["started_at"] = datetime.utcnow()
            logger.info(f"Job {job_id} started")

    def update_progress(
        self,
        job_id: str,
        files_processed: Optional[int] = None,
        chunks_created: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Update job progress.

        Args:
            job_id: Job ID
            files_processed: Number of files processed
            chunks_created: Number of chunks created
            details: Additional details
        """
        if job_id not in self.jobs:
            logger.warning(f"Job {job_id} not found for progress update")
            return

        job = self.jobs[job_id]

        if files_processed is not None:
            job["files_processed"] = files_processed

        if chunks_created is not None:
            job["chunks_created"] = chunks_created

        if details:
            job["details"].update(details)

        # Calculate progress
        if job["files_total"] > 0:
            progress = (job["files_processed"] / job["files_total"]) * 100
            job["progress_percent"] = round(progress, 2)
        else:
            job["progress_percent"] = 0.0

        logger.debug(
            f"Job {job_id} progress: {job['files_processed']}/{job['files_total']} "
            f"files ({job['progress_percent']}%)"
        )

    def complete_job(self, job_id: str, success: bool = True, error: Optional[str] = None):
        """
        Mark job as completed.

        Args:
            job_id: Job ID
            success: Whether job completed successfully
            error: Error message if failed
        """
        if job_id not in self.jobs:
            logger.warning(f"Job {job_id} not found for completion")
            return

        job = self.jobs[job_id]
        job["completed_at"] = datetime.utcnow()

        if success:
            job["status"] = JobStatus.COMPLETED
            logger.info(
                f"Job {job_id} completed successfully "
                f"({job['files_processed']} files, {job['chunks_created']} chunks)"
            )
        else:
            job["status"] = JobStatus.FAILED
            job["error"] = error
            logger.error(f"Job {job_id} failed: {error}")

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job status.

        Args:
            job_id: Job ID

        Returns:
            Job status dictionary or None if not found
        """
        return self.jobs.get(job_id)

    def list_jobs(self, status: Optional[JobStatus] = None) -> Dict[str, Dict[str, Any]]:
        """
        List all jobs, optionally filtered by status.

        Args:
            status: Optional status filter

        Returns:
            Dictionary of jobs
        """
        if status:
            return {
                job_id: job
                for job_id, job in self.jobs.items()
                if job["status"] == status
            }
        return self.jobs.copy()

    def cleanup_old_jobs(self, max_age_hours: int = 24):
        """
        Clean up old completed/failed jobs.

        Args:
            max_age_hours: Maximum age in hours
        """
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        removed = 0

        jobs_to_remove = []
        for job_id, job in self.jobs.items():
            if job["status"] in [JobStatus.COMPLETED, JobStatus.FAILED]:
                completed_at = job.get("completed_at")
                if completed_at and completed_at < cutoff:
                    jobs_to_remove.append(job_id)

        for job_id in jobs_to_remove:
            del self.jobs[job_id]
            removed += 1

        if removed > 0:
            logger.info(f"Cleaned up {removed} old jobs")
