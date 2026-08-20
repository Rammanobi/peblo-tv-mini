import io

from PIL import Image

from app import reference
from app.errors import ApiError

MIME_TO_FORMAT = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}
EXT_BY_MIME = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


def validate_and_probe(kind: str, mime_type: str, data: bytes) -> tuple[int, int]:
    """Validates mime, size, and aspect ratio. Returns (width, height) or raises ApiError."""
    allowed = reference.artwork_allowed_mimes()
    if mime_type not in allowed:
        raise ApiError(
            422,
            "validation_error",
            "That file type is not supported.",
            [
                {
                    "code": "ARTWORK_MIME_TYPE",
                    "field": "file",
                    "message": f'"{mime_type}" is not an accepted image type. Use JPEG, PNG or WebP.',
                    "hint": "Re-export the image as JPEG, PNG, or WebP.",
                    "resource": None,
                }
            ],
        )

    max_bytes = reference.artwork_max_bytes()
    if len(data) > max_bytes:
        raise ApiError(
            413,
            "payload_too_large",
            f"That {kind} is too big.",
            [
                {
                    "code": "ARTWORK_SIZE_LIMIT",
                    "field": "file",
                    "message": f"The file is {len(data) // 1024} KB. Artwork must be "
                    f"{max_bytes // 1024} KB or smaller.",
                    "hint": "Re-export the image as JPEG at ~80% quality, or use WebP.",
                    "resource": None,
                }
            ],
        )

    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
        img = Image.open(io.BytesIO(data))
        width, height = img.size
        actual_format = img.format
    except Exception:
        raise ApiError(
            422,
            "validation_error",
            "That file could not be read as an image.",
            [
                {
                    "code": "ARTWORK_MIME_TYPE",
                    "field": "file",
                    "message": "The uploaded file is not a valid image.",
                    "hint": "Upload a valid JPEG, PNG, or WebP file.",
                    "resource": None,
                }
            ],
        )

    expected_format = MIME_TO_FORMAT.get(mime_type)
    if actual_format != expected_format:
        raise ApiError(
            422,
            "validation_error",
            "That file's contents do not match its declared type.",
            [
                {
                    "code": "ARTWORK_MIME_TYPE",
                    "field": "file",
                    "message": f"The file was declared as {mime_type} but its contents look like {actual_format}.",
                    "hint": "Re-export and re-upload with matching content type.",
                    "resource": None,
                }
            ],
        )

    spec = reference.artwork_spec(kind)
    if not spec:
        raise ApiError(
            422,
            "validation_error",
            f'"{kind}" is not a supported artwork kind.',
            [
                {
                    "code": "ENUM_NOT_ALLOWED",
                    "field": "kind",
                    "message": "Supported kinds are: poster, banner, thumbnail.",
                    "hint": None,
                    "resource": None,
                }
            ],
        )

    ratio = width / height if height else 0
    expected_ratio = spec["aspect_ratio_value"]
    tolerance = reference.artwork_tolerance()
    if abs(ratio - expected_ratio) / expected_ratio > tolerance:
        raise ApiError(
            422,
            "validation_error",
            f"That {kind} is the wrong shape.",
            [
                {
                    "code": "ARTWORK_ASPECT_RATIO",
                    "field": "file",
                    "message": f"{kind.capitalize()}s must be {spec['aspect_ratio']} (about "
                    f"{spec['width']}x{spec['height']}). The uploaded image is {width}x{height}.",
                    "hint": f"Crop or re-export at {spec['width']}x{spec['height']} and upload again.",
                    "resource": None,
                }
            ],
        )

    return width, height
