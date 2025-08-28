# dad_player/core/settings_manager.py

import logging
import os
from kivy.event import EventDispatcher
from kivy.storage.jsonstore import JsonStore

from dad_player.constants import (
    CONFIG_KEY_AUTOPLAY,
    CONFIG_KEY_CONSOLIDATE_ALBUMS,
    CONFIG_KEY_LAST_VOLUME,
    CONFIG_KEY_MUSIC_FOLDERS,
    CONFIG_KEY_REPLAYGAIN,
    CONFIG_KEY_REPEAT,
    CONFIG_KEY_SHUFFLE,
    REPEAT_NONE,
    SETTINGS_FILE,
)
from dad_player.utils.file_utils import get_user_data_dir_for_app
from dad_player.core.exceptions import FolderExistsError, InvalidFolderPathError

log = logging.getLogger(__name__)

class SettingsManager(EventDispatcher):
    """Manages loading, saving, and accessing all application settings."""
    __events__ = ('on_setting_changed',)

    def __init__(self):
        super().__init__()
        self.user_data_dir = get_user_data_dir_for_app()
        self.settings_path = os.path.join(self.user_data_dir, SETTINGS_FILE)
        self.store = JsonStore(self.settings_path)
        self._defaults = {
            CONFIG_KEY_MUSIC_FOLDERS: [],
            CONFIG_KEY_AUTOPLAY: True,
            CONFIG_KEY_SHUFFLE: False,
            CONFIG_KEY_REPEAT: REPEAT_NONE,
            CONFIG_KEY_LAST_VOLUME: 0.75,
            CONFIG_KEY_REPLAYGAIN: False,
            CONFIG_KEY_CONSOLIDATE_ALBUMS: False,
        }
        self._load_settings()

    def _load_settings(self):
        """Ensures all default settings exist in the JSON store."""
        is_new_file = not os.path.exists(self.settings_path)
        for key, default_value in self._defaults.items():
            if not self.store.exists(key):
                self.store.put(key, value=default_value)
        if is_new_file:
            log.info(f"Created new settings file at: {self.settings_path}")
        else:
            log.info(f"Loaded settings from: {self.settings_path}")

    def get(self, key, default=None):
        """Gets a value from the settings store."""
        if self.store.exists(key):
            return self.store.get(key)["value"]
        if key in self._defaults:
            log.warning(f"Key '{key}' not in store, returning default value.")
            return self._defaults[key]
        log.error(f"Key '{key}' not found in store or defaults.")
        return default

    def put(self, key, value):
        """Puts a value into the settings store and dispatches an event."""
        self.store.put(key, value=value)
        log.debug(f"Setting '{key}' changed to '{value}'")
        self.dispatch('on_setting_changed', key, value)

    def get_music_folders(self):
        return self.get(CONFIG_KEY_MUSIC_FOLDERS, [])

    def add_music_folder(self, folder_path: str):
        norm_path = os.path.normpath(folder_path)
        if not os.path.isdir(norm_path):
            raise InvalidFolderPathError(f"Path is not a valid directory: {norm_path}")
        folders = self.get_music_folders()
        if norm_path in folders:
            raise FolderExistsError(f"Folder is already in the library: {norm_path}")
        folders.append(norm_path)
        self.put(CONFIG_KEY_MUSIC_FOLDERS, sorted(list(set(folders))))
        log.info(f"Added new music folder: {norm_path}")

    def remove_music_folder(self, folder_path: str):
        folders = self.get_music_folders()
        if folder_path in folders:
            folders.remove(folder_path)
            self.put(CONFIG_KEY_MUSIC_FOLDERS, sorted(folders))
            log.info(f"Removed music folder: {folder_path}")
            return True
        log.warning(f"Attempted to remove non-existent folder: {folder_path}")
        return False

    def get_autoplay(self) -> bool:
        return self.get(CONFIG_KEY_AUTOPLAY)

    def set_autoplay(self, value: bool):
        self.put(CONFIG_KEY_AUTOPLAY, bool(value))

    def get_shuffle(self) -> bool:
        return self.get(CONFIG_KEY_SHUFFLE)

    def set_shuffle(self, value: bool):
        self.put(CONFIG_KEY_SHUFFLE, bool(value))

    def get_repeat_mode(self) -> int:
        return self.get(CONFIG_KEY_REPEAT)

    def set_repeat_mode(self, value: int):
        self.put(CONFIG_KEY_REPEAT, int(value))

    def get_last_volume(self) -> float:
        return float(self.get(CONFIG_KEY_LAST_VOLUME))

    def set_last_volume(self, volume: float):
        self.put(CONFIG_KEY_LAST_VOLUME, max(0.0, min(1.0, float(volume))))
    
    def get_replaygain(self) -> bool:
        return self.get(CONFIG_KEY_REPLAYGAIN)
    
    def set_replaygain(self, value: bool):
        self.put(CONFIG_KEY_REPLAYGAIN, bool(value))

    def get_consolidate_albums(self) -> bool:
        return self.get(CONFIG_KEY_CONSOLIDATE_ALBUMS)

    def set_consolidate_albums(self, value: bool):
        self.put(CONFIG_KEY_CONSOLIDATE_ALBUMS, bool(value))

    def on_setting_changed(self, key, value):
        pass
