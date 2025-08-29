# dad_player/app.py

import logging
import os
import sys
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.uix.label import Label
from kivymd.app import MDApp
from kivymd.uix.screenmanager import MDScreenManager
from dad_player.constants import APP_NAME, APP_VERSION, CONFIG_KEY_CONSOLIDATE_ALBUMS
from dad_player.core.exceptions import VlcInitializationError
from dad_player.core.library_manager import LibraryManager
from dad_player.core.player_engine import PlayerEngine
from dad_player.core.settings_manager import SettingsManager
from dad_player.ui.screens.main_screen import MainScreen
from dad_player.ui.screens.settings_screen import SettingsScreen
from dad_player.ui.screens.track_details_view import TrackDetailsView
from dad_player.core.playlist_manager import PlaylistManager

log = logging.getLogger(__name__)

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class DadPlayerApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.settings_manager = None
        self.library_manager = None
        self.playlist_manager = None
        self.player_engine = None
        self.screen_manager = None
        self.floating_widget = None
        self.default_primary_palette = "Indigo"
        self.default_accent_palette = "Orange"

    def build(self):
        self.icon = resource_path('assets/icons/harmony_player_icon.ico')
        
        Window.size = (480, 800)
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = self.default_primary_palette
        self.theme_cls.accent_palette = self.default_accent_palette
        self.title = f"{APP_NAME} v{APP_VERSION}"
        
        Window.clearcolor = self.theme_cls.bg_darkest

        try:
            self.settings_manager = SettingsManager()
            self.settings_manager.bind(on_setting_changed=self._on_setting_changed)
            self.playlist_manager = PlaylistManager()
            self.library_manager = LibraryManager(settings_manager=self.settings_manager)
            self.player_engine = PlayerEngine(
                settings_manager=self.settings_manager,
                library_manager=self.library_manager,
                playlist_manager=self.playlist_manager
            )
        except VlcInitializationError as e:
            log.critical(f"App failed to start: {e}")
            return Label(text=f"Critical Error:\n{e}\nIs VLC installed?", halign="center")
        except Exception as e:
            log.critical(f"An unexpected error occurred during initialization: {e}", exc_info=True)
            return Label(text=f"An unexpected error occurred:\n{e}", halign="center")

        self._load_kv_files()
        self.screen_manager = MDScreenManager()
        
        main_screen = MainScreen(
            name="main_screen",
            player_engine=self.player_engine,
            library_manager=self.library_manager,
            settings_manager=self.settings_manager,
            playlist_manager=self.playlist_manager,
        )
        settings_screen = SettingsScreen(
            name="settings_screen",
            player_engine=self.player_engine,
            library_manager=self.library_manager,
            settings_manager=self.settings_manager,
        )
        track_details_screen = TrackDetailsView(name="track_details_view")

        self.screen_manager.add_widget(main_screen)
        self.screen_manager.add_widget(settings_screen)
        self.screen_manager.add_widget(track_details_screen)
        
        self.screen_manager.current = "main_screen"
        
        Window.bind(on_touch_down=self.on_window_touch_down)
        return self.screen_manager
    
    def _on_setting_changed(self, settings_manager_instance, key, value):
        if key == CONFIG_KEY_CONSOLIDATE_ALBUMS:
            log.info(f"'{key}' setting changed to '{value}'. Triggering library refresh.")
            try:
                main_screen = self.screen_manager.get_screen('main_screen')
                main_screen.refresh_visible_library_content()
                log.info("Library refresh command sent successfully.")
            except Exception as e:
                log.error(f"Failed to refresh library view after setting change: {e}", exc_info=True)

    def on_window_touch_down(self, window, touch):
        if self.floating_widget and not self.floating_widget.collide_point(*touch.pos):
            self.floating_widget.dismiss()
            return True

    def _load_kv_files(self):
        kv_path = resource_path(os.path.join("dad_player", "kv"))
        for root, _, files in os.walk(kv_path):
            for kv_file in files:
                if kv_file.endswith(".kv"):
                    log.debug(f"Loading KV file: {os.path.join(root, kv_file)}")
                    Builder.load_file(os.path.join(root, kv_file))

    def switch_screen(self, screen_name):
        log.debug(f"Attempting to switch screen to '{screen_name}'.")
        if self.screen_manager and self.screen_manager.has_screen(screen_name):
            self.screen_manager.current = screen_name
            log.debug(f"Successfully switched screen to '{screen_name}'.")
        else:
            log.error(f"Failed to switch screen: '{screen_name}' does not exist.")

    def show_track_details(self, track_path):
        log.debug(f"Request to show details for: {track_path}")
        details_screen = self.screen_manager.get_screen('track_details_view')
        
        track_data = self.library_manager.get_track_details_by_filepath(track_path)
        
        if track_data:
            details_screen.track_path = track_path
            details_screen.track_details = track_data
            details_screen.previous_screen = self.screen_manager.current
            details_screen.set_mode('view')
            self.switch_screen('track_details_view')
        else:
            log.error(f"Could not retrieve details for track: {track_path}")

    def save_track_details(self, track_path, new_data):
        try:
            log.info(f"Saving metadata for {track_path}")
            
            if 'album_art_path' in new_data:
                image_path = new_data.pop('album_art_path')
                self.library_manager.update_track_album_art(track_path, image_path)
            if new_data:
                self.library_manager.update_track_metadata(track_path, new_data)

        except Exception as e:
            log.error(f"Failed to save metadata: {e}")

    def on_stop(self):
        log.info("Harmony Player is shutting down.")
        if self.player_engine:
            self.player_engine.shutdown()
        if self.library_manager:
            self.library_manager.close()
