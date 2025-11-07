"""
Tests for text normalization service.
"""

import sys
sys.path.append('..')

from src.services.normalizer import NormalizerService


def test_normalizer_basic():
    """Test basic text normalization."""
    config = {
        'processing': {
            'normalization': {
                'unicode_form': 'NFKC',
                'standardize_quotes': True,
                'remove_excessive_whitespace': True,
                'correct_ocr_errors': True,
                'remove_page_artifacts': True,
            }
        }
    }

    normalizer = NormalizerService(config)

    # Test smart quotes
    text = '"Hello," she said'
    result = normalizer.normalize_text(text)
    assert '"' in result
    assert '"' not in result

    # Test excessive whitespace
    text = "Hello    world\n\n\n\nNew paragraph"
    result = normalizer.normalize_text(text)
    assert "    " not in result
    assert "\n\n\n\n" not in result

    print("✓ Normalizer tests passed")


def test_screenplay_flattening():
    """Test screenplay format flattening."""
    config = {
        'processing': {
            'normalization': {
                'unicode_form': 'NFKC',
                'standardize_quotes': True,
                'remove_excessive_whitespace': True,
                'correct_ocr_errors': True,
                'remove_page_artifacts': True,
            }
        }
    }

    normalizer = NormalizerService(config)

    screenplay_text = """
INT. COFFEE SHOP - DAY

JOHN
Hello there!

JANE
(smiling)
Hi, how are you?

John sits down across from Jane.
"""

    result = normalizer.normalize_text(screenplay_text, is_screenplay=True)

    # Check that scene headings are removed
    assert "INT." not in result
    assert "COFFEE SHOP" not in result

    # Check that dialogue is preserved
    assert "Hello there" in result or "Hi, how are you" in result

    print("✓ Screenplay flattening tests passed")


if __name__ == "__main__":
    test_normalizer_basic()
    test_screenplay_flattening()
    print("\nAll normalizer tests passed!")
