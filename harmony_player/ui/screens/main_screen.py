# harmony_player/ui/screens/main_screen.py

# =============================================================================
# Imports and Constants
# =============================================================================
import logging
import sys
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.properties import ObjectProperty, StringProperty
from kivymd.uix.screen import MDScreen
from kivymd.app import MDApp
from harmony_player.constants import LAYOUT_BREAKPOINT
from harmony_player.utils.color_utils import get_theme_colors_from_art, apply_theme_colors
# Import the new hybrid window manager
from harmony_player.utils.window_manager import WindowManager

log = logging.getLogger(__name__)

IS_WIN = sys.platform == 'win32'
if IS_WIN:
    try:
        import win32api
        import win32con
    except ImportError:
        log.warning("pywin32 is not installed. Maximize functionality will be limited.")
        IS_WIN = False


from kivymd.uix.button import MDIconButton
from kivy.properties import BooleanProperty

class HoverTitleBarButton(MDIconButton):
    hovering = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # We need to bind to Window mouse events for hover
        # Ideally using a proper Behavior, but this works for specific instance
        Window.bind(mouse_pos=self.on_mouse_pos)

    def on_mouse_pos(self, window, pos):
        if not self.parent:
            return
        # Convert to local coordinates?
        # collide_point handles global coordinates if widget is in tree
        # But for MDIconButton inside layouts, collide_point usually expects parent or window coords?
        # Kivy collide_point expects WINDOW coordinates (if using to_widget) or PARENT?
        # Kivy collide_point expects Widget Local coordinates? 
        # Standard: collide_point(x, y) checks if x,y (in widget coords) is inside.
        # But touch/mouse_pos is Window Coords.
        # We must internalize:
        local_pos = self.to_widget(*pos)
        if self.collide_point(*local_pos):
             self.hovering = True
             Window.set_system_cursor('hand')
        elif self.hovering:
             self.hovering = False
             Window.set_system_cursor('arrow')

class MainScreen(MDScreen):
    player_engine = ObjectProperty(None)
    library_manager = ObjectProperty(None)
    settings_manager = ObjectProperty(None)
    playlist_manager = ObjectProperty(None)
    top_bar_title = StringProperty("Harmony Player")

    def __init__(self, **kwargs):
        self._views = {}
        self._current_layout = None
        self._is_initialized = False
        self.current_sub_view = "library_screen"
        
        # =============================================================================
        # Hybrid Window Setup
        # =============================================================================
        self._is_maximized = False
        self._old_window_pos = None
        self._old_window_size = None
        self.window_manager = WindowManager(self, resize_border=4)

        super().__init__(**kwargs)

    def on_touch_down(self, touch):
        if self.window_manager.on_touch_down(touch):
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self.window_manager.on_touch_move(touch):
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if self.window_manager.on_touch_up(touch):
            return True
        return super().on_touch_up(touch)

    def bind_hover_events(self):
        Window.bind(mouse_pos=self._check_hover)

    def _check_hover(self, window, pos):
        # Only used for resize cursors now, buttons handle themselves
        x, y = pos
        width, height = Window.size
        border = self.window_manager.resize_border if self.window_manager else 8

        on_left = x < border
        on_right = x > width - border
        on_bottom = y < border
        on_top = y > height - border

        if (on_left and on_top) or (on_right and on_bottom):
            Window.set_system_cursor('size_nwse')
        elif (on_right and on_top) or (on_left and on_bottom):
            Window.set_system_cursor('size_nesw')
        elif on_left or on_right:
            Window.set_system_cursor('size_we')
        elif on_top or on_bottom:
            Window.set_system_cursor('size_ns')
        else:
            # Let buttons handle 'hand' cursor, otherwise arrow
            # Might conflict if button sets hand and this sets arrow.
            # But bind order matters.
            # We skip 'arrow' reset here if we think we are over a button?
            # It's better to let the button handle it.
            pass
    
    def _get_monitor_work_area(self):
        if not IS_WIN:
            return None
        monitor = win32api.MonitorFromPoint((Window.left, Window.top), win32con.MONITOR_DEFAULTTONEAREST)
        info = win32api.GetMonitorInfo(monitor)
        return info.get("Work")

    def close_window(self):
        MDApp.get_running_app().stop()

    def minimize_window(self):
        Window.minimize()

    def toggle_maximize_window(self):
        # We rely on Kivy's window state handling where possible.
        # On Linux/XWayland, Window.maximize() toggles or sets state.
        # To ensure we don't desync, we check our internal flag, but also trust the command.
        
        if self._is_maximized:
            # RESTORE
            Window.restore()
            self._is_maximized = False
            
            # Restore previous size/pos if available
            if self._old_window_pos:
                Window.left, Window.top = self._old_window_pos
            if self._old_window_size:
                Window.size = self._old_window_size

    def toggle_maximize_window(self):
        self._ignore_resize = True
        
        if self._is_maximized:
            # RESTORE
            if IS_WIN:
                 # ... existing windows specific logic if any, but simplified for brevity/consistency
                 # Assuming the previous logic or standard Window.restore()
                 pass

            Window.restore()
            self._is_maximized = False
            # Restore previous size explicitly if needed, but Window.restore() should handle it 
            # if we didn't mess it up. 
            # To be safe, let's force the fixed size after restore if we want "fixed or max"
            Clock.schedule_once(lambda dt: self._force_fixed_size(), 0.1)

        else:
            # MAXIMIZE
            if IS_WIN:
                work_area = self._get_monitor_work_area()
                if work_area:
                    x, y, w, h = work_area
                    Window.left = x
                    Window.top = y 
                    Window.size = (w - x, h - y)
                    self._is_maximized = True
                    # Reset flag after delay
                    Clock.schedule_once(lambda dt: setattr(self, '_ignore_resize', False), 0.5)
                    return

            # Linux/Mac/Generic
            Window.maximize()
            self._is_maximized = True
        
        # Reset flag after delay to allow animation to finish
        Clock.schedule_once(lambda dt: setattr(self, '_ignore_resize', False), 0.5)

    def _force_fixed_size(self):
        if not self._is_maximized:
            Window.size = (480, 800)

    def open_dashboard(self):
        print("Dashboard icon clicked!")
        # Implement dashboard logic here
        pass

    def on_enter(self, *args):
        if not self._is_initialized:
            Clock.schedule_once(self._initialize_layout)

    def _initialize_layout(self, dt):
        log.debug("MainScreen: Performing first-time initialization.")
        self._ignore_resize = False 
        self._populate_views()
        # ... (rest of init)
        if self.player_engine:
            self.player_engine.bind(on_media_loaded=self._on_new_media_loaded)

        Window.bind(on_resize=self.on_window_resize)
        
        self.bind_hover_events()

        # Register the title bar for native dragging
        if 'drag_handle' in self.ids:
            self.window_manager.register_title_bar(self.ids.drag_handle)
        else:
            log.error("Drag handle ID not found, native dragging will not work.")

        self.update_layout(Window.width)
        self._is_initialized = True

    def on_window_resize(self, window, width, height):
        # 1. Check ignore flag (set during maximize/restore transitions)
        if getattr(self, '_ignore_resize', False):
            # Just update layout, don't enforce size
            self._schedule_layout_update(width)
            return

        # With Config resizable=0, we don't need to fight the OS.
        # Just update layout when size changes (e.g. maximize).
        self._schedule_layout_update(width)

    def _schedule_layout_update(self, width):
        # Throttle layout updates
        if hasattr(self, '_resize_trigger'):
            self._resize_trigger.cancel()
        self._resize_trigger = Clock.schedule_once(lambda dt: self.update_layout(width), 0.1)

    def update_layout(self, width):
        new_layout = 'desktop' if width > LAYOUT_BREAKPOINT else 'mobile'
        
        if new_layout != self._current_layout:
            log.info(f"Layout breakpoint crossed. Switching to '{new_layout}' layout at width {width}.")
            self._current_layout = new_layout
            
            if 'layout_manager' in self.ids:
                self.ids.layout_manager.current = f'{new_layout}_layout'
                self._transfer_views()
                self._restore_active_view()
            else:
                log.error("CRITICAL: 'layout_manager' not found in ids. UI cannot switch layouts.")

    def _on_new_media_loaded(self, instance, media_path, duration_ms):
        """
        This is the central trigger for all theme updates.
        """
        if media_path:
            track_meta = self.library_manager.get_track_details_by_filepath(media_path)
            self.top_bar_title = track_meta.get('title', "Unknown Title")
            
            art_path = self.library_manager.get_album_art_path_for_file(media_path)
            self._update_theme_from_art(art_path)
        else:
            self.top_bar_title = "Harmony Player"
            self._update_theme_from_art(None)

    def _update_theme_from_art(self, art_path):
        """
        Coordinates the entire theme update process.
        """
        app = MDApp.get_running_app()
        theme_dict = get_theme_colors_from_art(art_path)
        apply_theme_colors(app, theme_dict)
        
        Clock.schedule_once(self.update_theme_dependent_colors)

    def update_theme_dependent_colors(self, *args):
        """
        This function is called whenever the theme changes.
        """
        log.debug("MainScreen: Broadcasting theme update to all child views.")
        theme_cls = MDApp.get_running_app().theme_cls

        for view in self._views.values():
            if hasattr(view, 'update_theme_colors'):
                view.update_theme_colors()

        # Update Mobile Nav Colors
        if self._current_layout == 'mobile' and 'bottom_nav' in self.ids:
            bottom_nav = self.ids.bottom_nav
            for child in bottom_nav.children:
                if hasattr(child, 'active') and child.active:
                     child.md_bg_color = theme_cls.primary_color
        
        # Update Desktop Nav Colors (Now same structure as mobile)
        if self._current_layout == 'desktop' and 'nav_rail' in self.ids:
            nav_rail = self.ids.nav_rail
            for child in nav_rail.children:
                if hasattr(child, 'active') and child.active:
                     child.md_bg_color = theme_cls.primary_color
                elif hasattr(child, 'active'):
                     child.md_bg_color = [0, 0, 0, 0]

    def _populate_views(self):
        if self._views:
            return

        log.debug("Populating view widgets for the first time.")
        from harmony_player.ui.screens.library_view import LibraryView
        from harmony_player.ui.screens.now_playing_view import NowPlayingView
        from harmony_player.ui.screens.playlist_view import PlaylistView

        self._views = {
            "now_playing_screen": NowPlayingView(
                player_engine=self.player_engine, 
                library_manager=self.library_manager, 
                settings_manager=self.settings_manager,
                playlist_manager=self.playlist_manager
            ),
            "library_screen": LibraryView(
                player_engine=self.player_engine, 
                library_manager=self.library_manager, 
                settings_manager=self.settings_manager,
                playlist_manager=self.playlist_manager
            ),
            "playlist_screen": PlaylistView(
                player_engine=self.player_engine, 
                library_manager=self.library_manager,
                playlist_manager=self.playlist_manager
            ),
        }
        log.info("Main views have been instantiated.")

    def _transfer_views(self):
        if not self._views:
            log.warning("Views not populated, cannot transfer.")
            return

        for view in self._views.values():
            if view.parent:
                view.parent.remove_widget(view)

        if self._current_layout == 'desktop':
            log.debug("Transferring views to DESKTOP layout containers.")
            for screen_name, view_widget in self._views.items():
                if self.ids.desktop_screen_manager.has_screen(screen_name):
                    target_screen = self.ids.desktop_screen_manager.get_screen(screen_name)
                    target_screen.add_widget(view_widget)
                else:
                    log.error(f"Desktop screen '{screen_name}' not found for view transfer.")
        
        elif self._current_layout == 'mobile':
            log.debug("Transferring views to MOBILE layout containers.")
            mobile_containers = {
                "now_playing_screen": self.ids.get('mobile_now_playing_screen'),
                "library_screen": self.ids.get('mobile_library_screen'),
                "playlist_screen": self.ids.get('mobile_playlist_screen'),
            }
            for screen_name, view_widget in self._views.items():
                container = mobile_containers.get(screen_name)
                if container:
                    container.add_widget(view_widget)
                else:
                    log.error(f"Mobile container for '{screen_name}' not found for view transfer.")

    def _restore_active_view(self):
        def restore_nav_state(container):
            if container:
                for child in container.children:
                    if hasattr(child, 'screen_name'):
                        child.active = (child.screen_name == self.current_sub_view)
                        # Also force color update
                        if child.active:
                            child.md_bg_color = MDApp.get_running_app().theme_cls.primary_color
                        else:
                             child.md_bg_color = [0, 0, 0, 0]

        def restore_mobile(dt):
            if 'mobile_screen_manager' in self.ids:
                 if self.ids.mobile_screen_manager.has_screen(self.current_sub_view):
                    self.ids.mobile_screen_manager.current = self.current_sub_view
                 
                 if 'bottom_nav' in self.ids:
                     restore_nav_state(self.ids.bottom_nav)
        
        def restore_desktop(dt):
            if self.ids.desktop_screen_manager.has_screen(self.current_sub_view):
                self.ids.desktop_screen_manager.current = self.current_sub_view
                
                if 'nav_rail' in self.ids:
                    restore_nav_state(self.ids.nav_rail)
        
        if self._current_layout == 'mobile':
            Clock.schedule_once(restore_mobile)
        else:
            Clock.schedule_once(restore_desktop)
        
        if self.current_sub_view == "library_screen":
            self.refresh_visible_library_content()

    def switch_view(self, screen_name: str):
        self.current_sub_view = screen_name
        
        # Helper to update active state of nav items
        def update_nav_active(container):
            if container:
                for child in container.children:
                    if hasattr(child, 'screen_name'):
                        child.active = (child.screen_name == screen_name)
                        # Re-apply theme colors logic instantly
                        if child.active:
                            child.md_bg_color = MDApp.get_running_app().theme_cls.primary_color
                        else:
                            child.md_bg_color = [0, 0, 0, 0]

        if self._current_layout == 'desktop':
            if self.ids.desktop_screen_manager.has_screen(screen_name):
                self.ids.desktop_screen_manager.current = screen_name
                if 'nav_rail' in self.ids:
                    update_nav_active(self.ids.nav_rail)
        
        elif self._current_layout == 'mobile':
            if self.ids.mobile_screen_manager.has_screen(screen_name):
                self.ids.mobile_screen_manager.current = screen_name
                if 'bottom_nav' in self.ids:
                    update_nav_active(self.ids.bottom_nav)

        if screen_name == "library_screen":
            self.refresh_visible_library_content()

    def refresh_visible_library_content(self):
        def do_refresh(dt):
            library_view = self._views.get("library_screen")
            if library_view and hasattr(library_view, "refresh_current_view"):
                log.debug("Refreshing library content.")
                library_view.refresh_current_view()
        
        Clock.schedule_once(do_refresh)

