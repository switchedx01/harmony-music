# dad_player/ui/screens/main_screen.py

import logging
import traceback
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.properties import ObjectProperty, StringProperty
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from dad_player.constants import LAYOUT_BREAKPOINT
from dad_player.core.exceptions import MetadataUpdateError

log = logging.getLogger(__name__)

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
        super().__init__(**kwargs)
        
    def on_enter(self, *args):
        if not self._is_initialized:
            Clock.schedule_once(self._initialize_layout)

    def _initialize_layout(self, dt):
        log.debug("MainScreen: Performing first-time initialization.")
        self._populate_views()
        
        if self.player_engine:
            self.player_engine.bind(on_media_loaded=self._update_top_bar_title)
        
        Window.bind(on_resize=self.on_window_resize)
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

    def _update_top_bar_title(self, instance, media_path, duration_ms):
        if media_path:
            track_meta = self.library_manager.get_track_details_by_filepath(media_path)
            self.top_bar_title = track_meta.get('title', "Unknown Title")
        else:
            self.top_bar_title = "Harmony Player"

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
        Clock.schedule_once(do_refresh, 0.05)
