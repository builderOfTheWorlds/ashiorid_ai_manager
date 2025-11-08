"""
PDF text extraction service with OCR fallback.
"""

import io
from typing import Dict, Tuple
from PIL import Image

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False

import sys
sys.path.append('../..')
from shared.logging_config import get_logger

logger = get_logger(__name__)


class PDFExtractor:
    """Service for extracting text from PDF files with OCR fallback."""

    def __init__(self, config: Dict = None):
        self.config = config or {}

        # PDF extraction settings
        pdf_config = self.config.get("pdf_extraction", {})
        self.min_text_length = pdf_config.get("min_text_length", 50)
        self.min_alpha_ratio = pdf_config.get("min_alpha_ratio", 0.6)
        self.ocr_enabled = pdf_config.get("ocr_enabled", True)
        self.ocr_dpi = pdf_config.get("ocr_dpi", 300)
        self.ocr_language = pdf_config.get("ocr_language", "eng")

        # Check dependencies
        if not PYMUPDF_AVAILABLE:
            raise ImportError("PyMuPDF (fitz) is required for PDF processing")

        if self.ocr_enabled and not PYTESSERACT_AVAILABLE:
            logger.warning("pytesseract not available, OCR will be disabled")
            self.ocr_enabled = False

    def extract_text(self, pdf_bytes: bytes) -> Tuple[str, Dict]:
        """
        Extract text from PDF with hybrid approach (text + OCR fallback).

        Args:
            pdf_bytes: PDF file content as bytes

        Returns:
            Tuple of (extracted_text, metadata)
        """
        metadata = {
            "extraction_method": None,
            "page_count": 0,
            "confidence_score": 0.0,
            "has_images": False,
            "processing_time_ms": 0,
        }

        try:
            import time
            start_time = time.time()

            # Open PDF from bytes
            pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
            metadata["page_count"] = len(pdf_document)

            # Try text extraction first
            extracted_text = self._extract_text_layer(pdf_document, metadata)

            # Check text quality
            if self._is_text_quality_poor(extracted_text):
                logger.info(
                    f"Poor text quality detected (length={len(extracted_text)}), "
                    f"attempting OCR fallback"
                )

                if self.ocr_enabled:
                    # Fallback to OCR
                    ocr_text = self._extract_with_ocr(pdf_document, metadata)

                    if len(ocr_text) > len(extracted_text):
                        extracted_text = ocr_text
                        metadata["extraction_method"] = "ocr"
                    else:
                        metadata["extraction_method"] = "hybrid"
                else:
                    logger.warning("OCR disabled, using poor quality text extraction")
                    metadata["extraction_method"] = "text"
            else:
                metadata["extraction_method"] = "text"

            # Calculate confidence score
            metadata["confidence_score"] = self._calculate_confidence(extracted_text)

            # Processing time
            metadata["processing_time_ms"] = int((time.time() - start_time) * 1000)

            pdf_document.close()

            logger.info(
                f"PDF extraction completed: method={metadata['extraction_method']}, "
                f"pages={metadata['page_count']}, "
                f"confidence={metadata['confidence_score']:.2f}, "
                f"text_length={len(extracted_text)}, "
                f"time_ms={metadata['processing_time_ms']}"
            )

            return extracted_text, metadata

        except Exception as e:
            logger.error(f"PDF extraction failed: {e}", exc_info=True)
            raise

    def _extract_text_layer(self, pdf_document, metadata: Dict) -> str:
        """
        Extract text from PDF's native text layer.

        Args:
            pdf_document: PyMuPDF document object
            metadata: Metadata dictionary to update

        Returns:
            Extracted text
        """
        text_parts = []
        has_images = False

        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]

            # Extract text
            page_text = page.get_text()
            text_parts.append(page_text)

            # Check for images
            if not has_images:
                image_list = page.get_images()
                if image_list:
                    has_images = True

        metadata["has_images"] = has_images

        return "\n".join(text_parts)

    def _extract_with_ocr(self, pdf_document, metadata: Dict) -> str:
        """
        Extract text using OCR on rendered PDF pages.

        Args:
            pdf_document: PyMuPDF document object
            metadata: Metadata dictionary to update

        Returns:
            OCR extracted text
        """
        if not self.ocr_enabled or not PYTESSERACT_AVAILABLE:
            logger.warning("OCR extraction requested but not available")
            return ""

        text_parts = []

        try:
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]

                # Render page to image at specified DPI
                mat = fitz.Matrix(self.ocr_dpi / 72, self.ocr_dpi / 72)
                pix = page.get_pixmap(matrix=mat)

                # Convert to PIL Image
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))

                # Perform OCR
                page_text = pytesseract.image_to_string(
                    img,
                    lang=self.ocr_language,
                    config='--psm 1'  # Automatic page segmentation with OSD
                )

                text_parts.append(page_text)

                logger.debug(f"OCR page {page_num + 1}/{len(pdf_document)}")

        except Exception as e:
            logger.error(f"OCR extraction failed: {e}", exc_info=True)
            raise

        return "\n".join(text_parts)

    def _is_text_quality_poor(self, text: str) -> bool:
        """
        Check if extracted text quality is poor.

        Args:
            text: Extracted text

        Returns:
            True if quality is poor
        """
        text = text.strip()

        # Check minimum length
        if len(text) < self.min_text_length:
            return True

        # Check alphabetic character ratio
        if len(text) > 0:
            alpha_count = sum(c.isalpha() or c.isspace() for c in text)
            alpha_ratio = alpha_count / len(text)

            if alpha_ratio < self.min_alpha_ratio:
                return True

        return False

    def _calculate_confidence(self, text: str) -> float:
        """
        Calculate extraction confidence score.

        Args:
            text: Extracted text

        Returns:
            Confidence score (0.0 - 1.0)
        """
        if not text or len(text.strip()) == 0:
            return 0.0

        text = text.strip()

        # Factors for confidence calculation
        length_score = min(len(text) / 1000, 1.0)  # Max at 1000 characters

        # Alphabetic ratio
        alpha_count = sum(c.isalpha() or c.isspace() for c in text)
        alpha_ratio = alpha_count / len(text) if len(text) > 0 else 0

        # Word count (simple whitespace split)
        word_count = len(text.split())
        word_score = min(word_count / 100, 1.0)  # Max at 100 words

        # Combined confidence
        confidence = (length_score * 0.3 + alpha_ratio * 0.5 + word_score * 0.2)

        return round(confidence, 2)
