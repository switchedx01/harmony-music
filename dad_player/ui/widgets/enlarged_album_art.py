# dad_player/ui/widgets/enlarged_album_art.py
import logging
import traceback
from kivy.properties import ObjectProperty, StringProperty, ListProperty
from kivy.uix.modalview import ModalView
from kivy.core.window import Window
from kivymd.app import MDApp
from kivymd.uix.card import MDCard
from kivymd.uix.button import MDIconButton, MDFlatButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import OneLineAvatarListItem
from functools import partial
from dad_player.constants import LAYOUT_BREAKPOINT
from kivy.metrics import dp
from kivy.clock import Clock

log = logging.getLogger(__name__)

class EnlargedAlbumArt(MDCard):
    art_texture = ObjectProperty(None)
    track_path = StringProperty(allownone=True)
    playlist_manager = ObjectProperty(None)
    layout_mode = StringProperty('mobile')
    
    menu_items = ListProperty([
        {"icon": "playlist-plus", "callback": "add_to_playlist", "requires_track": True},
        {"icon": "information-outline", "callback": "show_details", "requires_track": True}
    ])
    
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
        self.populate_menu()

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
        callback_info = item_data.get("callback")
        method_to_call = None

        if isinstance(callback_info, str):
            method_to_call = getattr(self, callback_info, None)
        elif callable(callback_info):
            method_to_call = callback_info

        button = MDIconButton(
            icon=item_data.get("icon", "circle"),
            icon_size="32sp",
            on_release=self.on_item_press
        )
        button.callback = method_to_call
        
        if item_data.get("requires_track", False) and not self.track_path:
            button.disabled = True
            
        container.add_widget(button)

    def on_item_press(self, button_instance):
        if not hasattr(button_instance, 'callback') or not callable(button_instance.callback):
            log.error(f"Button '{button_instance.icon}' was pressed but has no valid callback.")
            return

        callback_func = button_instance.callback
        log.debug(f"ACTION: Button '{button_instance.icon}' pressed, calling method '{callback_func.__name__}'.")
        
        if callback_func.__name__ == 'add_to_playlist':
            callback_func()
        else:
            self.dismiss()
            Clock.schedule_once(lambda dt: callback_func())
    
    def show_details(self):
        log.debug(f"Attempting to show details for track_path: '{self.track_path}'")
        if not self.track_path:
            log.warning("Show details aborted: track_path is missing.")
            return
        try:
            app = MDApp.get_running_app()
            log.debug("Calling DadPlayerApp.show_track_details...")
            app.show_track_details(self.track_path)
        except Exception as e:
            log.error(f"CRITICAL: Failed to open track details for '{self.track_path}': {e}")
            traceback.print_exc()

    def add_to_playlist(self):
        log.debug(f"Attempting to add to playlist for track_path: '{self.track_path}'")
        if not self.track_path:
            log.warning("Add to playlist aborted: track_path is missing.")
            return

        if not self.playlist_manager:
            log.error("Add to playlist aborted: PlaylistManager is not available.")
            return

        playlist_names = self.playlist_manager.playlist_names
        log.debug(f"Found playlists: {playlist_names}")
        if not playlist_names:
            dialog = MDDialog(
                title="No Playlists Found",
                text="Create a playlist first to add songs to it.",
                buttons=[MDFlatButton(text="OK", on_release=lambda x: dialog.dismiss())],
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
        self._playlist_dialog.open()

    def _add_to_selected_playlist(self, playlist_name):
        log.debug(f"Attempting to add track to playlist '{playlist_name}'.")
        if self._playlist_dialog:
            self._playlist_dialog.dismiss()
            
        if self.playlist_manager and self.track_path:
            try:
                log.debug(f"HANDOFF: EnlargedAlbumArt -> PlaylistManager.add_track_to_playlist('{playlist_name}').")
                self.playlist_manager.add_track_to_playlist(playlist_name, self.track_path)
                log.info(f"Successfully added '{self.track_path}' to playlist '{playlist_name}'.")
            except Exception as e:
                log.error(f"Failed to add track to playlist '{playlist_name}': {e}")
