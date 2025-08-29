# dad_player/utils/color_utils.py

import logging
from typing import Dict, Optional, List
import colorgram
from kivy.utils import get_color_from_hex
from colorsys import rgb_to_hls, hls_to_rgb

log = logging.getLogger(__name__)

# --- Constants ---
DEFAULT_PRIMARY_PALETTE = "BlueGray"
DEFAULT_ACCENT_PALETTE = "Blue"
CUSTOM_PRIMARY_NAME = "Red"
CUSTOM_ACCENT_NAME = "Pink"


# --- Custom Exception ---
class AlbumArtError(Exception):
    pass

# --- Core Functions ---

def _generate_shades(hex_color: str) -> Dict[str, str]:
    """
    Generates a 10-step Material Design palette from a single hex color
    by adjusting the lightness in the HLS color space.
    """
    r, g, b, _ = get_color_from_hex(hex_color)
    h, l, s = rgb_to_hls(r, g, b)

    shades = {}
    lightness_map = {
        "50": min(1.0, l + 0.5), "100": min(1.0, l + 0.35),
        "200": min(1.0, l + 0.2), "300": min(1.0, l + 0.1),
        "400": min(1.0, l + 0.05), "500": l,
        "600": max(0.0, l - 0.05), "700": max(0.0, l - 0.1),
        "800": max(0.0, l - 0.2), "900": max(0.0, l - 0.35)
    }

    for name, light_val in lightness_map.items():
        r_new, g_new, b_new = hls_to_rgb(h, light_val, s)
        shades[name] = f"#{int(r_new*255):02x}{int(g_new*255):02x}{int(b_new*255):02x}"
    
    return shades

def _get_primary_and_accent(image_path: str) -> Optional[Dict[str, str]]:
    try:
        colors: List[colorgram.Color] = colorgram.extract(image_path, 8)
        if not colors:
            raise AlbumArtError("colorgram could not extract any colors.")
        
        colors.sort(key=lambda c: c.hsl.s, reverse=True)
        
        primary_color = colors[0]
        accent_color = colors[1] if len(colors) > 1 else colors[0]

        return {
            'primary': f"#{primary_color.rgb.r:02x}{primary_color.rgb.g:02x}{primary_color.rgb.b:02x}",
            'accent': f"#{accent_color.rgb.r:02x}{accent_color.rgb.g:02x}{accent_color.rgb.b:02x}"
        }

    except Exception as e:
        raise AlbumArtError(f"Failed to process album art: {e}") from e

# --- Public API ---

def get_theme_colors_from_art(image_path: Optional[str]) -> Dict:
    if not image_path:
        return {'custom': False, 'primary_palette': DEFAULT_PRIMARY_PALETTE, 'accent_palette': DEFAULT_ACCENT_PALETTE}

    try:
        custom_palette = _get_primary_and_accent(image_path)
        if custom_palette is None:
             raise AlbumArtError("Palette generation returned None.")

        log.info(f"Generated custom theme from '{image_path}'")
        return {'custom': True, 'palette': custom_palette}

    except AlbumArtError as e:
        log.error(f"Could not generate theme from art: {e}. Falling back to default.")
        return {'custom': False, 'primary_palette': DEFAULT_PRIMARY_PALETTE, 'accent_palette': DEFAULT_ACCENT_PALETTE}

def apply_theme_colors(app, theme_dict: Dict) -> None:
    if theme_dict.get('custom'):
        palette = theme_dict['palette']
        primary_hex = palette['primary']
        accent_hex = palette['accent']

        primary_shades = _generate_shades(primary_hex)
        accent_shades = _generate_shades(accent_hex)

        app.theme_cls.colors[CUSTOM_PRIMARY_NAME] = primary_shades
        app.theme_cls.colors[CUSTOM_ACCENT_NAME] = accent_shades

        app.theme_cls.primary_palette = CUSTOM_PRIMARY_NAME
        app.theme_cls.accent_palette = CUSTOM_ACCENT_NAME
        log.debug("Applied custom generated theme by overwriting palettes.")
    else:
        app.theme_cls.primary_palette = theme_dict.get('primary_palette', DEFAULT_PRIMARY_PALETTE)
        app.theme_cls.accent_palette = theme_dict.get('accent_palette', DEFAULT_ACCENT_PALETTE)
        log.debug("Applied default theme.")
