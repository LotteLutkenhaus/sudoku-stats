from collections.abc import Iterator
from typing import cast
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask, request

from main import process_sudoku_screenshot

API_KEY = "test-api-key"


@pytest.fixture
def mocks() -> Iterator[dict[str, MagicMock]]:
    with (
        patch("main.get_secret", return_value=API_KEY) as get_secret,
        patch("main.get_screenshot", return_value=b"image-bytes") as get_screenshot,
        patch("main.process_screenshot") as process_screenshot,
        patch("main.get_file_metadata") as get_file_metadata,
        patch("main.insert_sudoku_result") as insert_sudoku_result,
    ):
        yield {
            "get_secret": get_secret,
            "get_screenshot": get_screenshot,
            "process_screenshot": process_screenshot,
            "get_file_metadata": get_file_metadata,
            "insert_sudoku_result": insert_sudoku_result,
        }


def _call_handler(headers: dict[str, str]) -> tuple[dict[str, str], int]:
    with Flask(__name__).test_request_context(
        method="POST", json={"file_id": "drive-file-id"}, headers=headers
    ):
        return cast(tuple[dict[str, str], int], process_sudoku_screenshot(request))


@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "wrong-key"}])
def test_rejects_request_without_valid_api_key(
    mocks: dict[str, MagicMock], headers: dict[str, str]
) -> None:
    body, status = _call_handler(headers)

    assert status == 401
    assert body == {"error": "Unauthorized"}
    mocks["get_screenshot"].assert_not_called()
    mocks["insert_sudoku_result"].assert_not_called()


def test_processes_screenshot_and_stores_result(mocks: dict[str, MagicMock]) -> None:
    body, status = _call_handler({"X-API-Key": API_KEY})

    assert status == 200
    assert body == {"message": "Success"}
    mocks["get_screenshot"].assert_called_once_with(file_id="drive-file-id")
    mocks["process_screenshot"].assert_called_once_with(b"image-bytes")
    mocks["get_file_metadata"].assert_called_once_with(file_id="drive-file-id")
    mocks["insert_sudoku_result"].assert_called_once_with(
        parsed_result=mocks["process_screenshot"].return_value,
        screenshot_metadata=mocks["get_file_metadata"].return_value,
    )


def test_returns_success_when_result_already_recorded(mocks: dict[str, MagicMock]) -> None:
    mocks["insert_sudoku_result"].return_value = None

    body, status = _call_handler({"X-API-Key": API_KEY})

    assert status == 200
    assert body == {"message": "Already recorded"}
