# dad_player/ui/screens/playlist_view.py

import logging
from kivy.properties import ObjectProperty, ListProperty, StringProperty, BooleanProperty
from kivy.clock import Clock
from kivy.metrics import dp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.menu import MDDropdownMenu
from kivy.core.window import Window

from dad_player.utils.formatting import format_duration
from dad_player.utils.image_utils import get_placeholder_album_art_path

log = logging.getLogger(__name__)

class PlaylistView(MDBoxLayout):
    player_engine = ObjectProperty(None, allownone=True)
    library_manager = ObjectProperty(None, allownone=True)
    playlist_manager = ObjectProperty(None, allownone=True)

    song_list_data = ListProperty([])
    playlist_names_data = ListProperty([])
    active_playlist_name = StringProperty("Queue")
    is_mobile = BooleanProperty(False)

    _dialog = None
    _playlist_menu = None
    _placeholder_art = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._placeholder_art = get_placeholder_album_art_path()
        Clock.schedule_once(self._post_init)
        Window.bind(on_resize=self._on_window_resize)

    def _post_init(self, dt):
        self.bind(width=self.check_layout)
        self.check_layout(self, self.width)

    def on_kv_post(self, base_widget):
        super().on_kv_post(base_widget)  # Call super if overriding
        if self.playlist_manager:
            self.refresh_playlist_names()
            self.select_playlist("Queue")

    def check_layout(self, instance, width):
        self.is_mobile = width < dp(600)
        self.refresh_current_view()  # Refresh on layout change

    def _on_window_resize(self, window, width, height):
        self.check_layout(self, width)

    def on_playlist_manager(self, instance, value):
        if value:
            self.playlist_manager.bind(on_playlists_changed=self.refresh_playlist_names)
            # No initial calls here; handled in on_kv_post

    def on_player_engine(self, instance, value):
        if value:
            self.player_engine.bind(
                on_playlist_changed=self._update_queue_view,
                on_media_loaded=self._update_queue_view
            )

    def refresh_playlist_names(self, *args):
        if not self.playlist_manager: return

        names = ["Queue"] + self.playlist_manager.playlist_names
        self.playlist_names_data = [
            {"text": name, "on_release": lambda x=name: self.select_playlist(x)}
            for name in names
        ]
        
        menu_items = [
            {"text": name, "viewclass": "OneLineListItem",
             "on_release": lambda x=name: self.select_playlist_from_menu(x)}
            for name in names
        ]
        
        if not self._playlist_menu and self.ids.get('mobile_menu_button'):
            self._playlist_menu = MDDropdownMenu(
                caller=self.ids.mobile_menu_button, items=menu_items, width_mult=4)
        elif self._playlist_menu:
            self._playlist_menu.items = menu_items

    def select_playlist(self, name: str):
        self.active_playlist_name = name
        if name == "Queue":
            self._update_queue_view()
        else:
            self._update_user_playlist_view()

    def select_playlist_from_menu(self, name: str):
        self.select_playlist(name)
        if self._playlist_menu: self._playlist_menu.dismiss()

    def _update_queue_view(self, *args):
        if self.active_playlist_name != "Queue": return
        if not self.player_engine or not self.library_manager: return

        queue = self.player_engine.get_current_playlist_details()
        playing_path = self.player_engine.current_media_path
        
        seen = set()
        unique_data = [
            {'text': track.get('title', 'Unknown'),
             'secondary_text': track.get('artist', 'Unknown'),
             'tertiary_text': format_duration(track.get('duration', 0)),
             'art_path': self.library_manager.get_album_art_path_for_file(track['filepath']) or self._placeholder_art,
             'is_playing': playing_path == track['filepath'],
             'on_press_callback': lambda fp=track['filepath']: self.on_song_selected(fp)}
            for track in queue if track.get('filepath') and track['filepath'] not in seen and not seen.add(track['filepath'])
        ]
        self.song_list_data = unique_data
        self.refresh_current_view()

    def _update_user_playlist_view(self):
        if not self.playlist_manager or not self.library_manager: return

        filepaths = self.playlist_manager.get_tracks_for_playlist(self.active_playlist_name)
        playing_path = self.player_engine.current_media_path if self.player_engine else None

        seen = set()
        unique_data = [
            {'text': track.get('title', 'Unknown'),
             'secondary_text': track.get('artist', 'Unknown'),
             'tertiary_text': format_duration(track.get('duration', 0)),
             'art_path': self.library_manager.get_album_art_path_for_file(fp) or self._placeholder_art,
             'is_playing': playing_path == fp,
             'on_press_callback': lambda fp_ref=fp: self.on_song_selected(fp_ref)}
            for fp in filepaths if (track := self.library_manager.get_track_details_by_filepath(fp)) and fp not in seen and not seen.add(fp)
        ]
        self.song_list_data = unique_data
        self.refresh_current_view()

    def refresh_current_view(self):
        if 'playlist_rv' not in self.ids:  # Safeguard for early calls
            return
        rv = self.ids.playlist_rv
        rv.data = []  # Clear to prevent duplicates/artifacts
        rv.viewclass = 'SongListItem' if self.is_mobile else 'SongRowItem'
        rv.data = self.song_list_data
        rv.refresh_from_data()

    def on_song_selected(self, filepath: str):
        if not self.player_engine: return

        if self.active_playlist_name == "Queue":
            active_list = self.player_engine._get_active_playlist()
            if filepath in active_list:
                self.player_engine.play_from_playlist_by_index(active_list.index(filepath))
        else:
            playlist_tracks = self.playlist_manager.get_tracks_for_playlist(self.active_playlist_name)
            self.player_engine.load_playlist(playlist_tracks, play_index=playlist_tracks.index(filepath))

    def show_create_playlist_dialog(self):
        if not self._dialog:
            self._dialog = MDDialog(
                title="Create New Playlist", type="custom",
                content_cls=MDTextField(hint_text="Playlist Name"),
                buttons=[
                    MDFlatButton(text="CANCEL", on_release=lambda x: self._dialog.dismiss()),
                    MDFlatButton(text="CREATE", on_release=self._create_playlist_callback)])
        self._dialog.content_cls.text = ""
        self._dialog.open()

    def _create_playlist_callback(self, *args):
        playlist_name = self._dialog.content_cls.text
        if playlist_name and self.playlist_manager:
            self.playlist_manager.create_playlist(playlist_name)
        self._dialog.dismiss()