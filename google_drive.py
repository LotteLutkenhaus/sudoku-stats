import io
import logging

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from PIL import Image

from google_utils import build_drive_service
from models import ScreenshotMetadata

logger = logging.getLogger(__name__)


def get_screenshot(file_id: str) -> bytes:
    """
    Download the file with the specified ID from Google Drive, and convert it to an image that can
    be handled by the Claude API.
    """
    file_bytes = _get_file_from_drive(file_id)
    return _prepare_image_for_claude(file_bytes)


def _get_file_from_drive(file_id: str) -> bytes:
    """
    Download a file from Google Drive and return its raw bytes.
    """
    service = build_drive_service()

    # Create a request to download the file's binary content, and a file buffer to store the
    # file in.
    request = service.files().get_media(fileId=file_id)
    buffer = io.BytesIO()

    # Use MediaIoBaseDownload to handle chunked downloads.
    downloader = MediaIoBaseDownload(buffer, request)

    # Download the file in chunks
    done = False
    while done is False:
        try:
            status, done = downloader.next_chunk()
            logger.info(f"Download {int(status.progress() * 100)}.")
        except HttpError as e:
            raise ValueError("An error occurred downloading file") from e

    # Return the complete file content from the buffer
    return buffer.getvalue()


def _prepare_image_for_claude(file_bytes: bytes) -> bytes:
    """
    Convert file bytes to an appropriate image format for Claude API.
    """
    # Open the raw bytes as an image using PIL
    try:
        image = Image.open(io.BytesIO(file_bytes))
    except Exception as e:
        raise ValueError("Failed to open file as image") from e

    # Convert to JPEG format for the Claude API
    buffer = io.BytesIO()
    try:
        image.save(buffer, format="JPEG", quality=85)
    except Exception as e:
        raise ValueError("Failed to convert image to JPEG") from e

    return buffer.getvalue()


def get_file_metadata(file_id: str) -> ScreenshotMetadata:
    """
    Get some metadata for the file with the specified ID, most specifically the time it was created.
    """
    service = build_drive_service()

    file_metadata = service.files().get(fileId=file_id, fields="*").execute()
    parsed_metadata: ScreenshotMetadata = ScreenshotMetadata.model_validate(file_metadata)
    return parsed_metadata
