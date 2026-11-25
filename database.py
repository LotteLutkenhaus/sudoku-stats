import logging
import os
from collections.abc import Generator
from contextlib import contextmanager
from datetime import timedelta
from typing import Any, cast

from sqlalchemy import (
    Column,
    DateTime,
    Index,
    Integer,
    Interval,
    String,
    create_engine,
    func,
)
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.sql.dml import ReturningInsert

from google_utils import get_secret
from models import ParsedSudokuResult, ScreenshotMetadata

logger = logging.getLogger(__name__)

# SQLAlchemy Base
Base = declarative_base()


class PuzzleSolution(Base):  # type: ignore[valid-type,misc]
    """SQLAlchemy model for puzzle solutions table."""

    __tablename__ = "puzzle_solutions"
    __table_args__ = (
        Index("idx_puzzle_solutions_unique_solve", "solved_at", "difficulty", unique=True),
    )

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
def get_db_session() -> Generator[Session, Any]:
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
) -> int | None:
    """
    Insert a new sudoku result into the PostgreSQL database.
    """
    # Convert seconds to timedelta for PostgreSQL interval
    solving_time = timedelta(seconds=parsed_result.time_to_solve)

    statement: ReturningInsert[tuple[int]] = (
        insert(PuzzleSolution)
        .values(
            solved_at=screenshot_metadata.metadata.time,
            time_to_solve=solving_time,
            difficulty=parsed_result.difficulty_level.value,
        )
        .on_conflict_do_nothing(index_elements=["solved_at", "difficulty"])
        .returning(PuzzleSolution.id)
    )

    with get_db_session() as session:
        puzzle_id = cast(int | None, session.execute(statement).scalar_one_or_none())

    if puzzle_id is None:
        logger.info("Puzzle solution already recorded, skipping")
    else:
        logger.info(f"Inserted puzzle solution with ID: {puzzle_id}")
    return puzzle_id
