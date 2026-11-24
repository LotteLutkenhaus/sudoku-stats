from datetime import datetime

import pytest
from pydantic import ValidationError

from models import (
    ClaudeSudokuExtraction,
    ParsedSudokuResult,
    ScreenshotMetadata,
    SudokuDifficulty,
)


@pytest.mark.parametrize(
    ("raw_time", "expected_seconds"),
    [("12:37", 757), ("0:05", 5), ("1:00", 60), ("75:00", 4500)],
)
def test_time_to_solve_is_parsed_to_seconds(raw_time: str, expected_seconds: int) -> None:
    result = ParsedSudokuResult.model_validate(
        {"difficulty_level": "easy", "time_to_solve": raw_time}
    )
    assert result.time_to_solve == expected_seconds


@pytest.mark.parametrize("raw_difficulty", ["Hard", "HARD", "hard"])
def test_difficulty_is_case_insensitive(raw_difficulty: str) -> None:
    result = ParsedSudokuResult.model_validate(
        {"difficulty_level": raw_difficulty, "time_to_solve": "1:00"}
    )
    assert result.difficulty_level == SudokuDifficulty.HARD


def test_unknown_difficulty_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ParsedSudokuResult.model_validate({"difficulty_level": "expert", "time_to_solve": "1:00"})


@pytest.mark.parametrize("raw_time", ["12", "12:3a", ""])
def test_malformed_time_is_rejected(raw_time: str) -> None:
    with pytest.raises(ValidationError):
        ParsedSudokuResult.model_validate({"difficulty_level": "easy", "time_to_solve": raw_time})


def test_screenshot_metadata_parses_google_timestamp() -> None:
    metadata = ScreenshotMetadata.model_validate(
        {"imageMediaMetadata": {"time": "2025:03:14 21:45:09"}}
    )
    assert metadata.metadata.time == datetime(2025, 3, 14, 21, 45, 9)


def test_claude_extraction_converts_to_parsed_result() -> None:
    extraction = ClaudeSudokuExtraction(difficulty_level="Hard", time_to_solve="12:37")
    result = ParsedSudokuResult.model_validate(extraction.model_dump())
    assert result.difficulty_level == SudokuDifficulty.HARD
    assert result.time_to_solve == 757


@pytest.mark.parametrize(
    ("raw_difficulty", "raw_time"),
    [("Expert", "12:37"), ("hard", "12:37"), ("Hard", "12"), ("Hard", "12:3")],
)
def test_claude_extraction_rejects_unexpected_values(raw_difficulty: str, raw_time: str) -> None:
    with pytest.raises(ValidationError):
        ClaudeSudokuExtraction.model_validate(
            {"difficulty_level": raw_difficulty, "time_to_solve": raw_time}
        )
