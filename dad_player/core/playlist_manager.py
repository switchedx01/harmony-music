# dad_player/core/playlist_manager.py

import logging
import json
from pathlib import Path
from kivy.event import EventDispatcher
from kivy.properties import ListProperty, DictProperty

from dad_player.utils.file_utils import get_user_data_dir_for_app

log = logging.getLogger(__name__)

PLAYLISTS_FILENAME = "playlists.json"
QUEUE_PLAYLIST_NAME = "Queue"

class PlaylistManager(EventDispatcher):
    __events__ = ('on_playlists_changed',)

    playlist_names = ListProperty([])
    playlists = DictProperty({})

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        user_data_dir = Path(get_user_data_dir_for_app())
        self._playlists_path = user_data_dir / PLAYLISTS_FILENAME
        self.load_playlists()

    def load_playlists(self):
        if self._playlists_path.exists():
            try:
                with open(self._playlists_path, 'r') as f:
                    self.playlists = json.load(f)
            except Exception as e:
                log.error(f"Failed to load playlists: {e}")
                self.playlists = {}
        
        if QUEUE_PLAYLIST_NAME not in self.playlists:
            self.playlists[QUEUE_PLAYLIST_NAME] = []

        self.playlist_names = sorted([p for p in self.playlists.keys() if p != QUEUE_PLAYLIST_NAME])
        log.info(f"Loaded {len(self.playlist_names)} user playlists.")
        self.dispatch('on_playlists_changed')

    def _save_playlists(self):
        try:
            with open(self._playlists_path, 'w') as f:
                json.dump(self.playlists, f, indent=4)
            self.dispatch('on_playlists_changed')
        except Exception as e:
            log.error(f"Failed to save playlists: {e}")

    def create_playlist(self, name: str) -> bool:
        if name == QUEUE_PLAYLIST_NAME or name in self.playlists:
            return False
        self.playlists[name] = []
        self.playlist_names = sorted([p for p in self.playlists.keys() if p != QUEUE_PLAYLIST_NAME])
        self._save_playlists()
        return True

    def delete_playlist(self, name: str):
        if name != QUEUE_PLAYLIST_NAME and name in self.playlists:
            del self.playlists[name]
            self.playlist_names = sorted([p for p in self.playlists.keys() if p != QUEUE_PLAYLIST_NAME])
            self._save_playlists()

    def update_queue(self, filepaths: list):
        """Persistently saves the current playing queue."""
        self.playlists[QUEUE_PLAYLIST_NAME] = filepaths
        self._save_playlists()

    def get_tracks_for_playlist(self, playlist_name: str) -> list:
        return self.playlists.get(playlist_name, [])

    def on_playlists_changed(self, *args):
        """Default handler for the on_playlists_changed event."""
        pass
