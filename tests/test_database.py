from collections.abc import Iterator
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, select

from database import (
    Base,
    PuzzleSolution,
    get_database_url,
    get_db_session,
    insert_sudoku_result,
)
from models import ParsedSudokuResult, ScreenshotMetadata


@pytest.fixture
def database_url(tmp_path: Path) -> Iterator[str]:
    url = f"sqlite:///{tmp_path / 'test.db'}"
    Base.metadata.create_all(create_engine(url))
    with patch("database.get_database_url", return_value=url):
        yield url


def test_insert_sudoku_result_stores_solution(database_url: str) -> None:
    parsed_result = ParsedSudokuResult.model_validate(
        {"difficulty_level": "Medium", "time_to_solve": "12:37"}
    )
    metadata = ScreenshotMetadata.model_validate(
        {"imageMediaMetadata": {"time": "2025:03:14 21:45:09"}}
    )

    puzzle_id = insert_sudoku_result(parsed_result=parsed_result, screenshot_metadata=metadata)

    with get_db_session() as session:
        solution = session.execute(select(PuzzleSolution)).scalar_one()
        assert solution.id == puzzle_id
        assert solution.solved_at == datetime(2025, 3, 14, 21, 45, 9)
        assert solution.time_to_solve == timedelta(minutes=12, seconds=37)
        assert solution.difficulty == "medium"
        assert solution.created_at is not None


def test_insert_sudoku_result_skips_already_recorded_solve(database_url: str) -> None:
    parsed_result = ParsedSudokuResult.model_validate(
        {"difficulty_level": "Hard", "time_to_solve": "16:56"}
    )
    metadata = ScreenshotMetadata.model_validate(
        {"imageMediaMetadata": {"time": "2026:11:16 07:54:44"}}
    )

    first_id = insert_sudoku_result(parsed_result=parsed_result, screenshot_metadata=metadata)
    second_id = insert_sudoku_result(parsed_result=parsed_result, screenshot_metadata=metadata)

    assert first_id is not None
    assert second_id is None
    with get_db_session() as session:
        assert len(session.execute(select(PuzzleSolution)).all()) == 1


def test_get_db_session_rolls_back_on_error(database_url: str) -> None:
    with pytest.raises(RuntimeError), get_db_session() as session:
        session.add(
            PuzzleSolution(
                solved_at=datetime(2025, 3, 14), time_to_solve=timedelta(1), difficulty="easy"
            )
        )
        session.flush()
        raise RuntimeError("boom")

    with get_db_session() as session:
        assert session.execute(select(PuzzleSolution)).first() is None


def test_get_database_url_prefers_dev_environment_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL_DEV", "postgresql://dev")
    with patch("database.get_secret") as get_secret:
        assert get_database_url() == "postgresql://dev"
        get_secret.assert_not_called()


def test_get_database_url_falls_back_to_secret_manager(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL_DEV", raising=False)
    with patch("database.get_secret", return_value="postgresql://prod") as get_secret:
        assert get_database_url() == "postgresql://prod"
        get_secret.assert_called_once_with("neon-database-connection-string")
