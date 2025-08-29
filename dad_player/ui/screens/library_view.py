# dad_player/ui/screens/library_view.py

import logging
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.properties import (
    BooleanProperty, DictProperty, NumericProperty, ObjectProperty, StringProperty
)
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.metrics import dp
from kivymd.app import MDApp
from dad_player.ui.widgets.album_grid_item import AlbumGridItem
from dad_player.ui.widgets.artist_list_item import ArtistListItem
from dad_player.ui.widgets.song_list_item import SongListItem, SongRowItem
from dad_player.ui.widgets.enlarged_album_art import EnlargedAlbumArt

from dad_player.utils.image_utils import get_placeholder_album_art_path
from dad_player.utils.formatting import format_duration

log = logging.getLogger(__name__)

class LibraryView(MDBoxLayout):
    __events__ = ('on_song_selected_for_playback',)

    player_engine = ObjectProperty(None)
    library_manager = ObjectProperty(None)
    settings_manager = ObjectProperty(None)
    playlist_manager = ObjectProperty(None)

    current_view_mode = StringProperty("all_albums")
    current_args = DictProperty({})
    display_path_text = StringProperty("All Albums")
    cycle_view_text = StringProperty("Artists")
    can_go_back = BooleanProperty(False)

    is_scanning = BooleanProperty(False)
    scan_progress_message = StringProperty("")
    progress_value = NumericProperty(0.0)

    is_wide = BooleanProperty(False)
    album_art_path = StringProperty("")
    album_artist = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._placeholder_art = get_placeholder_album_art_path()
        self._navigation_stack = []
        self._last_search_results = []
        self.bind(current_view_mode=self.on_view_mode_change)
        Clock.schedule_once(self._post_init)

    def _post_init(self, dt):
        self.library_manager.bind(
            on_scan_progress=self._on_scan_progress,
            on_scan_finished=self._on_scan_finished
        )
        Window.bind(on_resize=self._on_window_resize)
        self._update_layout_mode()
        self.navigate_to_all_albums()

    def on_view_mode_change(self, *args):
        if self.current_view_mode == "all_albums":
            self.cycle_view_text = "Artists"
        elif self.current_view_mode == "artists":
            self.cycle_view_text = "Songs"
        elif self.current_view_mode == "all_songs":
            self.cycle_view_text = "Albums"

    def _on_window_resize(self, window, width, height):
        self._update_layout_mode()
        Clock.unschedule(self.refresh_current_view)
        Clock.schedule_once(self.refresh_current_view, 0.1)

    def _update_layout_mode(self):
        self.is_wide = Window.width > dp(600)

    def _on_scan_progress(self, instance, progress, message):
        self.progress_value = progress
        self.scan_progress_message = message

    def _on_scan_finished(self, instance, message):
        self.is_scanning = False
        self.scan_progress_message = message
        self.refresh_current_view()

    def refresh_current_view(self, dt=None):
        log.debug(f"Refreshing library view for mode: {self.current_view_mode}")
        self.load_current_view()

    def load_current_view(self):
        no_results_label = self.ids.no_results_label
        no_results_label.height = 0
        no_results_label.opacity = 0
        self.can_go_back = bool(self._navigation_stack)

        data_map = {
            'on_context_menu_callback': self.show_song_context_menu
        }

        if self.current_view_mode == "all_albums":
            self.display_path_text = "All Albums"
            self.album_art_path = ""
            self.album_artist = ""
            consolidate = self.settings_manager.get_consolidate_albums()
            all_albums = self.library_manager.get_all_albums(consolidated=consolidate)
            data = [{
                'album_name': a['name'], 'artist_name': a['artist_name'],
                'art_path': a.get('art_path') or self._placeholder_art,
                'on_press_callback': lambda a=a: self.navigate_to_album(a['id'], a['name']),
                **data_map
            } for a in all_albums]
            self._update_rv('all_albums', data)

        elif self.current_view_mode == "artists":
            self.display_path_text = "All Artists"
            self.album_art_path = ""
            self.album_artist = ""
            artists = self.library_manager.get_all_artists()
            data = [{
                'text': a['name'],
                'on_press_callback': lambda a=a: self.navigate_to_albums_for_artist(a['id'], a['name']),
                **data_map
            } for a in artists]
            self._update_rv('artists', data)

        elif self.current_view_mode == "all_songs":
            self.display_path_text = "All Songs"
            self.album_art_path = ""
            self.album_artist = ""
            all_songs = self.library_manager.search_tracks('')
            self._last_search_results = all_songs
            data = [{
                'text': t.get('title', 'Unknown Title'),
                'secondary_text': f"{t.get('artist_name', 'Unknown Artist')} - {t.get('album_name', 'Unknown Album')}",
                'tertiary_text': format_duration(t.get('duration', 0)),
                'art_path': self.library_manager.get_album_art_path_for_file(t['filepath']) or self._placeholder_art,
                'filepath': t['filepath'],
                'on_press_callback': lambda t=t: self.on_song_selected(t['id'], t['filepath']),
                **data_map
            } for t in all_songs]
            self._update_rv('all_songs', data)

        elif self.current_view_mode == "albums_for_artist":
            artist_id = self.current_args['artist_id']
            artist_name = self.current_args['artist_name']
            self.display_path_text = artist_name
            self.album_art_path = ""
            self.album_artist = ""
            albums = self.library_manager.get_albums_by_artist(artist_id)
            data = [{
                'album_name': a['name'], 'artist_name': a['artist_name'],
                'art_path': a.get('art_path') or self._placeholder_art,
                'on_press_callback': lambda a=a: self.navigate_to_album(a['id'], a['name']),
                **data_map
            } for a in albums]
            self._update_rv('albums_for_artist', data)

        elif self.current_view_mode == "songs_for_album":
            album_id = self.current_args['album_id']
            album_name = self.current_args['album_name']
            self.display_path_text = album_name
            
            consolidate = self.settings_manager.get_consolidate_albums()
            is_from_consolidated_view = (self._navigation_stack and
                                       self._navigation_stack[-1]['mode'] == 'all_albums' and
                                       consolidate)

            if is_from_consolidated_view:
                tracks = self.library_manager.get_tracks_by_album_name(album_name)
            else:
                tracks = self.library_manager.get_tracks_by_album(album_id)

            if tracks:
                self.album_art_path = self.library_manager.get_album_art_path_for_file(tracks[0]['filepath']) or self._placeholder_art
                self.album_artist = tracks[0].get('artist_name', 'Unknown Artist')
            else:
                self.album_art_path = self._placeholder_art
                self.album_artist = 'Unknown Artist'
            data = [{
                'text': t.get('title', 'Unknown Title'),
                'secondary_text': t.get('artist_name', 'Unknown Artist'),
                'tertiary_text': format_duration(t.get('duration', 0)),
                'art_path': self.library_manager.get_album_art_path_for_file(t['filepath']) or self._placeholder_art,
                'filepath': t['filepath'],
                'on_press_callback': lambda t=t: self.on_song_selected(t['id'], t['filepath']),
                **data_map
            } for t in tracks]
            self._update_rv('songs_for_album', data)

        elif self.current_view_mode == "search_results":
            query = self.current_args.get('query', '')
            if not query:
                return
            self.display_path_text = f"Results for '{query}'"
            self.album_art_path = ""
            self.album_artist = ""
            results = self.library_manager.search_tracks(query)
            self._last_search_results = results
            data = [{
                'text': t.get('title', 'Unknown Title'),
                'secondary_text': f"{t.get('artist_name', 'Unknown Artist')} - {t.get('album_name', 'Unknown Album')}",
                'tertiary_text': format_duration(t.get('duration', 0)),
                'art_path': self.library_manager.get_album_art_path_for_file(t['filepath']) or self._placeholder_art,
                'filepath': t['filepath'],
                'on_press_callback': lambda t=t: self.on_song_selected(t['id'], t['filepath']),
                **data_map
            } for t in results]

            if not data:
                log.info("No search results, showing 'no results' label.")
                no_results_label.height = dp(48)
                no_results_label.opacity = 1
                self.ids.library_rv.opacity = 0
            else:
                self.ids.library_rv.opacity = 1

            self._update_rv('search_results', data)

    def _update_rv(self, mode, data):
        rv = self.ids.library_rv
        layout = self.ids.rv_layout

        if mode in ('all_albums', 'albums_for_artist'):
            rv.viewclass = 'AlbumGridItem'
            target_item_width = dp(180)
            if rv.width > 0:
                cols = max(2, int(rv.width / target_item_width))
                layout.cols = min(cols, 8)
            else:
                layout.cols = 2
            spacing = dp(16)
            if rv.width > 0 and layout.cols > 0:
                item_width = (rv.width - (layout.cols + 1) * spacing) / layout.cols
                layout.default_size = (None, item_width)
            else:
                layout.default_size = (None, dp(240))
        else:
            if mode == 'artists':
                rv.viewclass = 'ArtistListItem'
                layout.default_size = (None, dp(88))
            else:
                rv.viewclass = 'SongRowItem' if self.is_wide else 'SongListItem'
                layout.default_size = (None, dp(64) if self.is_wide else dp(88))
            layout.cols = 1
            layout.spacing = dp(2)

        rv.data = data
        rv.refresh_from_data()
        rv.scroll_y = 1

    def cycle_view(self):
        if self.current_view_mode in ["all_albums", "songs_for_album"]:
            self.navigate_to_artists()
        elif self.current_view_mode in ["artists", "albums_for_artist"]:
            self.navigate_to_all_songs()
        elif self.current_view_mode == "all_songs":
            self.navigate_to_all_albums()
        else:
            self.navigate_to_all_albums()

    def navigate_to_all_albums(self):
        self._navigation_stack = []
        self.current_view_mode = "all_albums"
        self.current_args = {}
        self.load_current_view()

    def navigate_to_artists(self):
        self._navigation_stack.append({
            'mode': self.current_view_mode,
            'args': self.current_args.copy()
        })
        self.current_view_mode = "artists"
        self.current_args = {}
        self.load_current_view()

    def navigate_to_all_songs(self):
        self._navigation_stack.append({
            'mode': self.current_view_mode,
            'args': self.current_args.copy()
        })
        self.current_view_mode = "all_songs"
        self.current_args = {}
        self.load_current_view()

    def navigate_to_albums_for_artist(self, artist_id, artist_name):
        self._navigation_stack.append({
            'mode': self.current_view_mode,
            'args': self.current_args.copy()
        })
        self.current_view_mode = "albums_for_artist"
        self.current_args = {'artist_id': artist_id, 'artist_name': artist_name}
        self.load_current_view()

    def navigate_to_album(self, album_id, album_name):
        self._navigation_stack.append({
            'mode': self.current_view_mode,
            'args': self.current_args.copy()
        })
        self.current_view_mode = "songs_for_album"
        self.current_args = {'album_id': album_id, 'album_name': album_name}
        self.load_current_view()

    def on_song_selected(self, track_id, filepath):
        if self.current_view_mode in ['search_results', 'all_songs']:
            playlist_filepaths = [track['filepath'] for track in self._last_search_results]
        else:
            album_tracks_data = self.ids.library_rv.data
            playlist_filepaths = [track['filepath'] for track in album_tracks_data]

        if filepath in playlist_filepaths:
            start_index = playlist_filepaths.index(filepath)
            self.player_engine.load_playlist(playlist_filepaths, play_index=start_index)
        
        self.dispatch('on_song_selected_for_playback', track_id)

    def go_back_library_navigation(self):
        if self.current_view_mode == "search_results":
            self.ids.search_field.text = ""

        if self._navigation_stack:
            prev = self._navigation_stack.pop()
            self.current_view_mode = prev['mode']
            self.current_args = prev['args']
            self.load_current_view()
        else:
            self.navigate_to_all_albums()

    def start_full_scan(self):
        self.is_scanning = True
        self.scan_progress_message = "Starting scan..."
        self.progress_value = 0
        self.library_manager.start_scan_music_library(full_rescan=True)
    
    def on_song_selected_for_playback(self, *args):
        pass

    def on_search_text(self, query: str):
        Clock.unschedule(self._perform_search)
        Clock.schedule_once(lambda dt: self._perform_search(query), 0.3)

    def _perform_search(self, query: str):
        query = query.strip()
        if not query:
            if self.current_view_mode == "search_results":
                self.go_back_library_navigation()
            return

        if self.current_view_mode != "search_results":
            self._navigation_stack.append({
                'mode': self.current_view_mode,
                'args': self.current_args.copy()
            })

        log.info(f"Performing search for: '{query}'")
        self.current_view_mode = "search_results"
        self.current_args = {'query': query}
        self.load_current_view()
    
    def show_song_context_menu(self, track_path):
        """Shows the context menu for a song."""
        log.info(f"Context menu requested for: {track_path}")

    def update_theme_colors(self):
        """Called by MainScreen to force a color refresh."""
        log.debug("LibraryView: Updating theme-dependent colors.")
        app = MDApp.get_running_app()
        theme_cls = app.theme_cls
        
        if 'cycle_view_button' in self.ids:
            self.ids.cycle_view_button.md_bg_color = theme_cls.primary_color
        if 'scan_button' in self.ids:
            self.ids.scan_button.md_bg_color = theme_cls.primary_color
