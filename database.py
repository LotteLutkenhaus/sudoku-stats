import logging
import os
from collections.abc import Generator
from contextlib import contextmanager
from datetime import timedelta
from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    Interval,
    String,
    create_engine,
    func,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from google_utils import get_secret
from models import ParsedSudokuResult, ScreenshotMetadata

logger = logging.getLogger(__name__)

# SQLAlchemy Base
Base = declarative_base()


class PuzzleSolution(Base):  # type: ignore[valid-type,misc]
    """SQLAlchemy model for puzzle solutions table."""

    __tablename__ = "puzzle_solutions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    solved_at = Column(DateTime(timezone=True), nullable=False)
    time_to_solve = Column(Interval, nullable=False)
    difficulty = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


def get_database_url() -> str:
    """
    Get database connection URL from environment variable or Google Secret Manager.

    Priority:
    1. DATABASE_URL_DEV environment variable (for local development)
    2. Google Secret Manager (for production)
    """
    # Check for local environment variable first
    connection_string = os.getenv("DATABASE_URL_DEV")

    if connection_string:
        logger.info("Using development database connection")
        return connection_string

    # Fall back to Google Secret Manager
    secret_name = "neon-database-connection-string"
    logger.info(f"Using database URL from Google Secret Manager: {secret_name}")
    connection_string = get_secret(secret_name)

    return connection_string


@contextmanager
def get_db_session() -> Generator[Session, Any, None]:
    """
    Context manager for database sessions.
    """
    engine = create_engine(get_database_url())
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        yield session
        session.commit()
    except Exception as e:
        logger.error(f"Database error: {e}")
        session.rollback()
        raise
    finally:
        session.close()


def insert_sudoku_result(
    parsed_result: ParsedSudokuResult, screenshot_metadata: ScreenshotMetadata
) -> int:
    """
    Insert a new sudoku result into the PostgreSQL database.
    """
    with get_db_session() as session:
        # Convert seconds to timedelta for PostgreSQL interval
        solving_time = timedelta(seconds=parsed_result.time_to_solve)

        # Create new puzzle solution record
        puzzle_solution = PuzzleSolution(
            solved_at=screenshot_metadata.metadata.time,
            time_to_solve=solving_time,
            difficulty=parsed_result.difficulty_level.value,
        )

        session.add(puzzle_solution)
        session.flush()
        puzzle_id: int = puzzle_solution.id

        logger.info(f"Inserted puzzle solution with ID: {puzzle_id}")
        return puzzle_id
