# dad_player/utils/image_utils.py

import logging
import os
from io import BytesIO
from pathlib import Path

try:
    from PIL import Image, ImageFilter
except ImportError:
    Image = None
    ImageFilter = None

try:
    import colorgram
except ImportError:
    colorgram = None

from dad_player.constants import PLACEHOLDER_ALBUM_FILENAME

log = logging.getLogger(__name__)

# =========================================================================
# Image Manipulation Functions
# =========================================================================

def resize_image_data(raw_data: bytes, target_max_dim: int, output_format="PNG", quality=90) -> BytesIO | None:
    """
    Resizes image data to a target maximum dimension, maintaining aspect ratio.
    """
    if not Image or not raw_data:
        return None
    try:
        with Image.open(BytesIO(raw_data)) as img:
            img.thumbnail((target_max_dim, target_max_dim), Image.Resampling.LANCZOS)
            stream = BytesIO()
            img.save(stream, format=output_format, quality=quality)
            stream.seek(0)
            return stream
    except Exception as e:
        log.error(f"Failed to resize image data: {e}")
        return None

def blur_image_data(raw_data: bytes, radius: int = 15) -> BytesIO | None:
    """
    Applies a Gaussian blur to image data.
    """
    if not Image or not raw_data:
        return None
    try:
        with Image.open(BytesIO(raw_data)) as img:
            blurred_img = img.filter(ImageFilter.GaussianBlur(radius))
            stream = BytesIO()
            blurred_img.save(stream, format="PNG")
            stream.seek(0)
            return stream
    except Exception as e:
        log.error(f"Failed to blur image data: {e}")
        return None

# =========================================================================
# Path and Color Extraction Utilities
# =========================================================================

def get_placeholder_album_art_path() -> str | None:
    """
    Constructs the path to the placeholder album art image.
    Assumes an 'assets/icons' directory relative to this file's location.
    """
    try:
        base_path = Path(__file__).resolve().parents[2]
        placeholder_path = base_path / "assets" / "icons" / PLACEHOLDER_ALBUM_FILENAME
        if placeholder_path.exists():
            return str(placeholder_path)
        log.warning(f"Placeholder image not found at expected path: {placeholder_path}")
    except Exception as e:
        log.error(f"Error constructing placeholder path: {e}")
    return None

MATERIAL_PALETTES = {
    "Red": (244, 67, 54), "Pink": (233, 30, 99), "Purple": (156, 39, 176),
    "DeepPurple": (103, 58, 183), "Indigo": (63, 81, 176), "Blue": (33, 150, 243),
    "LightBlue": (3, 169, 244), "Cyan": (0, 188, 212), "Teal": (0, 150, 136),
    "Green": (76, 175, 80), "LightGreen": (139, 195, 74), "Lime": (205, 220, 57),
    "Yellow": (255, 235, 59), "Amber": (255, 193, 7), "Orange": (255, 152, 0),
    "DeepOrange": (255, 87, 34), "Brown": (121, 85, 72), "Gray": (158, 158, 158),
    "BlueGray": (96, 125, 139),
}

def find_closest_material_palette(rgb_tuple: tuple) -> str:
    """Finds the closest Material Design palette name for a given RGB tuple."""
    min_distance = float("inf")
    closest_color_name = "BlueGray"
    for name, material_rgb in MATERIAL_PALETTES.items():
        distance = sum([(a - b) ** 2 for a, b in zip(rgb_tuple, material_rgb)])
        if distance < min_distance:
            min_distance = distance
            closest_color_name = name
    return closest_color_name
    """Extracts a dominant color from an image and finds the closest Material palette."""
    if not colorgram or not art_path or not os.path.exists(art_path):
        return None
    
    try:
        colors = colorgram.extract(art_path, 6)
        vibrant_colors = [c for c in colors if c.hsl.s > 0.3 and 0.2 < c.hsl.l < 0.8]
        if vibrant_colors:
            return find_closest_material_palette(vibrant_colors[0].rgb)
        elif colors:
            return find_closest_material_palette(colors[0].rgb)
    except Exception as e:
        log.error(f"Failed to extract colors from {art_path}: {e}")
    
    return None
