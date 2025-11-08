"""
Main processing pipeline orchestrator.
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import sys
sys.path.append('../..')
from shared.logging_config import get_logger

from src.services.normalizer import NormalizerService
from src.services.quality_checker import QualityCheckerService
from src.services.chunker import ChunkerService
from src.services.llm_enhancer import LLMEnhancerService
from src.services.file_manager import FileManagerService
from src.services.job_manager import JobManagerService

logger = get_logger(__name__)


class ProcessingPipeline:
    """Main processing pipeline orchestrator."""

    def __init__(
        self,
        config: Dict[str, Any],
        normalizer: NormalizerService,
        quality_checker: QualityCheckerService,
        chunker: ChunkerService,
        llm_enhancer: LLMEnhancerService,
        file_manager: FileManagerService,
        job_manager: JobManagerService,
    ):
        """
        Initialize processing pipeline.

        Args:
            config: Service configuration
            normalizer: Text normalization service
            quality_checker: Quality checking service
            chunker: Text chunking service
            llm_enhancer: LLM enhancement service
            file_manager: File management service
            job_manager: Job management service
        """
        self.config = config
        self.normalizer = normalizer
        self.quality_checker = quality_checker
        self.chunker = chunker
        self.llm_enhancer = llm_enhancer
        self.file_manager = file_manager
        self.job_manager = job_manager

    async def process_file(
        self,
        file_path: str,
        job_id: Optional[str] = None,
        config_override: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process a single file through the pipeline.

        Args:
            file_path: Path to input file
            job_id: Optional job ID for tracking
            config_override: Optional configuration overrides

        Returns:
            Processing result dictionary
        """
        filename = Path(file_path).name
        logger.info(f"Processing file: {filename}")

        result = {
            "source": filename,
            "success": False,
            "chunks_created": 0,
            "quality_issues": [],
            "error": None,
        }

        try:
            # Step 1: Normalize text
            logger.info(f"[{filename}] Step 1: Normalizing text")
            is_screenplay = self.file_manager.is_screenplay(filename)
            normalized_text = self.normalizer.normalize_file(file_path, is_screenplay=is_screenplay)

            if not normalized_text.strip():
                raise ValueError("Normalized text is empty")

            # Step 2: Quality check
            logger.info(f"[{filename}] Step 2: Quality checking")
            quality_issues = self.quality_checker.check_quality(normalized_text, source=filename)
            result["quality_issues"] = quality_issues

            if not self.quality_checker.is_acceptable(quality_issues):
                raise ValueError(f"Quality check failed: {quality_issues}")

            # Step 3: Chunk text
            logger.info(f"[{filename}] Step 3: Chunking text")
            chunks = self.chunker.chunk_text(normalized_text)

            if not chunks:
                raise ValueError("No chunks created")

            logger.info(f"[{filename}] Created {len(chunks)} chunks")

            # Step 4: LLM enhancement
            logger.info(f"[{filename}] Step 4: LLM enhancement")
            chunk_metadata_list = await self.llm_enhancer.enhance_chunks(chunks)

            # Step 5: Build final chunk objects
            logger.info(f"[{filename}] Step 5: Building final chunks")
            final_chunks = []

            for i, (chunk_text, metadata) in enumerate(zip(chunks, chunk_metadata_list)):
                chunk_obj = {
                    "source": filename,
                    "chunk_id": i,
                    "type": self._determine_chunk_type(chunk_text),
                    "text": chunk_text,
                    "metadata": {
                        **metadata,
                        "tokens": self.chunker.count_tokens(chunk_text),
                    },
                }
                final_chunks.append(chunk_obj)

            # Step 6: Write output
            logger.info(f"[{filename}] Step 6: Writing output")
            output_filename = f"{Path(filename).stem}.jsonl"
            output_path = self.file_manager.write_jsonl(final_chunks, output_filename)

            # Write metadata
            file_metadata = {
                "source": filename,
                "processed_date": datetime.utcnow().isoformat(),
                "chunks": len(final_chunks),
                "total_tokens": sum(c["metadata"]["tokens"] for c in final_chunks),
                "quality_issues": quality_issues,
                "processing_config": {
                    "normalization": self.config.get('processing', {}).get('normalization', {}),
                    "chunking": self.config.get('processing', {}).get('chunking', {}),
                    "llm_enhancement": {
                        "enabled": self.config.get('processing', {}).get('llm_enhancement', {}).get('enabled', False),
                    },
                },
                "statistics": {
                    "original_length": len(normalized_text),
                    "avg_chunk_size": len(normalized_text) // len(final_chunks) if final_chunks else 0,
                },
            }

            self.file_manager.write_metadata(Path(output_filename).stem, file_metadata)

            # Update result
            result["success"] = True
            result["chunks_created"] = len(final_chunks)
            result["output_file"] = output_filename

            logger.info(f"[{filename}] Processing complete: {len(final_chunks)} chunks created")

        except Exception as e:
            logger.error(f"[{filename}] Processing failed: {e}", exc_info=True)
            result["error"] = str(e)

        return result

    async def process_batch(
        self,
        source_dir: Optional[str] = None,
        output_dir: Optional[str] = None,
        config_override: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Process all files in a directory.

        Args:
            source_dir: Source directory path
            output_dir: Output directory path
            config_override: Configuration overrides

        Returns:
            Job ID
        """
        # List input files
        files = self.file_manager.list_input_files(source_dir)

        if not files:
            raise ValueError(f"No input files found in {source_dir or 'default directory'}")

        # Create job
        job_id = self.job_manager.create_job(
            job_type="batch",
            files_total=len(files),
            metadata={
                "source_dir": source_dir or str(self.file_manager.input_dir),
                "output_dir": output_dir or str(self.file_manager.output_dir),
            },
        )

        # Start background processing
        asyncio.create_task(
            self._process_batch_background(job_id, files, config_override)
        )

        return job_id

    async def _process_batch_background(
        self,
        job_id: str,
        files: List[str],
        config_override: Optional[Dict[str, Any]] = None,
    ):
        """
        Background task for batch processing.

        Args:
            job_id: Job ID
            files: List of file paths
            config_override: Configuration overrides
        """
        self.job_manager.start_job(job_id)

        total_chunks = 0
        files_processed = 0

        for i, file_path in enumerate(files):
            try:
                result = await self.process_file(file_path, job_id, config_override)

                if result["success"]:
                    total_chunks += result["chunks_created"]
                    files_processed += 1

                # Update progress
                self.job_manager.update_progress(
                    job_id,
                    files_processed=i + 1,
                    chunks_created=total_chunks,
                    details={
                        "last_processed": result["source"],
                        "last_success": result["success"],
                    },
                )

            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}", exc_info=True)
                self.job_manager.update_progress(
                    job_id,
                    files_processed=i + 1,
                    details={"last_error": str(e)},
                )

        # Complete job
        self.job_manager.complete_job(
            job_id,
            success=True,
            error=None if files_processed > 0 else "No files processed successfully",
        )

    async def process_uploaded_file(
        self,
        content: bytes,
        filename: str,
        config_override: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Process an uploaded file.

        Args:
            content: File content
            filename: Original filename
            config_override: Configuration overrides

        Returns:
            Job ID
        """
        import tempfile

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.txt') as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # Create job
            job_id = self.job_manager.create_job(
                job_type="single_file",
                files_total=1,
                metadata={"filename": filename},
            )

            # Process in background
            asyncio.create_task(
                self._process_uploaded_background(job_id, tmp_path, filename, config_override)
            )

            return job_id

        except Exception as e:
            # Clean up temp file on error
            import os
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise e

    async def _process_uploaded_background(
        self,
        job_id: str,
        tmp_path: str,
        filename: str,
        config_override: Optional[Dict[str, Any]] = None,
    ):
        """
        Background task for uploaded file processing.

        Args:
            job_id: Job ID
            tmp_path: Temporary file path
            filename: Original filename
            config_override: Configuration overrides
        """
        import os

        self.job_manager.start_job(job_id)

        try:
            result = await self.process_file(tmp_path, job_id, config_override)

            self.job_manager.update_progress(
                job_id,
                files_processed=1,
                chunks_created=result["chunks_created"],
            )

            self.job_manager.complete_job(
                job_id,
                success=result["success"],
                error=result.get("error"),
            )

        except Exception as e:
            logger.error(f"Error processing uploaded file: {e}", exc_info=True)
            self.job_manager.complete_job(job_id, success=False, error=str(e))

        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _determine_chunk_type(self, text: str) -> str:
        """
        Determine chunk type (prose, dialogue, mixed).

        Args:
            text: Chunk text

        Returns:
            Chunk type
        """
        # Simple heuristic: if >30% of text is in quotes, it's dialogue
        quote_chars = text.count('"') + text.count("'")
        total_chars = len(text)

        if total_chars == 0:
            return "prose"

        quote_ratio = quote_chars / total_chars

        if quote_ratio > 0.3:
            return "dialogue"
        elif quote_ratio > 0.1:
            return "mixed"
        else:
            return "prose"
