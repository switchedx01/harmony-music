# dad_player/ui/screens/track_details_view.py

import logging
import os
from kivy.properties import DictProperty, StringProperty, ObjectProperty
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from dad_player.utils.formatting import format_duration
from kivymd.uix.filemanager import MDFileManager
from kivymd.toast import toast

log = logging.getLogger(__name__)

class TrackDetailsView(MDScreen):
    track_path = StringProperty("")
    track_details = DictProperty({})
    previous_screen = StringProperty("")
    album_art_path = StringProperty("")

    _editable_fields = [
        'title_field', 'artist_field', 'album_field', 'album_artist_field',
        'composer_field', 'genre_field', 'year_field', 'track_number_field',
        'disc_number_field'
    ]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._new_album_art_path = None
        self.file_manager = MDFileManager(
            exit_manager=self.close_file_manager,
            select_path=self.select_art_path,
            ext=['.png', '.jpg', '.jpeg']
        )

    def on_track_details(self, instance, details):
        self.populate_details(details)

    def populate_details(self, details):
        if not details:
            return

        app = MDApp.get_running_app()
        art_path = app.library_manager.get_album_art_path_for_file(details.get('filepath', ''))
        self.album_art_path = art_path if art_path is not None else ""
        
        self.ids.title_field.text = details.get('title') or ''
        self.ids.artist_field.text = details.get('artist') or ''
        self.ids.album_field.text = details.get('album') or ''
        self.ids.album_artist_field.text = details.get('album_artist') or ''
        self.ids.composer_field.text = details.get('composer') or ''
        self.ids.genre_field.text = details.get('genre') or ''
        self.ids.filepath_field.text = details.get('filepath') or ''

        self.ids.year_field.text = str(details.get('year') or '')
        self.ids.track_number_field.text = str(details.get('track_number') or '')
        self.ids.disc_number_field.text = str(details.get('disc_number') or '')
        
        duration = details.get('duration')
        self.ids.duration_field.text = format_duration(duration) if duration else '0:00'

    def change_album_art(self):
        self.file_manager.show(os.path.expanduser("~"))

    def select_art_path(self, path):
        self._new_album_art_path = path
        self.ids.album_art_image.source = path
        self.close_file_manager()
        toast(f"Selected new art: {os.path.basename(path)}")

    def close_file_manager(self, *args):
        self.file_manager.close()

    def set_mode(self, mode):
        is_edit_mode = (mode == 'edit')
        
        for field_id in self._editable_fields:
            field = self.ids.get(field_id)
            if field:
                field.disabled = not is_edit_mode
        
        self.ids.edit_art_button.opacity = 1 if is_edit_mode else 0
        self.ids.edit_art_button.disabled = not is_edit_mode

        app_bar = self.ids.top_bar
        if is_edit_mode:
            app_bar.right_action_items = [
                ["check", lambda x: self.save_changes()],
                ["close", lambda x: self.cancel_edit()]
            ]
        else:
            app_bar.right_action_items = [["pencil", lambda x: self.set_mode('edit')]]

    def save_changes(self):
        new_data = {
            'title': self.ids.title_field.text,
            'artist': self.ids.artist_field.text,
            'album': self.ids.album_field.text,
            'album_artist': self.ids.album_artist_field.text,
            'composer': self.ids.composer_field.text,
            'genre': self.ids.genre_field.text,
            'year': self.ids.year_field.text,
            'track_number': self.ids.track_number_field.text,
            'disc_number': self.ids.disc_number_field.text,
        }
        if self._new_album_art_path:
            new_data['album_art_path'] = self._new_album_art_path

        MDApp.get_running_app().save_track_details(self.track_path, new_data)
        self._new_album_art_path = None
        self.set_mode('view')

    def cancel_edit(self):
        if self._new_album_art_path:
            self.ids.album_art_image.source = self.album_art_path
            self._new_album_art_path = None
            
        self.populate_details(self.track_details)
        self.set_mode('view')

    def close_view(self):
        app = MDApp.get_running_app()
        app.switch_screen(self.previous_screen)
