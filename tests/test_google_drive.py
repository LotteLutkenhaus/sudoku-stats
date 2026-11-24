import io

import pytest
from PIL import Image

from google_drive import _prepare_image_for_claude


def _png_bytes(mode: str) -> bytes:
    buffer = io.BytesIO()
    Image.new(mode, (10, 10)).save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.mark.parametrize("mode", ["RGB", "RGBA", "P", "LA", "L"])
def test_prepare_image_for_claude_converts_png_to_jpeg(mode: str) -> None:
    result = _prepare_image_for_claude(_png_bytes(mode))

    image = Image.open(io.BytesIO(result))
    assert image.format == "JPEG"
    assert image.mode == "RGB"
    assert image.size == (10, 10)


def test_prepare_image_for_claude_rejects_non_image_bytes() -> None:
    with pytest.raises(ValueError, match="Failed to open file as image"):
        _prepare_image_for_claude(b"not an image")
