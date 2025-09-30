import base64
import json

from anthropic import Anthropic
from anthropic.types import (
    Base64ImageSourceParam,
    ImageBlockParam,
    MessageParam,
    TextBlock,
    TextBlockParam,
)

from google_utils import get_secret
from models import ParsedSudokuResult


def _get_claude_prompt() -> str:
    return """This is a screenshot of the New York Times games app, of a finished Sudoku.
    Extract the difficulty level and completion time from the image.

    Return ONLY a JSON object with this structure, and nothing else:
    {
        "difficulty_level": "the difficulty level shown in the image",
        "time_to_solve": "the completion time shown in the image"
    }"""


def _parse_claude_response(raw_response: str) -> ParsedSudokuResult:
    """
    Parse Claude's response to our message

    Because we use prefilling the response via the 'assistent' role in the prompt, we should get
    back something like this:
    `'\n    "difficulty_level": "Hard",\n    "time_to_solve": "12:37"\n}'`
    """
    full_json = "{" + raw_response
    parsed_json = json.loads(full_json.strip())
    parsed_response: ParsedSudokuResult = ParsedSudokuResult.model_validate_json(parsed_json)
    return parsed_response


def process_screenshot(file_bytes: bytes) -> ParsedSudokuResult:
    """
    Build the Claude API service and the message to the API, and send it.
    """
    client = Anthropic(api_key=get_secret("claude-api-key"))
    file_content = base64.b64encode(file_bytes).decode("utf-8")

    messages = [
        MessageParam(
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
        MessageParam(role="assistant", content="{"),
    ]

    message = client.messages.create(
        model="claude-3-5-haiku-latest",  # cheapest available model, but up to the task
        max_tokens=100,
        messages=messages,
    )

    assert len(message.content) == 1, "Claude sent us multiple responses which we didn't expect"
    content = message.content[0]
    assert isinstance(content, TextBlock), "Claude returned something else than expected"
    return _parse_claude_response(content.text)
