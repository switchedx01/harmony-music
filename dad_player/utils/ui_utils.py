# dad_player/utils/ui_utils.py

import logging
from kivy.core.window import Window
from kivy.metrics import dp

log = logging.getLogger(__name__)

def spx(value_in_pixels: int | float) -> int | float:
    """
    Scaled Pixels: A density-independent scaling utility for Kivy.
    Falls back to the original value if Kivy's density is not available.
    """
    if Window and hasattr(Window, "density") and Window.density > 0:
        return dp(value_in_pixels)
    
    log.warning(f"spx({value_in_pixels}): Kivy density not available. Returning original value.")
    return value_in_pixels