# dad_player/ui/screens/now_playing_view.py

import logging
import os
from kivy.animation import Animation
from kivy.core.image import Image as CoreImage
from kivy.core.window import Window
from kivy.properties import (
    NumericProperty, ObjectProperty, StringProperty, BooleanProperty
)
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.clock import Clock
from kivymd.app import MDApp

from dad_player.ui.widgets.enlarged_album_art import EnlargedAlbumArt
from dad_player.utils.formatting import format_duration
from dad_player.utils.image_utils import (
    process_and_cache_album_art, get_placeholder_album_art_path
)
from dad_player.constants import ALBUM_ART_NOW_PLAYING_SIZE
from dad_player.ui.screens.main_screen import LAYOUT_BREAKPOINT

log = logging.getLogger(__name__)

class NowPlayingView(MDBoxLayout):
    player_engine = ObjectProperty(None)
    library_manager = ObjectProperty(None)
    settings_manager = ObjectProperty(None)
    playlist_manager = ObjectProperty(None)
    album_art_texture = ObjectProperty(None, allownone=True)

    song_title_text = StringProperty("No Song Playing")
    artist_name_text = StringProperty("...")
    current_time_text = StringProperty("0:00")
    total_time_text = StringProperty("0:00")
    progress_slider_value = NumericProperty(0)
    progress_slider_max = NumericProperty(1000)
    volume_slider_value = NumericProperty(100)
    play_pause_icon_text = StringProperty("play-circle")
    blurred_bg_texture = ObjectProperty(None, allownone=True)
    shuffle_enabled = BooleanProperty(False)
    repeat_mode_icon = StringProperty("repeat-off")

    _is_seeking = False
    _default_placeholder_texture = None
    _default_blurred_placeholder_texture = None
    _current_track_path = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Clock.schedule_once(self._post_init)

    # --- functions ---

    def on_touch_down(self, touch):
        album_art_card = self.ids.get('album_art_card')
        if album_art_card and album_art_card.collide_point(*touch.pos):
            if touch.button == 'right':
                self.show_context_menu()
                return True
        return super().on_touch_down(touch)

    def show_context_menu(self):
        app = MDApp.get_running_app()
        if hasattr(app, 'floating_widget') and app.floating_widget:
            app.floating_widget.dismiss()
        
        menu_items = [
            {'icon': 'playlist-plus', 'callback': 'add_to_playlist'},
            {'icon': 'account-music', 'callback': self.view_artist},
            {'icon': 'album', 'callback': self.view_album},
            {'icon': 'information-outline', 'callback': self.show_details},
        ]

        art_widget = EnlargedAlbumArt(
            art_texture=self.album_art_texture,
            menu_items=menu_items,
            track_path=self._current_track_path,
            playlist_manager=self.playlist_manager
        )
        art_widget.open()

    # --- Placeholder Callbacks for Menu Items ---
    def view_artist(self):
        print("ACTION: View Artist")

    def view_album(self):
        print("ACTION: View Album")

    def show_details(self):
        print("ACTION: Show Details")

    def _post_init(self, dt):
        """Perform initialization after the widget is created."""
        self._load_placeholder_textures()
        if self.player_engine:
            self._bind_player_events()
            self.update_ui_from_player_state()
        else:
            log.warning("NowPlayingView initialized without a PlayerEngine.")
            self._apply_placeholder_art()

    def start_seek(self, slider, touch):
        if slider.collide_point(*touch.pos):
            self._is_seeking = True
            self.ids.seeker_hint_label.opacity = 1

    def update_seek_label(self, slider, touch):
        if self._is_seeking:
            formatted_time = format_duration(slider.value / 1000)
            self.ids.seeker_hint_label.text = formatted_time

    def end_seek(self, slider, touch):
        if self._is_seeking:
            self._is_seeking = False
            self.ids.seeker_hint_label.opacity = 0
            if self.player_engine:
                log.debug(f"Calling player_engine.seek() with value {slider.value}")
                self.player_engine.seek(slider.value)

    def _load_placeholder_textures(self):
        """Loads default art and its blurred version ONCE."""
        try:
            placeholder_path = get_placeholder_album_art_path()
            if placeholder_path and os.path.exists(placeholder_path):
                with open(placeholder_path, 'rb') as f:
                    raw_data = f.read()
                
                self._default_placeholder_texture = CoreImage(placeholder_path).texture
                
                blurred_path, _ = process_and_cache_album_art(raw_data, "placeholder_blurred", blur_radius=25)
                if blurred_path:
                    self._default_blurred_placeholder_texture = CoreImage(blurred_path).texture
        except Exception as e:
            log.error(f"Failed to load placeholder textures: {e}")

    def _bind_player_events(self):
        self.player_engine.bind(
            on_position_changed=self._on_position_changed,
            on_shuffle_mode_changed=self._on_shuffle_mode_changed,
            on_repeat_mode_changed=self._on_repeat_mode_changed,
            on_media_loaded=self._on_media_loaded,
            on_playback_state_change=self._on_playback_state_change,
        )

    def update_ui_from_player_state(self, *args):
        if not self.player_engine: return
        
        current_path = self.player_engine.current_media_path
        if current_path:
            track_meta = self.player_engine.get_metadata_for_track(current_path)
            self.song_title_text = track_meta.get('title', "Unknown Title")
            self.artist_name_text = track_meta.get('artist', "Unknown Artist")
            if self._current_track_path != current_path:
                self._current_track_path = current_path
                self.load_album_art(current_path)
        else:
            self.song_title_text = "No Song Playing"
            self.artist_name_text = "..."
            self._apply_placeholder_art()
            self._current_track_path = None

        if hasattr(self.player_engine, 'get_volume'):
            self.volume_slider_value = self.player_engine.get_volume()
        self._on_playback_state_change()
        self._on_shuffle_mode_changed(None, self.player_engine.shuffle_mode)
        self._on_repeat_mode_changed(None, self.player_engine.repeat_mode)

    def load_album_art(self, track_path):
        """Loads album art using the new caching utility."""
        raw_art_data = self.library_manager.get_raw_album_art_for_file(track_path)
        
        if raw_art_data:
            try:
                cached_art_path, cached_blurred_path = process_and_cache_album_art(
                    raw_art_data,
                    track_path,
                    size=(ALBUM_ART_NOW_PLAYING_SIZE, ALBUM_ART_NOW_PLAYING_SIZE),
                    blur_radius=25
                )
                
                if cached_art_path:
                    self.album_art_texture = CoreImage(cached_art_path).texture
                if cached_blurred_path:
                    self.blurred_bg_texture = CoreImage(cached_blurred_path).texture
                
                self._animate_album_art()
                return
            except Exception as e:
                log.error(f"Error processing album art for {track_path}: {e}")
        
        self._apply_placeholder_art()

    def _apply_placeholder_art(self):
        self.album_art_texture = self._default_placeholder_texture
        self.blurred_bg_texture = self._default_blurred_placeholder_texture

    def _animate_album_art(self):
        album_art_image = self.ids.get('album_art_np')
        if album_art_image:
            anim = Animation(opacity=0, duration=0.2) + Animation(opacity=1, duration=0.3)
            anim.start(album_art_image)

    def on_play_pause_button_press(self):
        if self.player_engine: self.player_engine.play_pause_toggle()

    def on_previous_button_press(self):
        if self.player_engine: self.player_engine.play_previous()

    def on_next_button_press(self):
        if self.player_engine: self.player_engine.play_next()
    
    def on_shuffle_button_press(self):
        if self.settings_manager:
            new_mode = not self.settings_manager.get_shuffle()
            self.settings_manager.set_shuffle(new_mode)

    def on_repeat_button_press(self):
        if self.settings_manager:
            current_mode = self.settings_manager.get_repeat_mode()
            next_mode = (current_mode + 1) % 3
            self.settings_manager.set_repeat_mode(next_mode)

    def handle_volume_change(self, slider):
        if self.player_engine and hasattr(self.player_engine, 'set_volume'):
            new_volume = int(slider.value)
            self.player_engine.set_volume(new_volume)

    def _on_media_loaded(self, instance, media_path, duration_ms):
        self.update_ui_from_player_state()

    def _on_playback_state_change(self, *args):
        if self.player_engine:
            self.play_pause_icon_text = "pause-circle" if self.player_engine.is_playing() else "play-circle"

    def _on_position_changed(self, instance, position_ms, duration_ms):
        self.progress_slider_max = duration_ms
        self.total_time_text = format_duration(duration_ms / 1000)
        
        if not self._is_seeking:
            self.progress_slider_value = position_ms
            self.current_time_text = format_duration(position_ms / 1000)

    def _on_shuffle_mode_changed(self, instance, shuffle_enabled):
        self.shuffle_enabled = shuffle_enabled

    def _on_repeat_mode_changed(self, instance, repeat_mode):
        if repeat_mode == 0: self.repeat_mode_icon = "repeat-off"
        elif repeat_mode == 1: self.repeat_mode_icon = "repeat-once"
        else: self.repeat_mode_icon = "repeat"
