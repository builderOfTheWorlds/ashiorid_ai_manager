"""
File management service for input/output operations.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import sys
sys.path.append('../..')
from shared.logging_config import get_logger

logger = get_logger(__name__)


class FileManagerService:
    """Service for file management."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize file manager service.

        Args:
            config: Service configuration
        """
        self.config = config
        self.input_dir = Path(config.get('source_files', {}).get('input_directory', './input'))
        self.output_dir = Path(config.get('source_files', {}).get('output_directory', './processed_output'))
        self.supported_formats = config.get('source_files', {}).get('supported_formats', ['txt'])

        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"File manager initialized (input: {self.input_dir}, output: {self.output_dir})")

    def list_input_files(self, directory: Optional[str] = None) -> List[str]:
        """
        List all supported files in input directory.

        Args:
            directory: Optional directory path (uses default if not provided)

        Returns:
            List of file paths
        """
        input_path = Path(directory) if directory else self.input_dir

        if not input_path.exists():
            logger.warning(f"Input directory does not exist: {input_path}")
            return []

        files = []
        for ext in self.supported_formats:
            files.extend(input_path.glob(f"*.{ext}"))

        file_paths = [str(f) for f in files]
        logger.info(f"Found {len(file_paths)} input files in {input_path}")
        return file_paths

    def read_file(self, file_path: str) -> str:
        """
        Read text file content.

        Args:
            file_path: Path to file

        Returns:
            File content
        """
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        logger.debug(f"Read file: {file_path} ({len(content)} chars)")
        return content

    def write_jsonl(
        self,
        chunks: List[Dict[str, Any]],
        output_file: str,
        output_dir: Optional[str] = None,
    ) -> str:
        """
        Write chunks to JSONL file.

        Args:
            chunks: List of chunk dictionaries
            output_file: Output filename
            output_dir: Optional output directory (uses default if not provided)

        Returns:
            Path to written file
        """
        output_path = Path(output_dir) if output_dir else self.output_dir
        output_path.mkdir(parents=True, exist_ok=True)

        file_path = output_path / output_file

        with open(file_path, 'w', encoding='utf-8') as f:
            for chunk in chunks:
                # Write each chunk as a JSON line
                json_line = json.dumps(chunk, ensure_ascii=False)
                f.write(json_line + '\n')

        logger.info(f"Wrote {len(chunks)} chunks to {file_path}")
        return str(file_path)

    def read_jsonl(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Read JSONL file.

        Args:
            file_path: Path to JSONL file

        Returns:
            List of chunk dictionaries
        """
        chunks = []

        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    chunk = json.loads(line.strip())
                    chunks.append(chunk)
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing line {line_num} in {file_path}: {e}")

        logger.debug(f"Read {len(chunks)} chunks from {file_path}")
        return chunks

    def write_metadata(
        self,
        filename: str,
        metadata: Dict[str, Any],
        output_dir: Optional[str] = None,
    ):
        """
        Write metadata file.

        Args:
            filename: Base filename
            metadata: Metadata dictionary
            output_dir: Optional output directory
        """
        output_path = Path(output_dir) if output_dir else self.output_dir
        output_path.mkdir(parents=True, exist_ok=True)

        meta_file = output_path / f"{filename}.meta.json"

        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)

        logger.debug(f"Wrote metadata to {meta_file}")

    def read_metadata(self, filename: str, output_dir: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Read metadata file.

        Args:
            filename: Base filename
            output_dir: Optional output directory

        Returns:
            Metadata dictionary or None if not found
        """
        output_path = Path(output_dir) if output_dir else self.output_dir
        meta_file = output_path / f"{filename}.meta.json"

        if not meta_file.exists():
            return None

        with open(meta_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        return metadata

    def list_processed_files(self, output_dir: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all processed JSONL files.

        Args:
            output_dir: Optional output directory

        Returns:
            List of file info dictionaries
        """
        output_path = Path(output_dir) if output_dir else self.output_dir

        if not output_path.exists():
            return []

        files = []
        for jsonl_file in output_path.glob("*.jsonl"):
            # Get file stats
            stats = jsonl_file.stat()
            size_mb = stats.st_size / (1024 * 1024)

            # Read metadata if exists
            metadata = self.read_metadata(jsonl_file.stem, output_dir)

            # Count chunks
            try:
                chunks = self.read_jsonl(str(jsonl_file))
                chunk_count = len(chunks)
            except Exception as e:
                logger.error(f"Error reading {jsonl_file}: {e}")
                chunk_count = 0

            file_info = {
                "filename": jsonl_file.name,
                "source": metadata.get('source', '') if metadata else '',
                "chunks": chunk_count,
                "size_mb": round(size_mb, 2),
                "processed_date": metadata.get('processed_date', '') if metadata else '',
                "quality_issues": metadata.get('quality_issues', []) if metadata else [],
            }
            files.append(file_info)

        logger.debug(f"Found {len(files)} processed files")
        return files

    def delete_processed_file(self, filename: str, output_dir: Optional[str] = None) -> bool:
        """
        Delete processed file and its metadata.

        Args:
            filename: Filename to delete
            output_dir: Optional output directory

        Returns:
            True if successful
        """
        output_path = Path(output_dir) if output_dir else self.output_dir

        jsonl_file = output_path / filename
        meta_file = output_path / f"{Path(filename).stem}.meta.json"

        success = False

        # Delete JSONL file
        if jsonl_file.exists():
            jsonl_file.unlink()
            logger.info(f"Deleted {jsonl_file}")
            success = True

        # Delete metadata file
        if meta_file.exists():
            meta_file.unlink()
            logger.info(f"Deleted {meta_file}")

        return success

    def get_file_size_stats(self, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Get size statistics for processed files.

        Args:
            output_dir: Optional output directory

        Returns:
            Statistics dictionary
        """
        output_path = Path(output_dir) if output_dir else self.output_dir

        if not output_path.exists():
            return {"total_files": 0, "total_size_gb": 0.0}

        total_size = 0
        file_count = 0

        for jsonl_file in output_path.glob("*.jsonl"):
            total_size += jsonl_file.stat().st_size
            file_count += 1

        return {
            "total_files": file_count,
            "total_size_gb": round(total_size / (1024 ** 3), 3),
        }

    def is_screenplay(self, filename: str) -> bool:
        """
        Detect if file is a screenplay based on filename.

        Args:
            filename: Filename to check

        Returns:
            True if appears to be screenplay
        """
        screenplay_keywords = ['script', 'screenplay', 'teleplay']
        filename_lower = filename.lower()

        return any(keyword in filename_lower for keyword in screenplay_keywords)
