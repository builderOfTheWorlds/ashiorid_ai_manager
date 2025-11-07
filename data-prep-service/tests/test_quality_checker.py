"""
Tests for quality checking service.
"""

import sys
sys.path.append('..')

from src.services.quality_checker import QualityCheckerService


def test_quality_checker_short_content():
    """Test quality checker detects short content."""
    config = {
        'processing': {
            'quality': {
                'check_duplicates': True,
                'detect_corruption': True,
                'flag_incomplete': True,
                'min_content_length': 50,
            }
        }
    }

    checker = QualityCheckerService(config)

    # Test short content
    short_text = "Too short"
    issues = checker.check_quality(short_text)

    assert len(issues) > 0, "Should detect short content"
    assert any("too short" in issue.lower() for issue in issues)

    print("✓ Short content detection passed")


def test_quality_checker_corruption():
    """Test quality checker detects corruption."""
    config = {
        'processing': {
            'quality': {
                'check_duplicates': True,
                'detect_corruption': True,
                'flag_incomplete': True,
                'min_content_length': 50,
            }
        }
    }

    checker = QualityCheckerService(config)

    # Test corrupted text with replacement characters
    corrupted_text = "This text has some � replacement characters in it. " * 3
    issues = checker.check_quality(corrupted_text)

    assert len(issues) > 0, "Should detect corruption"
    assert any("replacement character" in issue.lower() for issue in issues)

    print("✓ Corruption detection passed")


def test_quality_checker_acceptable():
    """Test quality checker accepts good content."""
    config = {
        'processing': {
            'quality': {
                'check_duplicates': True,
                'detect_corruption': True,
                'flag_incomplete': True,
                'min_content_length': 50,
            }
        }
    }

    checker = QualityCheckerService(config)

    # Test good content
    good_text = "This is a nice long piece of text that should pass all quality checks. " * 5
    issues = checker.check_quality(good_text)

    # Should be acceptable (might have minor issues but not critical)
    assert checker.is_acceptable(issues), "Good content should be acceptable"

    print("✓ Acceptable content detection passed")


if __name__ == "__main__":
    test_quality_checker_short_content()
    test_quality_checker_corruption()
    test_quality_checker_acceptable()
    print("\nAll quality checker tests passed!")
