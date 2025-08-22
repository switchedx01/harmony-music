# dad_player/core/player_engine.py

import logging
import os
import random
import vlc
from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.properties import ObjectProperty

from dad_player.constants import (
    CONFIG_KEY_SHUFFLE, CONFIG_KEY_REPEAT, REPEAT_NONE, REPEAT_PLAYLIST, REPEAT_SONG
)
from dad_player.core.exceptions import VlcInitializationError, MediaLoadError

log = logging.getLogger(__name__)

class PlayerEngine(EventDispatcher):
    """
    Handles all audio playback, playlist management, and state tracking using python-vlc.
    """
    __events__ = (
        "on_playback_state_change",
        "on_position_changed", "on_media_loaded", "on_error", "on_playlist_changed",
        "on_shuffle_mode_changed", "on_repeat_mode_changed", "on_volume_changed",
    )

    current_song = ObjectProperty(None, allownone=True)

    def __init__(self, settings_manager, library_manager, **kwargs):
        super().__init__(**kwargs)
        self.settings_manager = settings_manager
        self.library_manager = library_manager

        self._playlist = []
        self._playlist_metadata = {}
        self._shuffled_playlist = []
        self._current_playlist_index = -1
        self.current_media_path = None
        self.current_media_duration_ms = 0
        self._position_update_event = None

        self.shuffle_mode = self.settings_manager.get_shuffle()
        self.repeat_mode = self.settings_manager.get_repeat_mode()
        
        instance_args = ["--no-video", "--quiet", "--no-metadata-network-access"]
        if self.settings_manager.get_replaygain():
            instance_args.append("--replaygain-mode=track")

        try:
            self.vlc_instance = vlc.Instance(" ".join(instance_args))
            self.player = self.vlc_instance.media_player_new()
            log.info(f"VLC initialized with args: {' '.join(instance_args)}")
        except Exception as e:
            log.critical(f"Failed to initialize VLC instance or player: {e}")
            raise VlcInitializationError(f"VLC initialization failed: {e}. Is VLC installed correctly?")

        self.event_manager = self.player.event_manager()
        self._bind_vlc_events()
        self.bind_settings_events()
        self.set_volume(self.settings_manager.get_last_volume() * 100)

    def _bind_vlc_events(self):
        """Attaches callbacks to VLC media player events."""
        self.event_manager.event_attach(vlc.EventType.MediaPlayerPlaying, self._on_vlc_state_change)
        self.event_manager.event_attach(vlc.EventType.MediaPlayerPaused, self._on_vlc_state_change)
        self.event_manager.event_attach(vlc.EventType.MediaPlayerStopped, self._on_vlc_state_change)
        self.event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_vlc_end_reached)
        self.event_manager.event_attach(vlc.EventType.MediaPlayerEncounteredError, self._on_vlc_error)

    def bind_settings_events(self):
        """Binds to events from the SettingsManager to react to changes."""
        self.settings_manager.bind(on_setting_changed=self._on_setting_changed)

    def _on_setting_changed(self, instance, key, value):
        log.debug(f"PlayerEngine received setting change: {key} = {value}")
        if key == CONFIG_KEY_SHUFFLE and self.shuffle_mode != value:
            self.set_shuffle_mode(value)
        elif key == CONFIG_KEY_REPEAT and self.repeat_mode != value:
            self.set_repeat_mode(value)

    def _schedule_dispatch(self, event_name, *args):
        Clock.schedule_once(lambda dt: self.dispatch(event_name, *args), 0)

    def _on_vlc_state_change(self, event):
        if self.player.is_playing():
            self._start_position_updater()
        else:
            self._stop_position_updater()
        self._schedule_dispatch("on_playback_state_change")

    def _on_vlc_end_reached(self, event):
        self._stop_position_updater()
        self._schedule_dispatch("on_playback_state_change")
        Clock.schedule_once(lambda dt: self.play_next(from_song_end=True), 0.1)

    def _on_vlc_error(self, event):
        self._stop_position_updater()
        log.error(f"VLC playback error for: {self.current_media_path}")
        self._schedule_dispatch("on_error", f"VLC error for {self.current_media_path}")

    def _start_position_updater(self):
        self._stop_position_updater()
        self._position_update_event = Clock.schedule_interval(self._update_position, 0.25)

    def _stop_position_updater(self):
        if self._position_update_event:
            self._position_update_event.cancel()
            self._position_update_event = None

    def _update_position(self, dt):
        if not self.player or not self.is_playing():
            return

        pos_ms = self.player.get_time()
        if pos_ms == -1: return

        if self.current_media_duration_ms <= 0:
            duration = self.player.get_length()
            if duration > 0:
                self.current_media_duration_ms = duration
        
        if self.current_media_duration_ms > 0:
            self.dispatch("on_position_changed", pos_ms, self.current_media_duration_ms)

    def load_media(self, file_path: str, play_immediately: bool = False):
        if not file_path or not os.path.exists(file_path):
            raise MediaLoadError(f"File not found: {file_path}")

        self.stop()
        self.current_media_path = file_path
        self.current_song = file_path

        track_metadata = self.library_manager.get_track_details_by_filepath(file_path)
        self._playlist_metadata[file_path] = track_metadata or {}

        media = self.vlc_instance.media_new_path(os.path.abspath(file_path))
        self.player.set_media(media)
        media.release()

        duration = self.player.get_length() or 0
        self.current_media_duration_ms = duration
        self._schedule_dispatch("on_media_loaded", self.current_media_path, duration)

        if play_immediately:
            self.play()

    def play(self):
        if self.player and self.current_media_path:
            self.player.play()

    def play_pause_toggle(self):
        if self.current_media_path:
            self.player.pause()

    def stop(self):
        if self.player:
            self.player.stop()

    def seek(self, position_ms: int):
        """Seeks to a position given in milliseconds."""
        log.debug(f"Seek called with position_ms={position_ms}")
        if self.player and self.current_media_path:
            seekable = self.player.is_seekable()
            log.debug(f"Media is seekable: {seekable}")
            if seekable:
                self._stop_position_updater()
                self.player.set_time(int(position_ms))
                
                if self.current_media_duration_ms > 0:
                    self.dispatch("on_position_changed", int(position_ms), self.current_media_duration_ms)
                
                Clock.schedule_once(lambda dt: self._start_position_updater(), 0.5)
            else:
                log.warning("Seek failed: media is not seekable.")
        else:
            log.warning("Seek failed: no player or media path.")

    def set_volume(self, volume_0_to_100: int):
        """Sets the player volume (0-100)."""
        if self.player:
            clamped_volume = max(0, min(100, int(volume_0_to_100)))
            self.player.audio_set_volume(clamped_volume)
            self.settings_manager.set_last_volume(clamped_volume / 100.0)
            log.debug(f"Volume set to {clamped_volume}")
    
    def get_volume(self) -> int:
        """Returns the current player volume (0-100)."""
        if self.player:
            return self.player.audio_get_volume()
        return 100

    def is_playing(self) -> bool:
        return self.player.is_playing() if self.player else False

    def get_metadata_for_track(self, track_path: str) -> dict:
        return self._playlist_metadata.get(track_path, {})
        
    def get_current_position_ms(self) -> int:
        """Returns the current playback position in milliseconds."""
        if self.player:
            return self.player.get_time()
        return 0

    def _get_active_playlist(self):
        return self._shuffled_playlist if self.shuffle_mode else self._playlist

    def load_playlist(self, filepaths: list, play_index: int = 0):
        self.clear_playlist(dispatch_event=False)
        self._playlist = [p for p in filepaths if os.path.exists(p)]
        
        if self.shuffle_mode:
            self._shuffled_playlist = list(self._playlist)
            random.shuffle(self._shuffled_playlist)
        
        self._schedule_dispatch("on_playlist_changed", self.get_current_playlist_details())
        
        active_list = self._get_active_playlist()
        if active_list and 0 <= play_index < len(active_list):
            self.play_from_playlist_by_index(play_index)

    def clear_playlist(self, dispatch_event=True):
        self.stop()
        self._playlist = []
        self._shuffled_playlist = []
        self._playlist_metadata = {}
        self.current_media_path = None
        self.current_media_duration_ms = 0
        self.current_song = None
        self._current_playlist_index = -1
        if dispatch_event:
            self._schedule_dispatch("on_playlist_changed", [])
            self._schedule_dispatch("on_media_loaded", None, 0)

    def play_from_playlist_by_index(self, index: int):
        active_list = self._get_active_playlist()
        if 0 <= index < len(active_list):
            self._current_playlist_index = index
            self.load_media(active_list[index], play_immediately=True)

    def get_current_playlist_details(self) -> list:
        return [self.get_metadata_for_track(path) for path in self._get_active_playlist()]

    def set_shuffle_mode(self, shuffle_on: bool):
        if self.shuffle_mode == shuffle_on: return
        self.shuffle_mode = shuffle_on
        self.load_playlist(self._playlist, play_index=self._current_playlist_index)
        self._schedule_dispatch("on_shuffle_mode_changed", self.shuffle_mode)

    def set_repeat_mode(self, mode: int):
        if mode in [REPEAT_NONE, REPEAT_SONG, REPEAT_PLAYLIST] and self.repeat_mode != mode:
            self.repeat_mode = mode
            self._schedule_dispatch("on_repeat_mode_changed", self.repeat_mode)

    def play_next(self, from_song_end=False):
        active_list = self._get_active_playlist()
        if not active_list: return

        if self.repeat_mode == REPEAT_SONG and from_song_end:
            self.play_from_playlist_by_index(self._current_playlist_index)
            return

        new_index = self._current_playlist_index + 1
        if new_index >= len(active_list):
            if self.repeat_mode == REPEAT_PLAYLIST:
                new_index = 0
            else:
                self.stop()
                return
        self.play_from_playlist_by_index(new_index)

    def play_previous(self):
        if self.get_current_position_ms() > 3000:
            self.seek(0)
            return

        active_list = self._get_active_playlist()
        if not active_list: return

        new_index = self._current_playlist_index - 1
        if new_index < 0:
            if self.repeat_mode == REPEAT_PLAYLIST:
                new_index = len(active_list) - 1
            else:
                return
        self.play_from_playlist_by_index(new_index)

    def shutdown(self):
        log.info("Shutting down PlayerEngine.")
        self._stop_position_updater()
        if self.player:
            self.player.stop()
            self.player.release()
        if self.vlc_instance:
            self.vlc_instance.release()

    # --- Default Event Handlers ---
    def on_playback_state_change(self, *args): pass
    def on_position_changed(self, *args): pass
    def on_media_loaded(self, *args): pass
    def on_error(self, *args): pass
    def on_playlist_changed(self, *args): pass
    def on_shuffle_mode_changed(self, *args): pass
    def on_repeat_mode_changed(self, *args): pass
    def on_volume_changed(self, *args): pass
