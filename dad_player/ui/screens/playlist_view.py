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
        Clock.schedule_once(self._post_init)

    def _post_init(self, dt):
        if self.playlist_manager:
            self.playlist_manager.bind(on_playlists_changed=self.refresh_playlist_names)
            self.refresh_playlist_names()
        
        if self.player_engine:
            self.player_engine.bind(
                on_playlist_changed=self._on_engine_playlist_changed,
                on_media_loaded=self._on_engine_media_loaded
            )
            
        self.select_playlist("Queue")

    def _on_engine_playlist_changed(self, *args):
        if self.active_playlist_name == "Queue":
            self.refresh_active_view_content()

    def _on_engine_media_loaded(self, *args):
        self.refresh_active_view_content()

    def refresh_active_view_content(self, *args):
        if not self.playlist_manager or not self.library_manager:
            log.warning("Playlist or Library manager not available to refresh content.")
            self.song_list_data = []
            return
            
        name = self.active_playlist_name
        log.debug(f"Refreshing content for playlist: {name}")
        
        filepaths = self.playlist_manager.get_tracks_for_playlist(name)
        
        tracks_details = []
        for fp in filepaths:
            details = self.library_manager.get_track_details_by_filepath(fp)
            if details:
                tracks_details.append(details)
            else:
                log.warning(f"Could not find details for track: {fp}")

        self._populate_song_list(tracks_details)

    def refresh_playlist_names(self, *args):
        """
        Rebuilds the navigation rail and refreshes the active content view
        to reflect the current data state.
        """
        if not self.playlist_manager or not self.ids.get('nav_rail'):
            return

        rail = self.ids.nav_rail
        static_item_texts = {"Queue", "Recents"}

        for child in rail.children[:]:
            if isinstance(child, MDNavigationRailItem) and child.text not in static_item_texts:
                rail.remove_widget(child)

        for name in reversed(self.playlist_manager.playlist_names):
            item = MDNavigationRailItem(text=name, icon="playlist-music")
            item.bind(on_release=lambda instance, p_name=name: self.select_playlist(p_name))
            rail.add_widget(item)

        if self.active_playlist_name not in self.playlist_manager.playlists:
            log.info(f"Active playlist '{self.active_playlist_name}' no longer exists. Switching to Queue.")
            self.active_playlist_name = "Queue"
        
        self.refresh_active_view_content()

        for item in rail.children:
            if isinstance(item, MDNavigationRailItem) and item.text == self.active_playlist_name:
                rail.set_active_item(item)
                break

    def select_playlist(self, name: str):
        """Selects a playlist, updates the content, and ensures the UI is synced."""
        log.debug(f"Attempting to select playlist: '{name}'")
        
        if name not in self.playlist_manager.playlists:
            log.warning(f"Attempted to select a non-existent playlist: '{name}'. Defaulting to Queue.")
            name = "Queue"

        self.active_playlist_name = name
        self.refresh_active_view_content()

        if self.ids and self.ids.get('nav_rail'):
            for item in self.ids.nav_rail.children:
                if isinstance(item, MDNavigationRailItem) and item.text == name:
                    self.ids.nav_rail.set_active_item(item)
                    break

    def _populate_song_list(self, tracks_details: list):
        playing_path = self.player_engine.current_media_path if self.player_engine else None
        
        song_data = []
        for track in tracks_details:
            if track and 'filepath' in track:
                song_data.append({
                    'text': track.get('title', 'Unknown Title'),
                    'secondary_text': f"{track.get('artist_name', 'Unknown Artist')} - {track.get('album_name', 'Unknown Album')}",
                    'tertiary_text': format_duration(track.get('duration', 0)),
                    'art_path': self.library_manager.get_album_art_path_for_file(track['filepath']) or self._placeholder_art,
                    'is_playing': playing_path == track['filepath'],
                    'filepath': track['filepath'],
                    'on_press_callback': lambda fp=track['filepath']: self.on_song_selected(fp)
                })
        self.song_list_data = song_data
        self.ids.playlist_rv.data = self.song_list_data
        self.ids.playlist_rv.refresh_from_data()


    def on_song_selected(self, filepath: str):
        if not self.player_engine: return
        
        current_playlist_filepaths = [item['filepath'] for item in self.ids.playlist_rv.data]
        if filepath in current_playlist_filepaths:
            start_index = current_playlist_filepaths.index(filepath)
            self.player_engine.load_playlist(current_playlist_filepaths, play_index=start_index)

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
            self._dialog.dismiss()
            Clock.schedule_once(lambda dt: self.select_playlist(playlist_name))
        except PlaylistExistsError as e:
            self.show_error_dialog(str(e))
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
        if self.active_playlist_name in ["Queue", "Recents"]: return

        confirm_dialog = MDDialog(
            title="Delete Playlist?",
            text=f"Are you sure you want to delete '{self.active_playlist_name}'? This cannot be undone.",
            buttons=[
                MDFlatButton(text="CANCEL", on_release=lambda x: confirm_dialog.dismiss()),
                MDFlatButton(text="DELETE", on_release=lambda x: self._delete_playlist_callback(confirm_dialog))
            ]
        )
        confirm_dialog.open()

    def _delete_playlist_callback(self, dialog_instance):
        dialog_instance.dismiss()
        try:
            playlist_to_delete = self.active_playlist_name
            self.select_playlist("Queue")
            self.playlist_manager.delete_playlist(playlist_to_delete)
        except Exception as e:
            log.error(f"Failed to delete playlist: {e}")
            self.show_error_dialog("An error occurred while deleting the playlist.")

    def show_error_dialog(self, text):
        if not hasattr(self, '_error_dialog'):
            self._error_dialog = MDDialog(title="Error", text=text, buttons=[MDFlatButton(text="OK", on_release=lambda x: self._error_dialog.dismiss())])
        self._error_dialog.text = text
        self._error_dialog.open()
