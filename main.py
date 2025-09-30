import functions_framework
from flask import Request
from neon_db import insert_sudoku_result

from claude import process_screenshot
from google_drive import get_file_metadata, get_screenshot
from google_utils import get_secret
from models import WebhookPayload


@functions_framework.http
def process_sudoku_screenshot(request: Request) -> tuple[dict[str, str], int]:
    data = request.get_json()
    api_key = request.headers.get("X-API-Key")

    if api_key != get_secret("make-api-key"):
        return ({"error": "Unauthorized"}), 401

    payload = WebhookPayload.model_validate(data)

    file = get_screenshot(file_id=payload.file_id)
    parsed_sudoku_result = process_screenshot(file)
    file_metadata = get_file_metadata(file_id=payload.file_id)
    insert_sudoku_result(parsed_result=parsed_sudoku_result, screenshot_metadata=file_metadata)

    return ({"message": "Success"}), 200
