import base64

from anthropic import Anthropic
from anthropic.types import (
    Base64ImageSourceParam,
    ImageBlockParam,
    MessageParam,
    TextBlockParam,
    UserMessageParam,
)

from google_utils import get_secret
from models import ClaudeSudokuExtraction, ParsedSudokuResult


def _get_claude_prompt() -> str:
    return """This is a screenshot of the New York Times games app, of a finished Sudoku.
    Extract the difficulty level and completion time from the image."""


def process_screenshot(file_bytes: bytes) -> ParsedSudokuResult:
    """
    Build the Claude API service and the message to the API, and send it.
    """
    client = Anthropic(api_key=get_secret("claude-api-key"))
    file_content = base64.b64encode(file_bytes).decode("utf-8")

    messages: list[MessageParam] = [
        UserMessageParam(
            role="user",
            content=[
                TextBlockParam(type="text", text=_get_claude_prompt()),
                ImageBlockParam(
                    type="image",
                    source=Base64ImageSourceParam(
                        type="base64",
                        media_type="image/jpeg",
                        data=file_content,
                    ),
                ),
            ],
        ),
    ]

    message = client.messages.parse(
        model="claude-haiku-5-5",  # cheapest available model
        max_tokens=1024,
        output_config={"effort": "low"}, # enough for parsing a screenshot
        messages=messages,
        output_format=ClaudeSudokuExtraction,
    )

    if message.stop_reason != "end_turn":
        raise ValueError(f"Claude stopped unexpectedly (stop_reason={message.stop_reason!r})")

    extraction = message.parsed_output
    if extraction is None:
        raise ValueError("Claude did not return a structured output")

    return ParsedSudokuResult.model_validate(extraction.model_dump())
