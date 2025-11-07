"""
Text processing utilities for Data Preparation Service.
"""

import re
import unicodedata
from typing import List, Tuple
import chardet


# OCR error corrections mapping
OCR_CORRECTIONS = {
    r'\brn\b': 'm',  # rn -> m
    r'\bvv\b': 'w',  # vv -> w
    r'\bl\b(?=[I])': 'I',  # l -> I (before I)
    r'(?<=[a-z])l(?=[A-Z])': 'I',  # l -> I (between lower and upper)
    r'\b0\b(?=[A-Za-z])': 'O',  # 0 -> O (before letters)
}


def detect_encoding(file_path: str) -> str:
    """
    Detect file encoding.

    Args:
        file_path: Path to the file

    Returns:
        Detected encoding name
    """
    with open(file_path, 'rb') as f:
        raw_data = f.read(10000)  # Read first 10KB
        result = chardet.detect(raw_data)
        return result['encoding'] or 'utf-8'


def normalize_unicode(text: str, form: str = 'NFKC') -> str:
    """
    Normalize Unicode characters.

    Args:
        text: Input text
        form: Normalization form (NFC, NFKC, NFD, NFKD)

    Returns:
        Normalized text
    """
    return unicodedata.normalize(form, text)


def standardize_quotes(text: str) -> str:
    """
    Standardize smart quotes to regular quotes.

    Args:
        text: Input text

    Returns:
        Text with standardized quotes
    """
    # Smart single quotes to regular
    text = text.replace(''', "'").replace(''', "'")
    # Smart double quotes to regular
    text = text.replace('"', '"').replace('"', '"')
    # Other quote-like characters
    text = text.replace('‹', '<').replace('›', '>')
    text = text.replace('«', '"').replace('»', '"')
    return text


def remove_excessive_whitespace(text: str) -> str:
    """
    Remove excessive whitespace while preserving paragraph breaks.

    Args:
        text: Input text

    Returns:
        Text with normalized whitespace
    """
    # Replace tabs with spaces
    text = text.replace('\t', ' ')

    # Replace multiple spaces with single space
    text = re.sub(r' +', ' ', text)

    # Replace more than 2 consecutive newlines with 2
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Remove spaces at start/end of lines
    text = re.sub(r' *\n *', '\n', text)

    return text.strip()


def correct_ocr_errors(text: str) -> str:
    """
    Correct common OCR errors.

    Args:
        text: Input text

    Returns:
        Text with OCR errors corrected
    """
    for pattern, replacement in OCR_CORRECTIONS.items():
        text = re.sub(pattern, replacement, text)
    return text


def remove_page_artifacts(text: str) -> str:
    """
    Remove page numbers, headers, and footers.

    Args:
        text: Input text

    Returns:
        Text with artifacts removed
    """
    # Remove standalone page numbers (number on its own line)
    text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)

    # Remove common header patterns (e.g., "Chapter 1 - 23")
    text = re.sub(r'^[A-Z][a-z]+ \d+ - \d+\s*$', '', text, flags=re.MULTILINE)

    # Remove footer patterns (e.g., "Page 23")
    text = re.sub(r'^Page \d+\s*$', '', text, flags=re.MULTILINE)

    # Remove consecutive hyphens (dividers)
    text = re.sub(r'^-{3,}\s*$', '', text, flags=re.MULTILINE)

    return text


def flatten_screenplay_format(text: str) -> str:
    """
    Flatten screenplay format to prose.
    Removes scene headings and character name labels, keeping only dialogue and action.

    Args:
        text: Input screenplay text

    Returns:
        Flattened prose text
    """
    lines = text.split('\n')
    prose_lines = []

    for line in lines:
        stripped = line.strip()

        # Skip scene headings (INT./EXT. or FADE IN/OUT)
        if re.match(r'^(INT\.|EXT\.|FADE|CUT TO|DISSOLVE)', stripped):
            continue

        # Skip character names (all caps, centered-ish)
        if stripped.isupper() and len(stripped) < 30 and not any(c in stripped for c in '.!?'):
            continue

        # Skip parentheticals (stage directions in parentheses)
        if re.match(r'^\([^)]+\)$', stripped):
            continue

        # Keep dialogue and action
        if stripped:
            prose_lines.append(stripped)

    return ' '.join(prose_lines)


def detect_chapter_boundaries(text: str) -> List[Tuple[int, str]]:
    """
    Detect chapter/section boundaries in text.

    Args:
        text: Input text

    Returns:
        List of (position, chapter_title) tuples
    """
    boundaries = []

    # Common chapter patterns
    patterns = [
        r'^(Chapter|CHAPTER)\s+(\d+|[IVXLCDM]+)(\s*[:-]\s*.+)?$',  # Chapter 1, Chapter I
        r'^(Part|PART)\s+(\d+|[IVXLCDM]+)(\s*[:-]\s*.+)?$',  # Part 1, Part I
        r'^(Book|BOOK)\s+(\d+|[IVXLCDM]+)(\s*[:-]\s*.+)?$',  # Book 1
        r'^(Prologue|PROLOGUE|Epilogue|EPILOGUE)$',  # Prologue/Epilogue
        r'^(Act|ACT)\s+(\d+|[IVXLCDM]+)$',  # Act 1
        r'^(\d+)\s*$',  # Just a number
    ]

    lines = text.split('\n')
    position = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        for pattern in patterns:
            if re.match(pattern, stripped):
                boundaries.append((position, stripped))
                break
        position += len(line) + 1  # +1 for newline

    return boundaries


def detect_scene_boundaries(text: str) -> List[int]:
    """
    Detect scene boundaries in text.

    Args:
        text: Input text

    Returns:
        List of character positions where scenes start
    """
    boundaries = []

    # Scene break markers
    patterns = [
        r'^\s*\*\s*\*\s*\*\s*$',  # * * *
        r'^\s*#\s*$',  # #
        r'^Scene \d+',  # Scene 1
        r'^\s*---\s*$',  # ---
    ]

    lines = text.split('\n')
    position = 0

    for line in lines:
        stripped = line.strip()
        for pattern in patterns:
            if re.match(pattern, stripped):
                boundaries.append(position)
                break
        position += len(line) + 1

    return boundaries


def detect_corruption(text: str) -> List[str]:
    """
    Detect encoding corruption and other issues.

    Args:
        text: Input text

    Returns:
        List of corruption issues found
    """
    issues = []

    # Check for replacement character
    if '�' in text:
        count = text.count('�')
        issues.append(f"Found {count} replacement character(s) (�)")

    # Check for common mojibake patterns
    mojibake_patterns = [
        (r'â€™', "Mojibake detected (likely UTF-8 decoded as Latin-1)"),
        (r'Ã©', "Mojibake detected (likely UTF-8 decoded as Latin-1)"),
        (r'â€"', "Mojibake detected (likely UTF-8 decoded as Latin-1)"),
    ]

    for pattern, message in mojibake_patterns:
        if re.search(pattern, text):
            if message not in issues:
                issues.append(message)

    # Check for excessive special characters
    special_char_ratio = len(re.findall(r'[^\w\s.,!?;:\'"()-]', text)) / max(len(text), 1)
    if special_char_ratio > 0.1:
        issues.append(f"High ratio of special characters: {special_char_ratio:.2%}")

    return issues


def detect_duplicate_paragraphs(text: str, min_length: int = 100) -> List[str]:
    """
    Detect duplicate paragraphs in text.

    Args:
        text: Input text
        min_length: Minimum paragraph length to check

    Returns:
        List of duplicate paragraphs found
    """
    paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) >= min_length]

    seen = set()
    duplicates = []

    for para in paragraphs:
        if para in seen:
            duplicates.append(para[:100] + '...' if len(para) > 100 else para)
        else:
            seen.add(para)

    return duplicates


def is_incomplete_text(text: str) -> bool:
    """
    Check if text appears to be incomplete (truncated).

    Args:
        text: Input text

    Returns:
        True if text appears incomplete
    """
    # Check if ends with incomplete sentence
    text = text.strip()

    if not text:
        return True

    # If doesn't end with sentence-ending punctuation
    if text[-1] not in '.!?"':
        # But has reasonable length, might be intentional
        if len(text) < 1000:
            return True

    # Check for truncation markers
    truncation_markers = ['[truncated]', '...', '(continued)', '[end of preview]']
    text_lower = text[-200:].lower()

    for marker in truncation_markers:
        if marker in text_lower:
            return True

    return False


def count_tokens_estimate(text: str) -> int:
    """
    Estimate token count (rough approximation).
    For accurate counting, use tiktoken in the chunker service.

    Args:
        text: Input text

    Returns:
        Estimated token count
    """
    # Rough estimate: ~4 characters per token
    return len(text) // 4
