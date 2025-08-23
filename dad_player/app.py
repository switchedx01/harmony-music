# dad_player/app.py

import logging
import os
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.uix.label import Label
from kivymd.app import MDApp
from kivymd.uix.screenmanager import MDScreenManager

from dad_player.constants import APP_NAME, APP_VERSION
from dad_player.core.exceptions import VlcInitializationError
from dad_player.core.library_manager import LibraryManager
from dad_player.core.player_engine import PlayerEngine
from dad_player.core.settings_manager import SettingsManager
from dad_player.ui.screens.main_screen import MainScreen
from dad_player.ui.screens.settings_screen import SettingsScreen
from dad_player.utils.color_utils import get_theme_colors_from_art, apply_theme_colors
from dad_player.core.playlist_manager import PlaylistManager

log = logging.getLogger(__name__)

class DadPlayerApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.settings_manager = None
        self.library_manager = None
        self.playlist_manager = None
        self.player_engine = None
        self.screen_manager = None
        self.default_primary_palette = "BlueGray"
        self.default_accent_palette = "Blue"

    def build(self):
        Window.size = (480, 800)
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = self.default_primary_palette
        self.theme_cls.accent_palette = self.default_accent_palette
        self.title = f"{APP_NAME} v{APP_VERSION}"

        try:
            self.settings_manager = SettingsManager()
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

        self.player_engine.bind(on_media_loaded=self._on_media_loaded)

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
        self.screen_manager.add_widget(main_screen)
        self.screen_manager.add_widget(settings_screen)
        
        self.screen_manager.current = "main_screen"
        
        return self.screen_manager
    
    def _load_kv_files(self):
        kv_path = os.path.join(os.path.dirname(__file__), "kv")
        for root, _, files in os.walk(kv_path):
            for kv_file in files:
                if kv_file.endswith(".kv"):
                    log.debug(f"Loading KV file: {os.path.join(root, kv_file)}")
                    Builder.load_file(os.path.join(root, kv_file))

    def switch_screen(self, screen_name):
        if self.screen_manager and self.screen_manager.has_screen(screen_name):
            self.screen_manager.current = screen_name
        else:
            log.error(f"Attempted to switch to non-existent screen: {screen_name}")

    def on_stop(self):
        log.info("Harmony Player is shutting down.")
        if self.player_engine:
            self.player_engine.shutdown()
        if self.library_manager:
            self.library_manager.close()

    def _on_media_loaded(self, instance, media_path, duration_ms):
        if not media_path:
            apply_theme_colors(self, self.default_primary_palette, self.default_accent_palette)
            return

        art_path = self.library_manager.get_album_art_path_for_file(media_path)
        theme = get_theme_colors_from_art(art_path)
        apply_theme_colors(self, theme['primary_color'], theme['accent_color'])
