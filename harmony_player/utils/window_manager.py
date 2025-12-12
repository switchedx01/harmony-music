import logging
import sys
from kivy.core.window import Window

log = logging.getLogger(__name__)

IS_WIN = sys.platform == 'win32'

class WindowManager:
    """
    Manages window resizing using delta-accumulation (avoids feedback loops) 
    and native window dragging.
    """
    
    def __init__(self, screen, **kwargs):
        self.screen = screen
        self.resize_border = kwargs.get('resize_border', 10)
        self._title_bar_widget = None
        
        # Resize State
        self._resize_direction = None
        
        # Delta Accumulators (for sub-pixel precision smoothing)
        self._accum_x = 0.0
        self._accum_y = 0.0

    def register_title_bar(self, widget):
        """
        Registers a widget to act as the title bar for native dragging.
        """
        self._title_bar_widget = widget
        
        # 1. Native Dragging (Kivy/SDL2 Built-in)
        # This is proven to work for moving the window.
        if hasattr(Window, 'set_custom_titlebar'):
            try:
                Window.set_custom_titlebar(widget)
                log.info("Registered custom titlebar with Kivy Window.")
            except Exception as e:
                log.error(f"Failed to set custom titlebar: {e}")
        else:
            log.warning("Window.set_custom_titlebar not available.")

    def on_touch_down(self, touch):
        # 1. Handle Double Tap Maximize (manual)
        if self._title_bar_widget and self._title_bar_widget.collide_point(*touch.pos):
            if touch.is_double_tap:
                self.screen.toggle_maximize_window()
                return True
        
        # 2. Handle Resize Grab
        self._resize_direction = self._get_resize_direction(touch.pos)
        if self._resize_direction:
            touch.grab(self.screen)
            # Reset accumulators
            self._accum_x = 0.0
            self._accum_y = 0.0
            return True

        return False
    
    def on_touch_move(self, touch):
        if self._resize_direction and touch.grab_current is self.screen:
            # We use local deltas (touch.dx, touch.dy) because they (usually) 
            # compensate for the window moving, acting as "screen deltas".
            # This prevents the feedback loop where resizing left shifts 
            # origin and causes coordinate jumps.
            
            self._apply_kivy_resize(touch.dx, touch.dy)
            return True
        return False

    def on_touch_up(self, touch):
        if self._resize_direction and touch.grab_current is self.screen:
            self._resize_direction = None
            touch.ungrab(self.screen)
            return True
        return False

    def _get_resize_direction(self, pos):
        x, y = pos
        width, height = Window.size
        border = self.resize_border

        on_left = x < border
        on_right = x > width - border
        on_bottom = y < border
        on_top = y > height - border

        if on_left and on_top: return 'top-left'
        if on_right and on_top: return 'top-right'
        if on_left and on_bottom: return 'bottom-left'
        if on_right and on_bottom: return 'bottom-right'
        if on_left: return 'left'
        if on_right: return 'right'
        if on_bottom: return 'bottom'
        if on_top: return 'top'
        return None

    def _apply_kivy_resize(self, dx, dy):
        """
        Applies resize based on deltas with 2x speed multiplier.
        """
        # Apply 2x speed multiplier for faster resizing
        dx = dx * 2.0
        dy = dy * 2.0
        
        self._accum_x += dx
        self._accum_y += dy
        
        # Only apply if we have at least 1 pixel of movement
        step_x = int(self._accum_x)
        step_y = int(self._accum_y)
        
        if step_x == 0 and step_y == 0:
            return

        # Consumption
        self._accum_x -= step_x
        self._accum_y -= step_y
        
        min_width, min_height = 400, 300
        cur_w, cur_h = Window.size
        cur_l, cur_t = Window.left, Window.top
        
        new_w, new_h = cur_w, cur_h
        new_l, new_t = cur_l, cur_t
        
        direction = self._resize_direction

        # Horizontal
        if 'left' in direction:
            target_w = cur_w - step_x
            if target_w >= min_width:
                new_w = target_w
                new_l = cur_l + step_x
            else:
                self._accum_x = 0
        elif 'right' in direction:
            target_w = cur_w + step_x
            if target_w >= min_width:
                new_w = target_w
            else:
                self._accum_x = 0

        # Vertical
        if 'bottom' in direction:
            target_h = cur_h - step_y
            if target_h >= min_height:
                new_h = target_h
            else:
                self._accum_y = 0

        elif 'top' in direction:
            target_h = cur_h + step_y
            if target_h >= min_height:
                new_h = target_h
                new_t = cur_t - step_y
            else:
                self._accum_y = 0

        # Apply
        if (new_w != cur_w or new_h != cur_h):
            Window.size = (new_w, new_h)
            
        # Update Position logic
        if (new_l != cur_l or new_t != cur_t):
            if IS_WIN or not hasattr(Window, 'custom_titlebar'):
                Window.left = new_l
                Window.top = new_t
