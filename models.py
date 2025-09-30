from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, Field


class SudokuDifficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class WebhookPayload(BaseModel):
    file_id: str


def get_solved_time_in_seconds(value: str) -> int:
    minutes, seconds = map(int, value.split(":"))
    return (minutes * 60) + seconds


def parse_googles_funky_timestamp(value: str) -> datetime:
    return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")


def uncapitalize_string(value: str) -> str:
    return value.lower()


class ParsedSudokuResult(BaseModel):
    difficulty_level: Annotated[SudokuDifficulty, BeforeValidator(uncapitalize_string)]
    time_to_solve: Annotated[int, BeforeValidator(get_solved_time_in_seconds)]


class ImageMetaData(BaseModel):
    time: Annotated[datetime, BeforeValidator(parse_googles_funky_timestamp)]


class ScreenshotMetadata(BaseModel):
    metadata: ImageMetaData = Field(alias="imageMediaMetadata")
