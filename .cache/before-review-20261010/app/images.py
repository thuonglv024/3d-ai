from io import BytesIO
import warnings

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from .config import MAX_PIXELS, MAX_UPLOAD


class InvalidPhoto(ValueError):
    """A recoverable user input error."""


def decode_photo(data: bytes) -> np.ndarray:
    if not data or len(data) > MAX_UPLOAD:
        raise InvalidPhoto("Mỗi ảnh cần nhỏ hơn 10 MB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as original:
                if original.format not in {"JPEG", "PNG", "WEBP"}:
                    raise InvalidPhoto("Chỉ nhận ảnh JPG, PNG hoặc WebP.")
                if original.width * original.height > MAX_PIXELS:
                    raise InvalidPhoto("Ảnh quá lớn. Hãy giảm xuống dưới 20 megapixel.")
                image = ImageOps.exif_transpose(original).convert("RGB")
                if min(image.size) < 200:
                    raise InvalidPhoto("Ảnh quá nhỏ. Hãy dùng ảnh có cạnh ngắn ít nhất 200 pixel.")
                image.thumbnail((1400, 1800))
                return np.ascontiguousarray(image)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise InvalidPhoto("Không đọc được ảnh. Hãy xuất lại ảnh thành JPG hoặc PNG.") from exc
