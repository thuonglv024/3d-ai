from io import BytesIO
import pytest
from PIL import Image
from app.images import InvalidPhoto, decode_photo


def test_invalid_bytes_rejected():
    with pytest.raises(InvalidPhoto):
        decode_photo(b"this is not an image")


def test_large_image_is_resized_and_orientation_normalized():
    out = BytesIO()
    image = Image.new("RGB", (2400, 3200), "white")
    exif = Image.Exif()
    exif[274] = 6
    image.save(out, format="JPEG", exif=exif)
    decoded = decode_photo(out.getvalue())
    assert decoded.shape[1] > decoded.shape[0]
    assert decoded.shape[1] <= 1400


def test_tiny_image_rejected():
    out = BytesIO()
    Image.new("RGB", (20, 20)).save(out, format="PNG")
    with pytest.raises(InvalidPhoto):
        decode_photo(out.getvalue())
