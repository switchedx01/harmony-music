# dad_player/utils/window_manager.py

import logging
import sys
from kivy.core.window import Window

log = logging.getLogger(__name__)

IS_WIN = sys.platform == 'win32'
if IS_WIN:
    import ctypes
    user32 = ctypes.windll.user32
    # Win32 API constants for window messages
    WM_NCLBUTTONDOWN = 0x00A1
    HTCAPTION = 2

class WindowManager:
    def __init__(self, screen, resize_border=8):
        self.screen = screen
        self.resize_border = resize_border
        self._hwnd = None
        if IS_WIN:
            try:
                self._hwnd = Window.get_window_info().window
            except Exception as e:
                log.error(f"Could not get window handle (HWND). Native dragging disabled. Error: {e}")
                self._hwnd = None

        self._resize_direction = None
        self._initial_touch_pos = (0, 0)
        self._initial_window_pos = (0, 0)
        self._initial_window_size = (0, 0)

    def on_touch_down(self, touch):
        if self.screen._is_maximized:
            if self.screen.ids.title_bar.collide_point(*touch.pos) and touch.is_double_tap:
                self.screen.toggle_maximize_window()
            return True

        self._resize_direction = self._get_resize_direction(touch.pos)
        if self._resize_direction:
            touch.grab(self.screen)
            self._initial_touch_pos = touch.pos
            self._initial_window_pos = (Window.left, Window.top)
            self._initial_window_size = Window.size
            return True

        title_bar = self.screen.ids.get('title_bar')
        if IS_WIN and self._hwnd and title_bar and title_bar.collide_point(*touch.pos):
            is_on_button = any(
                hasattr(child, 'icon') and child.collide_point(*touch.pos)
                for child in title_bar.children
            )
            if not is_on_button:
                if touch.is_double_tap:
                    self.screen.toggle_maximize_window()
                    return True
                touch.ungrab(self.screen)
                user32.ReleaseCapture()
                user32.SendMessageW(self._hwnd, WM_NCLBUTTONDOWN, HTCAPTION, 0)
                return True
        
        return False

    def on_touch_move(self, touch):
        """
        This method is ONLY used for resizing. Dragging is handled by the OS.
        """
        if self._resize_direction and touch.grab_current is self.screen:
            self._apply_kivy_resize(touch)
            return True
        return False

    def on_touch_up(self, touch):
        """
        Resets the state after a Kivy-handled resize operation.
        """
        if self._resize_direction and touch.grab_current is self.screen:
            self._resize_direction = None
            touch.ungrab(self.screen)
            return True
        return False

    def _get_resize_direction(self, pos):
        """Determines which border or corner is being touched."""
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

    def _apply_kivy_resize(self, touch):
        min_width, min_height = 200, 150
        
        dx = touch.x - self._initial_touch_pos[0]
        dy = touch.y - self._initial_touch_pos[1]

        new_left, new_top = self._initial_window_pos
        new_width, new_height = self._initial_window_size

        if 'left' in self._resize_direction:
            new_width = self._initial_window_size[0] - dx
            if new_width >= min_width:
                new_left = self._initial_window_pos[0] + dx
        elif 'right' in self._resize_direction:
            new_width = self._initial_window_size[0] + dx
        
        if 'bottom' in self._resize_direction:
            new_height = self._initial_window_size[1] + dy
        elif 'top' in self._resize_direction:
            new_height = self._initial_window_size[1] - dy
            if new_height >= min_height:
                new_top = self._initial_window_pos[1] - dy
        
        Window.size = (max(new_width, min_width), max(new_height, min_height))
        Window.left, Window.top = new_left, new_top

