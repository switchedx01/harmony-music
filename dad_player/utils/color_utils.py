# dad_player/utils/color_utils.py

import colorgram
import logging
from math import sqrt
from typing import Dict, Tuple, Optional, List


log = logging.getLogger(__name__)


MATERIAL_COLORS = {
    "Red": {"100": "#FFCDD2", "300": "#E57373", "500": "#F44336", "700": "#D32F2F", "900": "#B71C1C"},
    "Pink": {"100": "#F8BBD0", "300": "#F06292", "500": "#E91E63", "700": "#C2185B", "900": "#880E4F"},
    "Purple": {"100": "#E1BEE7", "300": "#BA68C8", "500": "#9C27B0", "700": "#7B1FA2", "900": "#4A148C"},
    "DeepPurple": {"100": "#D1C4E9", "300": "#9575CD", "500": "#673AB7", "700": "#512DA8", "900": "#311B92"},
    "Indigo": {"100": "#C5CAE9", "300": "#7986CB", "500": "#3F51B5", "700": "#303F9F", "900": "#1A237E"},
    "Blue": {"100": "#BBDEFB", "300": "#64B5F6", "500": "#2196F3", "700": "#1976D2", "900": "#0D47A1"},
    "LightBlue": {"100": "#B3E5FC", "300": "#4FC3F7", "500": "#03A9F4", "700": "#0288D1", "900": "#01579B"},
    "Cyan": {"100": "#B2EBF2", "300": "#4DD0E1", "500": "#00BCD4", "700": "#0097A7", "900": "#006064"},
    "Teal": {"100": "#B2DFDB", "300": "#4DB6AC", "500": "#009688", "700": "#00796B", "900": "#004D40"},
    "Green": {"100": "#C8E6C9", "300": "#81C784", "500": "#4CAF50", "700": "#388E3C", "900": "#1B5E20"},
    "LightGreen": {"100": "#DCEDC8", "300": "#AED581", "500": "#8BC34A", "700": "#689F38", "900": "#33691E"},
    "Lime": {"100": "#F0F4C3", "300": "#DCE775", "500": "#CDDC39", "700": "#AFB42B", "900": "#827717"},
    "Yellow": {"100": "#FFF9C4", "300": "#FFF176", "500": "#FFEB3B", "700": "#FBC02D", "900": "#F57F17"},
    "Amber": {"100": "#FFECB3", "300": "#FFD54F", "500": "#FFC107", "700": "#FFA000", "900": "#FF6F00"},
    "Orange": {"100": "#FFE0B2", "300": "#FFB74D", "500": "#FF9800", "700": "#F57C00", "900": "#E65100"},
    "DeepOrange": {"100": "#FFCCBC", "300": "#FF8A65", "500": "#FF5722", "700": "#E64A19", "900": "#BF360C"},
    "Brown": {"100": "#D7CCC8", "300": "#A1887F", "500": "#795548", "700": "#5D4037", "900": "#3E2723"},
    "Gray": {"100": "#F5F5F5", "300": "#E0E0E0", "500": "#9E9E9E", "700": "#616161", "900": "#212121"},
    "BlueGray": {"100": "#CFD8DC", "300": "#90A4AE", "500": "#607D8B", "700": "#455A64", "900": "#263238"}
}

DEFAULT_PRIMARY_COLOR = "BlueGray"
DEFAULT_ACCENT_COLOR = "Blue"

class AlbumArtError(Exception):
    """Custom exception for errors related to album art processing."""
    pass

def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def _color_distance(rgb1: Tuple[int, int, int], rgb2: Tuple[int, int, int]) -> float:
    r1, g1, b1 = rgb1
    r2, g2, b2 = rgb2
    return sqrt((r1 - r2)**2 + (g1 - g2)**2 + (b1 - b2)**2)

def get_vibrant_color_from_image(image_path: str) -> Optional[Tuple[int, int, int]]:
    """
    Extracts a palette of colors and returns the most vibrant (saturated) one.
    
    Raises:
        AlbumArtError: If the image file cannot be opened or processed.
    """
    try:
        colors: List[colorgram.Color] = colorgram.extract(image_path, 6)
        if not colors:
            log.warning(f"colorgram could not extract any colors from {image_path}.")
            return None
        

        vibrant_color = max(colors, key=lambda c: c.hsl.s)
        return tuple(vibrant_color.rgb)

    except Exception as e:
        raise AlbumArtError(f"Failed to process album art at {image_path}: {e}") from e

def find_closest_material_color(rgb_color: Optional[Tuple[int, int, int]]) -> str:
    """
    Finds the name of the closest Material Design color from our expanded palette.
    """
    if not rgb_color:
        return DEFAULT_PRIMARY_COLOR

    min_distance = float('inf')
    closest_color_name = DEFAULT_PRIMARY_COLOR

    for color_name, shades in MATERIAL_COLORS.items():
        for hex_val in shades.values():
            material_rgb = _hex_to_rgb(hex_val)
            distance = _color_distance(rgb_color, material_rgb)
            if distance < min_distance:
                min_distance = distance
                closest_color_name = color_name
                
    return closest_color_name

def get_theme_colors_from_art(image_path: str) -> Dict[str, str]:
    if not image_path:
        return {'primary_color': DEFAULT_PRIMARY_COLOR, 'accent_color': DEFAULT_ACCENT_COLOR}

    try:
        vibrant_color = get_vibrant_color_from_image(image_path)
        primary_color = find_closest_material_color(vibrant_color)
        accent_color = DEFAULT_ACCENT_COLOR 
        
        log.info(f"Theme generated from '{image_path}': Primary={primary_color}")
        return {
            'primary_color': primary_color,
            'accent_color': accent_color
        }
    except AlbumArtError as e:
        log.error(f"Could not generate theme from art: {e}")
        return {
            'primary_color': DEFAULT_PRIMARY_COLOR,
            'accent_color': DEFAULT_ACCENT_COLOR
        }

def apply_theme_colors(app, primary_color: str, accent_color: str) -> None:
    """
    Applies the given colors to the KivyMD app's theme.
    """
    app.theme_cls.primary_palette = primary_color
    app.theme_cls.accent_palette = accent_color
