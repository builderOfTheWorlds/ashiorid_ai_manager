"""
Text normalization service.
"""

from typing import Dict, Any
import sys
sys.path.append('../..')
from shared.logging_config import get_logger
from src.utils.text_utils import (
    normalize_unicode,
    standardize_quotes,
    remove_excessive_whitespace,
    correct_ocr_errors,
    remove_page_artifacts,
    flatten_screenplay_format,
    detect_encoding,
)

logger = get_logger(__name__)


class NormalizerService:
    """Service for text normalization."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize normalizer service.

        Args:
            config: Service configuration
        """
        self.config = config
        self.norm_config = config.get('processing', {}).get('normalization', {})

    def normalize_text(self, text: str, is_screenplay: bool = False) -> str:
        """
        Normalize text according to configuration.

        Args:
            text: Input text
            is_screenplay: Whether the text is in screenplay format

        Returns:
            Normalized text
        """
        logger.debug(f"Normalizing text (length: {len(text)}, screenplay: {is_screenplay})")

        # Unicode normalization
        unicode_form = self.norm_config.get('unicode_form', 'NFKC')
        text = normalize_unicode(text, form=unicode_form)

        # Standardize quotes
        if self.norm_config.get('standardize_quotes', True):
            text = standardize_quotes(text)

        # Flatten screenplay format
        if is_screenplay:
            logger.info("Flattening screenplay format to prose")
            text = flatten_screenplay_format(text)

        # OCR error correction
        if self.norm_config.get('correct_ocr_errors', True):
            text = correct_ocr_errors(text)

        # Remove page artifacts
        if self.norm_config.get('remove_page_artifacts', True):
            text = remove_page_artifacts(text)

        # Remove excessive whitespace (do this last)
        if self.norm_config.get('remove_excessive_whitespace', True):
            text = remove_excessive_whitespace(text)

        logger.debug(f"Normalization complete (new length: {len(text)})")
        return text

    def normalize_file(self, file_path: str, is_screenplay: bool = False) -> str:
        """
        Normalize text from a file.

        Args:
            file_path: Path to the file
            is_screenplay: Whether the file is a screenplay

        Returns:
            Normalized text
        """
        # Detect encoding
        encoding = detect_encoding(file_path)
        logger.info(f"Detected encoding: {encoding} for file: {file_path}")

        # Read file with detected encoding
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                text = f.read()
        except UnicodeDecodeError:
            logger.warning(f"Failed to decode with {encoding}, trying utf-8 with errors='replace'")
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                text = f.read()

        # Normalize
        return self.normalize_text(text, is_screenplay=is_screenplay)
