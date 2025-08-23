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


class PlaylistManager(EventDispatcher):
    """
    Manages loading, saving, and manipulation of all playlists, including the
    special 'Queue' playlist. Acts as the single source of truth for playlist data.
    """
    __events__ = ('on_playlists_changed',)

    # Public properties that the UI can bind to.
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
                self.playlists = {}  # Start fresh if file is corrupt
        else:
            self.playlists = {}

        # Ensure the persistent queue always exists.
        if QUEUE_PLAYLIST_NAME not in self.playlists:
            self.playlists[QUEUE_PLAYLIST_NAME] = []

        self._update_public_properties()
        log.info(f"Loaded {len(self.playlist_names)} user playlists.")
        self.dispatch('on_playlists_changed')

    def _save_playlists(self):
        """Saves the current state of all playlists to the JSON file."""
        try:
            # Create parent directory if it doesn't exist
            self._playlists_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._playlists_path, 'w', encoding='utf-8') as f:
                json.dump(self.playlists, f, indent=4)
            # Dispatch event after a successful save
            self.dispatch('on_playlists_changed')
        except IOError as e:
            log.error(f"Failed to save playlists to {self._playlists_path}: {e}")
            # Optionally, raise a specific error here to be caught by the app's global error handler
            raise PlaylistError(f"Could not save playlists: {e}")

    def _update_public_properties(self):
        """Updates the ListProperty of names for UI binding."""
        # The UI should only see user-created playlists in this list.
        self.playlist_names = sorted(
            [p for p in self.playlists.keys() if p != QUEUE_PLAYLIST_NAME]
        )

    def create_playlist(self, name: str):
        """
        Creates a new, empty playlist.

        Args:
            name (str): The name for the new playlist.

        Raises:
            PlaylistExistsError: If a playlist with the same name already exists.
        """
        if not name or name.strip() == "":
            raise ValueError("Playlist name cannot be empty.")
        if name == QUEUE_PLAYLIST_NAME or name in self.playlists:
            raise PlaylistExistsError(f"Playlist '{name}' already exists.")

        log.info(f"Creating new playlist: {name}")
        self.playlists[name] = []
        self._update_public_properties()
        self._save_playlists()

    def delete_playlist(self, name: str):
        """
        Deletes a user-created playlist.

        Args:
            name (str): The name of the playlist to delete.

        Raises:
            PlaylistNotFoundError: If the playlist does not exist.
        """
        if name == QUEUE_PLAYLIST_NAME:
            log.warning("Attempted to delete the special 'Queue' playlist. Operation aborted.")
            return
        if name not in self.playlists:
            raise PlaylistNotFoundError(f"Playlist '{name}' not found.")

        log.info(f"Deleting playlist: {name}")
        del self.playlists[name]
        self._update_public_properties()
        self._save_playlists()

    def add_track_to_playlist(self, playlist_name: str, filepath: str):
        """
        Adds a track to a specified playlist.

        Args:
            playlist_name (str): The name of the target playlist.
            filepath (str): The file path of the track to add.

        Raises:
            PlaylistNotFoundError: If the playlist does not exist.
        """
        if playlist_name not in self.playlists:
            raise PlaylistNotFoundError(f"Playlist '{playlist_name}' not found.")
        
        # Avoid duplicates
        if filepath not in self.playlists[playlist_name]:
            log.info(f"Adding track '{filepath}' to playlist '{playlist_name}'.")
            self.playlists[playlist_name].append(filepath)
            self._save_playlists()
        else:
            log.warning(f"Track '{filepath}' already exists in playlist '{playlist_name}'.")

    def remove_track_from_playlist(self, playlist_name: str, filepath: str):
        """
        Removes a track from a specified playlist.

        Args:
            playlist_name (str): The name of the target playlist.
            filepath (str): The file path of the track to remove.

        Raises:
            PlaylistNotFoundError: If the playlist does not exist.
        """
        if playlist_name not in self.playlists:
            raise PlaylistNotFoundError(f"Playlist '{playlist_name}' not found.")
        
        if filepath in self.playlists[playlist_name]:
            log.info(f"Removing track '{filepath}' from playlist '{playlist_name}'.")
            self.playlists[playlist_name].remove(filepath)
            self._save_playlists()
        else:
            log.warning(f"Track '{filepath}' not found in playlist '{playlist_name}'.")

    def save_queue(self, filepaths: list):
        """Persistently saves the current playing queue."""
        self.playlists[QUEUE_PLAYLIST_NAME] = filepaths
        # Note: We don't dispatch 'on_playlists_changed' for queue updates
        # to avoid unnecessary UI refreshes of the playlist list itself.
        # The player_engine's on_playlist_changed event handles the queue view update.
        try:
            with open(self._playlists_path, 'w', encoding='utf-8') as f:
                json.dump(self.playlists, f, indent=4)
        except IOError as e:
            log.error(f"Failed to save queue state: {e}")


    def get_tracks_for_playlist(self, playlist_name: str) -> list:
        """
        Retrieves all track filepaths for a given playlist.

        Args:
            playlist_name (str): The name of the playlist.

        Returns:
            list: A list of file paths, or an empty list if not found.
        """
        return self.playlists.get(playlist_name, [])

    def on_playlists_changed(self, *args):
        """Default handler for the on_playlists_changed event."""
        log.debug("PlaylistManager: on_playlists_changed event fired.")
        pass

