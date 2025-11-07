"""
Quality checking service.
"""

from typing import Dict, Any, List
import sys
sys.path.append('../..')
from shared.logging_config import get_logger
from src.utils.text_utils import (
    detect_corruption,
    detect_duplicate_paragraphs,
    is_incomplete_text,
)

logger = get_logger(__name__)


class QualityCheckerService:
    """Service for text quality checking."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize quality checker service.

        Args:
            config: Service configuration
        """
        self.config = config
        self.quality_config = config.get('processing', {}).get('quality', {})

    def check_quality(self, text: str, source: str = "") -> List[str]:
        """
        Check text quality and return list of issues.

        Args:
            text: Input text
            source: Source identifier for logging

        Returns:
            List of quality issues found
        """
        issues = []

        logger.debug(f"Checking quality for {source}")

        # Check minimum content length
        min_length = self.quality_config.get('min_content_length', 50)
        if len(text.strip()) < min_length:
            issues.append(f"Content too short: {len(text.strip())} chars (min: {min_length})")

        # Check for corruption
        if self.quality_config.get('detect_corruption', True):
            corruption_issues = detect_corruption(text)
            issues.extend(corruption_issues)

        # Check for duplicates
        if self.quality_config.get('check_duplicates', True):
            duplicates = detect_duplicate_paragraphs(text)
            if duplicates:
                issues.append(f"Found {len(duplicates)} duplicate paragraph(s)")
                logger.debug(f"Duplicate paragraphs: {duplicates[:3]}")  # Log first 3

        # Check for incomplete text
        if self.quality_config.get('flag_incomplete', True):
            if is_incomplete_text(text):
                issues.append("Text appears incomplete or truncated")

        if issues:
            logger.warning(f"Quality issues found in {source}: {issues}")
        else:
            logger.debug(f"No quality issues found in {source}")

        return issues

    def is_acceptable(self, issues: List[str]) -> bool:
        """
        Determine if quality issues are acceptable for processing.

        Args:
            issues: List of quality issues

        Returns:
            True if acceptable, False if should be rejected
        """
        # For now, we accept everything but log issues
        # Could be configured to reject based on severity
        critical_keywords = ['too short', 'completely corrupted']

        for issue in issues:
            for keyword in critical_keywords:
                if keyword in issue.lower():
                    return False

        return True
