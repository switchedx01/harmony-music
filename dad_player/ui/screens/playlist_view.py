# dad_player/ui/screens/playlist_view.py

import logging
from kivy.clock import Clock
from kivy.properties import ObjectProperty, ListProperty
from kivymd.uix.boxlayout import MDBoxLayout
from dad_player.utils.image_utils import get_placeholder_album_art_path
from dad_player.utils.formatting import format_duration

log = logging.getLogger(__name__)

class PlaylistView(MDBoxLayout):
    player_engine = ObjectProperty(None)
    library_manager = ObjectProperty(None)
    playlist_data = ListProperty([])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._placeholder_art = get_placeholder_album_art_path()
        if self.player_engine:
            self.player_engine.bind(
                on_playlist_changed=self.refresh_playlist,
                on_playback_started=self.refresh_playlist
            )
        Clock.schedule_once(self.refresh_playlist)

    def refresh_playlist(self, *args):
        current_queue = self.player_engine.get_current_playlist_details()
        current_playing_path = self.player_engine.current_media_path
        
        new_data = []
        for track in current_queue:
            filepath = track.get('filepath')
            if not filepath: continue
            
            art_path = self.library_manager.get_album_art_path_for_file(filepath)
            new_data.append({
                'text': track.get('title', 'Unknown Title'),
                'secondary_text': track.get('artist', 'Unknown Artist'),
                'tertiary_text': format_duration(track.get('duration', 0)),
                'art_path': art_path or self._placeholder_art,
                'is_playing': current_playing_path == filepath,
                'on_press_callback': lambda fp=filepath: self.on_song_selected(fp)
            })
        self.playlist_data = new_data
        
        rv = self.ids.get('playlist_rv')
        if rv:
            rv.data = self.playlist_data
            rv.refresh_from_data()

    def on_song_selected(self, filepath):
        active_list = self.player_engine._get_active_playlist()
        if filepath in active_list:
            idx = active_list.index(filepath)
            self.player_engine.play_from_playlist_by_index(idx)

    def on_clear_playlist_button_press(self):
        if self.player_engine:
            self.player_engine.clear_playlist()
