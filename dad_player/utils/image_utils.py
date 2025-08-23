# dad_player/utils/image_utils.py

import logging
import os
from io import BytesIO
from pathlib import Path
import hashlib

try:
    from PIL import Image, ImageFilter
except ImportError:
    Image = None
    ImageFilter = None

from dad_player.constants import PLACEHOLDER_ALBUM_FILENAME

log = logging.getLogger(__name__)

CACHE_BASE_DIR = Path(__file__).resolve().parents[2] / "cache"
ALBUM_ART_CACHE_DIR = CACHE_BASE_DIR / "album_art"

os.makedirs(ALBUM_ART_CACHE_DIR, exist_ok=True)

def get_placeholder_album_art_path() -> str | None:
    """Constructs the path to the placeholder album art image."""
    try:
        base_path = Path(__file__).resolve().parents[2]
        placeholder_path = base_path / "assets" / "icons" / PLACEHOLDER_ALBUM_FILENAME
        if placeholder_path.exists():
            return str(placeholder_path)
        log.warning(f"Placeholder image not found at expected path: {placeholder_path}")
    except Exception as e:
        log.error(f"Error constructing placeholder path: {e}")
    return None

def _generate_cache_filename(unique_id: str, suffix: str) -> str:
    """Creates a unique, safe filename for caching based on a unique ID."""
    hasher = hashlib.md5()
    hasher.update(unique_id.encode('utf-8'))
    return f"{hasher.hexdigest()}_{suffix}.png"

def process_and_cache_album_art(
    raw_data: bytes,
    unique_id: str,
    size: tuple = (800, 800),
    blur_radius: int = 0,
    force_overwrite: bool = False
) -> tuple[str | None, str | None]:
    """
    Processes raw image data (resizes, blurs) and saves it to a cache.
    Returns paths to the cached normal and blurred images.
    """
    if not Image or not raw_data:
        return None, None

    normal_filename = _generate_cache_filename(unique_id, f"{size[0]}x{size[1]}")
    normal_cache_path = ALBUM_ART_CACHE_DIR / normal_filename

    if force_overwrite or not normal_cache_path.exists():
        try:
            with Image.open(BytesIO(raw_data)) as img:
                img.thumbnail(size, Image.Resampling.LANCZOS)
                img.save(normal_cache_path, format="PNG", quality=95)
        except Exception as e:
            log.error(f"Failed to process and cache normal image for '{unique_id}': {e}")
            return None, None
    
    blurred_cache_path = None
    if blur_radius > 0:
        blurred_filename = _generate_cache_filename(unique_id, f"blurred_{blur_radius}")
        blurred_cache_path = ALBUM_ART_CACHE_DIR / blurred_filename

        if force_overwrite or not blurred_cache_path.exists():
            try:
                with Image.open(BytesIO(raw_data)) as img:
                    img.thumbnail((400, 400), Image.Resampling.LANCZOS)
                    blurred_img = img.filter(ImageFilter.GaussianBlur(blur_radius))
                    blurred_img.save(blurred_cache_path, format="PNG", quality=80)
            except Exception as e:
                log.error(f"Failed to process and cache blurred image for '{unique_id}': {e}")
                blurred_cache_path = None

    return str(normal_cache_path) if normal_cache_path.exists() else None, \
           str(blurred_cache_path) if blurred_cache_path and blurred_cache_path.exists() else None
