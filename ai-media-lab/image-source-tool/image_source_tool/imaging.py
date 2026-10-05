"""Bounded decoding and fresh pixel-only normalization; never persists upload data."""
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import warnings
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_PIXELS = 40_000_000
MAX_UPLOAD_BYTES = 12 * 1024 * 1024
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
Image.MAX_IMAGE_PIXELS = MAX_PIXELS

class InputError(ValueError):
    pass

@dataclass(frozen=True)
class PreparedImage:
    info: dict
    upload: bytes


def prepare_image(path: Path, max_side: int = 1600) -> PreparedImage:
    if not 128 <= max_side <= 1600:
        raise InputError("max_side must be between 128 and 1600 pixels")
    if not path.is_file():
        raise InputError("Input must be a readable local image file")
    if path.stat().st_size > MAX_FILE_BYTES:
        raise InputError("Input exceeds 20 MiB limit")
    with path.open("rb") as handle:
        raw = handle.read(MAX_FILE_BYTES + 1)
    if len(raw) > MAX_FILE_BYTES:
        raise InputError("Input exceeds 20 MiB limit")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(raw)) as image:
                if image.format not in ALLOWED_FORMATS:
                    raise InputError("Supported formats: still JPEG, PNG and WebP")
                if getattr(image, "n_frames", 1) != 1:
                    raise InputError("Animated images are unsupported; choose a frame locally")
                if image.width * image.height > MAX_PIXELS:
                    raise InputError("Image exceeds 40 megapixel limit")
                fmt, width, height = image.format, image.width, image.height
                has_metadata = bool(image.info or image.getexif())
                image.load()
                oriented = ImageOps.exif_transpose(image)
                # Flatten transparency on white, then create a NEW image from pixels.
                # Merely convert()/copy() may retain info metadata.
                rgba = oriented.convert("RGBA")
                flattened = Image.new("RGBA", rgba.size, "white")
                flattened.alpha_composite(rgba)
                flattened.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
                pixels = Image.frombytes("RGB", flattened.size, flattened.convert("RGB").tobytes())
                buffer = BytesIO()
                pixels.save(buffer, format="PNG")
                upload = buffer.getvalue()
                if len(upload) > MAX_UPLOAD_BYTES:
                    raise InputError("Normalized upload exceeds 12 MiB limit; reduce max_side")
                return PreparedImage({
                    "sha256": sha256(raw).hexdigest(), "bytes": len(raw),
                    "format": fmt, "width": width, "height": height,
                    "metadata_present": has_metadata,
                    "normalized": {"format": "PNG", "width": pixels.width,
                                   "height": pixels.height, "bytes": len(upload),
                                   "sha256": sha256(upload).hexdigest(),
                                   "metadata_stripped": True},
                }, upload)
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError,
            Image.DecompressionBombWarning) as exc:
        raise InputError("Image could not be safely decoded") from exc
