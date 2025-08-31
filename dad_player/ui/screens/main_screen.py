# dad_player/ui/screens/main_screen.py

import logging
import sys
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.properties import ObjectProperty, StringProperty
from kivymd.uix.screen import MDScreen
from kivymd.app import MDApp
from dad_player.constants import LAYOUT_BREAKPOINT
from dad_player.utils.color_utils import get_theme_colors_from_art, apply_theme_colors
# Import the new hybrid window manager
from dad_player.utils.window_manager import WindowManager

log = logging.getLogger(__name__)

IS_WIN = sys.platform == 'win32'
if IS_WIN:
    try:
        import win32api
        import win32con
    except ImportError:
        log.warning("pywin32 is not installed. Maximize functionality will be limited.")
        IS_WIN = False


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
        
        # --- NEW HYBRID SETUP ---
        self._is_maximized = False
        self._old_window_pos = None
        self._old_window_size = None
        self.window_manager = WindowManager(self, resize_border=8)

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
        title_bar = self.ids.get('title_bar')
        is_over_button = False
        if title_bar:
            button_ids = ['dashboard_button', 'minimize_button', 'maximize_button', 'close_button']
            for button_id in button_ids:
                button = self.ids.get(button_id)
                if button:
                    if button.collide_point(*button.to_local(*pos)):
                        button.hovering = True
                        is_over_button = True
                    else:
                        button.hovering = False
        
        if is_over_button:
            Window.set_system_cursor('arrow')
            return

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
            Window.set_system_cursor('arrow')
    
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
        if self._is_maximized:
            if self._old_window_pos and self._old_window_size:
                Window.left, Window.top = self._old_window_pos
                Window.size = self._old_window_size
            else:
                Window.restore()
            self._is_maximized = False
        else:
            self._old_window_pos = (Window.left, Window.top)
            self._old_window_size = Window.size
            if IS_WIN:
                work_area = self._get_monitor_work_area()
                if work_area:
                    x, y, w, h = work_area
                    Window.left = x
                    Window.top = y 
                    Window.size = (w - x, h - y)
                else:
                    Window.maximize()
            else:
                Window.maximize()
            self._is_maximized = True
    
    def open_dashboard(self):
        print("Dashboard icon clicked!")

    def on_enter(self, *args):
        if not self._is_initialized:
            Clock.schedule_once(self._initialize_layout)

    def _initialize_layout(self, dt):
        log.debug("MainScreen: Performing first-time initialization.")
        self._populate_views()

        if self.player_engine:
            self.player_engine.bind(on_media_loaded=self._on_new_media_loaded)

        Window.bind(on_resize=self.on_window_resize)
        
        self.bind_hover_events()

        self.update_layout(Window.width)
        self._is_initialized = True

    def on_window_resize(self, window, width, height):
        self.update_layout(width)

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
        It commands all child views to update their own colors.
        """
        log.debug("MainScreen: Broadcasting theme update to all child views.")
        theme_cls = MDApp.get_running_app().theme_cls

        for view in self._views.values():
            if hasattr(view, 'update_theme_colors'):
                view.update_theme_colors()

        if self._current_layout == 'mobile' and 'bottom_nav' in self.ids:
            bottom_nav = self.ids.bottom_nav
            bottom_nav.selected_color_background = theme_cls.primary_color
            
            if hasattr(bottom_nav, 'ids') and 'tabs_bar' in bottom_nav.ids:
                for tab in bottom_nav.ids.tabs_bar.children:
                    tab.text_color_active = theme_cls.primary_color
        
        if self._current_layout == 'desktop' and 'nav_rail' in self.ids:
            nav_rail = self.ids.nav_rail
            nav_rail.selected_color_background = theme_cls.primary_color

    def _populate_views(self):
        if self._views:
            return

        log.debug("Populating view widgets for the first time.")
        from dad_player.ui.screens.library_view import LibraryView
        from dad_player.ui.screens.now_playing_view import NowPlayingView
        from dad_player.ui.screens.playlist_view import PlaylistView

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
        def restore_mobile(dt):
            if 'bottom_nav' in self.ids:
                self.ids.bottom_nav.switch_tab(self.current_sub_view)
        
        def restore_desktop(dt):
            if self.ids.desktop_screen_manager.has_screen(self.current_sub_view):
                self.ids.desktop_screen_manager.current = self.current_sub_view
                if 'nav_rail' in self.ids:
                    nav_rail = self.ids.nav_rail
                    for item in nav_rail.children:
                        if hasattr(item, 'name') and item.name == self.current_sub_view:
                            nav_rail.set_active_item(item)
                            break
        
        if self._current_layout == 'mobile':
            Clock.schedule_once(restore_mobile)
        else:
            Clock.schedule_once(restore_desktop)
        
        if self.current_sub_view == "library_screen":
            self.refresh_visible_library_content()

    def switch_view(self, screen_name: str):
        if self._current_layout == 'desktop':
            if self.ids.desktop_screen_manager.has_screen(screen_name):
                self.ids.desktop_screen_manager.current = screen_name
                if 'nav_rail' in self.ids:
                    nav_rail = self.ids.nav_rail
                    for item in nav_rail.children:
                        if hasattr(item, 'name') and item.name == screen_name:
                            nav_rail.set_active_item(item)
                            break
                if screen_name == "library_screen":
                    self.refresh_visible_library_content()
            else:
                log.error(f"Attempted to switch to non-existent desktop view: {screen_name}")
        self.current_sub_view = screen_name

    def on_switch_tabs(self, instance_tabs, instance_tab, instance_tab_label=None, tab_text=None):
        self.current_sub_view = instance_tab.name
        if instance_tab.name == "library_screen":
            self.refresh_visible_library_content()

    def refresh_visible_library_content(self):
        def do_refresh(dt):
            library_view = self._views.get("library_screen")
            if library_view and hasattr(library_view, "refresh_current_view"):
                log.debug("Refreshing library content.")
                library_view.refresh_current_view()

