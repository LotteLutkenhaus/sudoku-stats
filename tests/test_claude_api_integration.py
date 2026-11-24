"""
Integration test for the screenshot -> Claude result flow.

Makes an API call to the Anthropic API so costs a (small) amount.

Skipped unless RUN_CLAUDE_TESTS=1 and ANTHROPIC_API_KEY are set, e.g.:
    RUN_CLAUDE_TESTS=1 ANTHROPIC_API_KEY=... pytest tests/test_claude_api_integration.py
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from claude_api import process_screenshot
from google_drive import _prepare_image_for_claude
from models import SudokuDifficulty

FIXTURES = Path(__file__).parent / "fixtures"

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_CLAUDE_TESTS") != "1" or not os.getenv("ANTHROPIC_API_KEY"),
    reason="set RUN_CLAUDE_TESTS=1 and ANTHROPIC_API_KEY to call the real Claude API",
)


@pytest.mark.parametrize(
    ("fixture", "expected_difficulty", "expected_seconds"),
    [
        ("screenshot_hard.png", SudokuDifficulty.HARD, 5 * 60 + 43),
        ("screenshot_medium.png", SudokuDifficulty.MEDIUM, 11 * 60 + 19),
    ],
)
def test_process_screenshot_against_claude_api(
    fixture: str, expected_difficulty: SudokuDifficulty, expected_seconds: int
) -> None:
    image = _prepare_image_for_claude((FIXTURES / fixture).read_bytes())

    with patch("claude_api.get_secret", return_value=os.environ["ANTHROPIC_API_KEY"]):
        result = process_screenshot(image)

    assert result.difficulty_level == expected_difficulty
    assert result.time_to_solve == expected_seconds
