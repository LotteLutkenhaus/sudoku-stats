import base64
from unittest.mock import MagicMock, patch

import pytest
from anthropic.types import TextBlock
from pydantic import ValidationError

from claude_api import _parse_claude_response, process_screenshot
from models import SudokuDifficulty

EXPECTED_RESPONSE = '\n    "difficulty_level": "Hard",\n    "time_to_solve": "12:37"\n}'


def test_parse_claude_response_completes_prefilled_json() -> None:
    result = _parse_claude_response(EXPECTED_RESPONSE)
    assert result.difficulty_level == SudokuDifficulty.HARD
    assert result.time_to_solve == 757


def test_parse_claude_response_rejects_invalid_json() -> None:
    with pytest.raises(ValidationError):
        _parse_claude_response("this is not json")


def _mock_client(content: list[TextBlock]) -> MagicMock:
    client = MagicMock()
    client.messages.create.return_value.content = content
    return client


def test_process_screenshot_sends_image_and_parses_response() -> None:
    client = _mock_client([TextBlock(type="text", text=EXPECTED_RESPONSE)])

    with (
        patch("claude_api.get_secret", return_value="test-key"),
        patch("claude_api.Anthropic", return_value=client),
    ):
        result = process_screenshot(b"image-bytes")

    assert result.difficulty_level == SudokuDifficulty.HARD
    assert result.time_to_solve == 757

    messages = client.messages.create.call_args.kwargs["messages"]
    image_block = messages[0]["content"][1]
    assert image_block["source"]["data"] == base64.b64encode(b"image-bytes").decode()
    assert messages[-1] == {"role": "assistant", "content": "{"}


def test_process_screenshot_rejects_multiple_content_blocks() -> None:
    block = TextBlock(type="text", text=EXPECTED_RESPONSE)
    client = _mock_client([block, block])

    with (
        patch("claude_api.get_secret", return_value="test-key"),
        patch("claude_api.Anthropic", return_value=client),
        pytest.raises(AssertionError),
    ):
        process_screenshot(b"image-bytes")
