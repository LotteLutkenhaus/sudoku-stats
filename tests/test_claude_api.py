import base64
from unittest.mock import MagicMock, patch

import pytest

from claude_api import process_screenshot
from models import ClaudeSudokuExtraction, ParsedSudokuResult, SudokuDifficulty

EXPECTED_EXTRACTION = ClaudeSudokuExtraction(difficulty_level="Hard", time_to_solve="12:37")


def _mock_client(
    parsed_output: ClaudeSudokuExtraction | None = EXPECTED_EXTRACTION,
    stop_reason: str = "end_turn",
) -> MagicMock:
    client = MagicMock()
    client.messages.parse.return_value.parsed_output = parsed_output
    client.messages.parse.return_value.stop_reason = stop_reason
    return client


def _process_with(client: MagicMock) -> ParsedSudokuResult:
    with (
        patch("claude_api.get_secret", return_value="test-key"),
        patch("claude_api.Anthropic", return_value=client),
    ):
        return process_screenshot(b"image-bytes")


def test_process_screenshot_sends_image_and_parses_response() -> None:
    client = _mock_client()

    result = _process_with(client)

    assert result.difficulty_level == SudokuDifficulty.HARD
    assert result.time_to_solve == 757

    kwargs = client.messages.parse.call_args.kwargs
    assert kwargs["output_format"] is ClaudeSudokuExtraction
    messages = kwargs["messages"]
    assert len(messages) == 1, "no assistant prefill should be sent"
    image_block = messages[0]["content"][1]
    assert image_block["source"]["data"] == base64.b64encode(b"image-bytes").decode()


@pytest.mark.parametrize("stop_reason", ["max_tokens", "refusal"])
def test_process_screenshot_rejects_unexpected_stop_reason(stop_reason: str) -> None:
    client = _mock_client(stop_reason=stop_reason)

    with pytest.raises(ValueError, match=stop_reason):
        _process_with(client)


def test_process_screenshot_rejects_missing_structured_output() -> None:
    client = _mock_client(parsed_output=None)

    with pytest.raises(ValueError, match="structured output"):
        _process_with(client)
