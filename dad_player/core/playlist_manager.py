# dad_player/core/playlist_manager.py

import logging
import json
from pathlib import Path
from kivy.event import EventDispatcher
from kivy.properties import ListProperty, DictProperty

from dad_player.core.exceptions import PlaylistError, PlaylistExistsError, PlaylistNotFoundError
from dad_player.utils.file_utils import get_user_data_dir_for_app

log = logging.getLogger(__name__)

PLAYLISTS_FILENAME = "playlists.json"
QUEUE_PLAYLIST_NAME = "Queue"
RECENTS_PLAYLIST_NAME = "Recents"
RECENTS_MAX_SIZE = 30


class PlaylistManager(EventDispatcher):
    __events__ = ('on_playlist_list_changed', 'on_playlist_content_changed')

    playlist_names = ListProperty([])
    playlists = DictProperty({})

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        user_data_dir = Path(get_user_data_dir_for_app())
        self._playlists_path = user_data_dir / PLAYLISTS_FILENAME
        self.load_playlists()

    def load_playlists(self):
        """Loads playlists from the JSON file into memory."""
        log.info(f"Loading playlists from: {self._playlists_path}")
        if self._playlists_path.exists():
            try:
                with open(self._playlists_path, 'r', encoding='utf-8') as f:
                    self.playlists = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                log.error(f"Failed to load or parse playlists file: {e}")
                self.playlists = {}
        else:
            self.playlists = {}

        if QUEUE_PLAYLIST_NAME not in self.playlists:
            self.playlists[QUEUE_PLAYLIST_NAME] = []
        if RECENTS_PLAYLIST_NAME not in self.playlists:
            self.playlists[RECENTS_PLAYLIST_NAME] = []

        self._update_public_properties()
        log.info(f"Loaded {len(self.playlist_names)} user playlists.")
        self.dispatch('on_playlist_list_changed')

    def _save_playlists(self, content_changed_playlist: str = None):
        try:
            self._playlists_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._playlists_path, 'w', encoding='utf-8') as f:
                json.dump(self.playlists, f, indent=4)
            
            if content_changed_playlist:
                self.dispatch('on_playlist_content_changed', content_changed_playlist)
        except IOError as e:
            log.error(f"Failed to save playlists to {self._playlists_path}: {e}")
            raise PlaylistError(f"Could not save playlists: {e}")

    def _update_public_properties(self):
        special_lists = [QUEUE_PLAYLIST_NAME, RECENTS_PLAYLIST_NAME]
        self.playlist_names = sorted(
            [p for p in self.playlists.keys() if p not in special_lists]
        )

    def create_playlist(self, name: str):
        if not name or name.strip() == "":
            raise ValueError("Playlist name cannot be empty.")
        if name in [QUEUE_PLAYLIST_NAME, RECENTS_PLAYLIST_NAME] or name in self.playlists:
            raise PlaylistExistsError(f"Playlist '{name}' is a reserved name or already exists.")

        log.info(f"Creating new playlist: {name}")
        self.playlists[name] = []
        self._update_public_properties()
        self._save_playlists()
        self.dispatch('on_playlist_list_changed')

    def delete_playlist(self, name: str):
        if name in [QUEUE_PLAYLIST_NAME, RECENTS_PLAYLIST_NAME]:
            log.warning(f"Attempted to delete the special '{name}' playlist. Operation aborted.")
            return
        if name not in self.playlists:
            raise PlaylistNotFoundError(f"Playlist '{name}' not found.")

        log.info(f"Deleting playlist: {name}")
        del self.playlists[name]
        self._update_public_properties()
        self._save_playlists()
        self.dispatch('on_playlist_list_changed')

    def add_track_to_recents(self, filepath: str):
        recents = self.playlists.get(RECENTS_PLAYLIST_NAME, [])
        if filepath in recents:
            recents.remove(filepath)
        
        recents.insert(0, filepath)
        
        self.playlists[RECENTS_PLAYLIST_NAME] = recents[:RECENTS_MAX_SIZE]
        self._save_playlists(content_changed_playlist=RECENTS_PLAYLIST_NAME)

    def add_track_to_playlist(self, playlist_name: str, filepath: str):
        if playlist_name not in self.playlists:
            raise PlaylistNotFoundError(f"Playlist '{playlist_name}' not found.")
        
        if filepath not in self.playlists[playlist_name]:
            self.playlists[playlist_name].append(filepath)
            self._save_playlists(content_changed_playlist=playlist_name)
        else:
            log.warning(f"Track '{filepath}' already exists in playlist '{playlist_name}'.")

    def remove_track_from_playlist(self, playlist_name: str, filepath: str):
        if playlist_name not in self.playlists:
            raise PlaylistNotFoundError(f"Playlist '{playlist_name}' not found.")
        
        if filepath in self.playlists[playlist_name]:
            self.playlists[playlist_name].remove(filepath)
            self._save_playlists(content_changed_playlist=playlist_name)
        else:
            log.warning(f"Track '{filepath}' not found in playlist '{playlist_name}'.")

    def save_queue(self, filepaths: list):
        self.playlists[QUEUE_PLAYLIST_NAME] = filepaths
        self._save_playlists(content_changed_playlist=QUEUE_PLAYLIST_NAME)

    def get_tracks_for_playlist(self, playlist_name: str) -> list:
        return self.playlists.get(playlist_name, [])

    def on_playlist_list_changed(self, *args):
        log.debug("PlaylistManager: on_playlist_list_changed event fired.")
        pass
        
    def on_playlist_content_changed(self, playlist_name: str):
        log.debug(f"PlaylistManager: on_playlist_content_changed event fired for '{playlist_name}'.")
        pass
