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
from kivymd.uix.navigationrail import MDNavigationRailItem

from dad_player.core.exceptions import PlaylistExistsError
from dad_player.utils.formatting import format_duration
from dad_player.utils.image_utils import get_placeholder_album_art_path

log = logging.getLogger(__name__)

class PlaylistView(MDBoxLayout):
    player_engine = ObjectProperty(None)
    library_manager = ObjectProperty(None)
    playlist_manager = ObjectProperty(None)

    song_list_data = ListProperty([])
    active_playlist_name = StringProperty("Queue")
    is_mobile = BooleanProperty(False)

    _dialog = None
    _playlist_menu = None
    _placeholder_art = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._placeholder_art = get_placeholder_album_art_path()
        self.bind(width=self._on_width_change)
        Clock.schedule_once(lambda dt: self._on_width_change(self, self.width))

    def on_kv_post(self, base_widget):
        if self.playlist_manager:
            self.refresh_playlist_names()
            self.select_playlist("Queue")

    def _on_width_change(self, instance, width):
        self.is_mobile = width < dp(700)
        self.refresh_current_view()

    def on_playlist_manager(self, instance, value):
        if value:
            self.playlist_manager.bind(on_playlists_changed=self.refresh_playlist_names)

    def on_player_engine(self, instance, value):
        if value:
            value.bind(
                on_playlist_changed=self._update_queue_view,
                on_media_loaded=self._update_queue_view
            )

    def refresh_playlist_names(self, *args):
        if not self.playlist_manager: return

        rail = self.ids.nav_rail
        for item in list(rail.children):
            if isinstance(item, MDNavigationRailItem) and item.text != "Queue":
                rail.remove_widget(item)

        names = self.playlist_manager.playlist_names
        for name in names:
            item = MDNavigationRailItem(text=name, icon="playlist-music")
            item.bind(on_active=lambda instance, x=name: self.select_playlist(x))
            rail.add_widget(item)

    def select_playlist(self, name: str):
        self.active_playlist_name = name
        if name == "Queue":
            self._update_queue_view()
        else:
            self._update_user_playlist_view()

        for item in self.ids.nav_rail.children:
            if isinstance(item, MDNavigationRailItem) and item.text == name:
                self.ids.nav_rail.set_active_item(item)
                break

    def _update_queue_view(self, *args):
        if self.active_playlist_name != "Queue": return
        if not self.player_engine or not self.library_manager: return

        queue = self.player_engine.get_current_playlist_details()
        self._populate_song_list(queue)

    def _update_user_playlist_view(self):
        if not self.playlist_manager or not self.library_manager: return

        filepaths = self.playlist_manager.get_tracks_for_playlist(self.active_playlist_name)
        tracks_details = [
            self.library_manager.get_track_details_by_filepath(fp) for fp in filepaths
        ]
        self._populate_song_list(tracks_details)

    def _populate_song_list(self, tracks_details: list):
        playing_path = self.player_engine.current_media_path if self.player_engine else None

        self.song_list_data = [
            {
                'text': track.get('title', 'Unknown'),
                'secondary_text': track.get('artist', 'Unknown'),
                'tertiary_text': format_duration(track.get('duration', 0)),
                'art_path': self.library_manager.get_album_art_path_for_file(track['filepath']) or self._placeholder_art,
                'is_playing': playing_path == track['filepath'],
                'on_press_callback': lambda fp=track['filepath']: self.on_song_selected(fp)
            }
            for track in tracks_details if track and track.get('filepath')
        ]
        self.refresh_current_view()

    def refresh_current_view(self):
        if 'playlist_rv' not in self.ids: return
        rv = self.ids.playlist_rv
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
                title="Create New Playlist",
                type="custom",
                content_cls=MDTextField(hint_text="Playlist Name", required=True),
                buttons=[
                    MDFlatButton(text="CANCEL", on_release=lambda x: self._dialog.dismiss()),
                    MDFlatButton(text="CREATE", on_release=self._create_playlist_callback),
                ],
            )
        self._dialog.content_cls.text = ""
        self._dialog.open()

    def _create_playlist_callback(self, *args):
        playlist_name = self._dialog.content_cls.text.strip()
        if not playlist_name:
            self._dialog.content_cls.error = True
            return

        try:
            self.playlist_manager.create_playlist(playlist_name)
            self.select_playlist(playlist_name)
            self._dialog.dismiss()
        except PlaylistExistsError:
            self.show_error_dialog(f"A playlist named '{playlist_name}' already exists.")
        except Exception as e:
            log.error(f"Failed to create playlist: {e}")
            self.show_error_dialog("An unexpected error occurred.")

    def open_playlist_menu(self, button):
        menu_items = [
            {"text": "Delete Playlist", "on_release": self.show_delete_confirmation}
        ]
        self._playlist_menu = MDDropdownMenu(caller=button, items=menu_items, width_mult=4)
        self._playlist_menu.open()

    def show_delete_confirmation(self):
        self._playlist_menu.dismiss()
        if self.active_playlist_name == "Queue": return

        confirm_dialog = MDDialog(
            title="Delete Playlist?",
            text=f"Are you sure you want to delete '{self.active_playlist_name}'? This cannot be undone.",
            buttons=[
                MDFlatButton(text="CANCEL", on_release=lambda x: x.parent.parent.parent.dismiss()),
                MDFlatButton(text="DELETE", on_release=self._delete_playlist_callback)
            ]
        )
        confirm_dialog.open()

    def _delete_playlist_callback(self, button):
        button.parent.parent.parent.dismiss()
        try:
            self.playlist_manager.delete_playlist(self.active_playlist_name)
            self.select_playlist("Queue") # Go back to queue after deletion
        except Exception as e:
            log.error(f"Failed to delete playlist: {e}")
            self.show_error_dialog("An error occurred while deleting the playlist.")

    def show_error_dialog(self, text):
        error_dialog = MDDialog(title="Error", text=text, buttons=[MDFlatButton(text="OK")])
        error_dialog.open()
