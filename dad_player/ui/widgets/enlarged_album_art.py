# dad_player/ui/widgets/enlarged_album_art.py

import logging
from kivy.properties import ObjectProperty, StringProperty, ListProperty
from kivy.uix.modalview import ModalView
from kivy.core.window import Window
from kivymd.app import MDApp
from kivymd.uix.card import MDCard
from kivymd.uix.button import MDIconButton, MDFlatButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import OneLineAvatarListItem
from functools import partial
from dad_player.ui.screens.main_screen import LAYOUT_BREAKPOINT
from kivy.metrics import dp
from kivy.clock import Clock

log = logging.getLogger(__name__)

class EnlargedAlbumArt(MDCard):
    art_texture = ObjectProperty(None)
    track_path = StringProperty("")
    playlist_manager = ObjectProperty(None)
    layout_mode = StringProperty('mobile')
    menu_items = ListProperty([])
    
    _background_modal = None
    _playlist_dialog = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.md_bg_color = [0.15, 0.15, 0.15, 1]
        self.radius = [18]
        self.elevation = 12
        self.pos_hint = {'center_x': 0.5, 'center_y': 0.5}
        Window.bind(on_resize=self.on_window_resize)

    def on_kv_post(self, base_widget):
        self.on_window_resize(Window, Window.width, Window.height, force_update=True)

    def on_window_resize(self, window, width, height, force_update=False):
        art_size = min(width, height) * 0.7
        new_layout = 'desktop' if width > LAYOUT_BREAKPOINT else 'mobile'
        menu_area_size = dp(60)
        spacing = dp(self.spacing)
        total_padding = dp(self.padding[0]) * 2 if isinstance(self.padding, (list, tuple)) else dp(self.padding) * 2

        if new_layout == 'desktop':
            self.size = (art_size + spacing + menu_area_size + total_padding, art_size + total_padding)
        else:
            self.size = (art_size + total_padding, art_size + spacing + menu_area_size + total_padding)

        if new_layout != self.layout_mode or force_update:
            self.layout_mode = new_layout
            self.update_layout()

    def update_layout(self):
        self.ids.layout_manager.current = f"{self.layout_mode}_layout"
        self.populate_menu()

    def open(self):
        app = MDApp.get_running_app()
        if hasattr(app, 'floating_widget') and app.floating_widget:
            app.floating_widget.dismiss()
        app.floating_widget = self

        self._background_modal = ModalView(
            background_color=[0, 0, 0, 0.8],
            background="",
            auto_dismiss=True
        )
        self._background_modal.bind(on_dismiss=self.dismiss)
        self._background_modal.open()
        Window.add_widget(self)

    def dismiss(self, *args):
        Window.unbind(on_resize=self.on_window_resize)
        app = MDApp.get_running_app()
        if hasattr(app, 'floating_widget') and app.floating_widget == self:
            app.floating_widget = None

        if self._background_modal:
            self._background_modal.unbind(on_dismiss=self.dismiss)
            self._background_modal.dismiss()
            self._background_modal = None

        if self.parent:
            self.parent.remove_widget(self)

    def populate_menu(self):
        container = self.ids.right_menu if self.layout_mode == 'desktop' else self.ids.bottom_menu
        container.clear_widgets()
        for item in self.menu_items:
            self.add_button_to_container(container, item)

    def add_button_to_container(self, container, item_data):
        button = MDIconButton(
            icon=item_data.get("icon", "circle"),
            icon_size="32sp",
            on_release=partial(self.on_item_press, item_data.get("callback"))
        )
        container.add_widget(button)

    def on_item_press(self, callback, instance):
        if isinstance(callback, str) and callback == 'add_to_playlist':
            method = getattr(self, callback, None)
            if method:
                Clock.schedule_once(lambda dt: method())
        else:
            self.dismiss()
            if callback:
                if isinstance(callback, str):
                     method = getattr(self, callback, None)
                     if method:
                         method()
                else:
                    callback()

    # --- Playlist Logic ---
    def add_to_playlist(self):
        """Opens a dialog to select a playlist to add the current song to."""
        if not self.track_path:
            log.warning("Add to playlist called, but no track_path was provided.")
            return

        if not self.playlist_manager:
            log.error("Playlist manager is not available to EnlargedAlbumArt.")
            return

        playlist_names = self.playlist_manager.playlist_names
        if not playlist_names:
            dialog = MDDialog(
                title="No Playlists Found",
                text="Create a playlist first to add songs to it.",
                buttons=[MDFlatButton(text="OK", on_release=lambda x: self.dismiss(x, dialog.dismiss()))],
            )
            dialog.open()
            return

        self._playlist_dialog = MDDialog(
            title="Add to Playlist",
            type="simple",
            items=[
                OneLineAvatarListItem(
                    text=name,
                    on_release=lambda x, playlist_name=name: self._add_to_selected_playlist(playlist_name)
                ) for name in playlist_names
            ],
        )
        self._playlist_dialog.bind(on_dismiss=self.dismiss)
        
        self._playlist_dialog.open()

    def _add_to_selected_playlist(self, playlist_name):
        """Callback to add the current track to the chosen playlist."""
        if self._playlist_dialog:
            self._playlist_dialog.dismiss()
            
        if self.playlist_manager and self.track_path:
            try:
                self.playlist_manager.add_track_to_playlist(playlist_name, self.track_path)
                log.info(f"Added '{self.track_path}' to playlist '{playlist_name}'.")
            except Exception as e:
                log.error(f"Failed to add track to playlist '{playlist_name}': {e}")
