# dad_player/ui/popups/manage_folders_popup.py

import logging
import os
import platform
from string import ascii_uppercase
from kivy.metrics import dp
from kivy.properties import ObjectProperty, ListProperty, StringProperty
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton
from kivy.uix.modalview import ModalView
from kivymd.uix.filemanager import MDFileManager

log = logging.getLogger(__name__)


class FolderListItem(RecycleDataViewBehavior, MDBoxLayout):
    path = StringProperty("")
    root_popup = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def refresh_view_attrs(self, rv, index, data):
        """ Catch and handle the view changes."""
        self.path = data['path']
        self.root_popup = data['root_popup']
        return super().refresh_view_attrs(rv, index, data)


class CustomFileManager(MDFileManager):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.is_windows = platform.system() == 'Windows'
        self.virtual_root = 'Computer' if self.is_windows else '/'

    def show(self, path):
        super().show(path)
        self.ids.toolbar.right_action_items = [["check", lambda x: self.select_path(self.current_path)]]

    def close(self):
        if hasattr(self.ids.toolbar, 'right_action_items'):
            self.ids.toolbar.right_action_items = []
        super().close()

    def _update_files(self, *args):
        try:
            if self.current_path == self.virtual_root and self.is_windows:
                drives = sorted([f"{d}:{os.sep}" for d in ascii_uppercase if os.path.exists(f"{d}:{os.sep}")])
                self.ids.rv.data = []
                for drive in drives:
                    self.ids.rv.data.append({
                        'viewclass': 'MDFileManagerItem',
                        'path': drive,
                        '_root': self,
                        'sep': os.sep,
                        'isdir': True,
                        'icon': 'harddisk',
                        'name': drive,
                        'height': dp(48),
                        'events_callback': self.select_dir_or_file,
                    })
            else:
                super()._update_files(*args)
                self.ids.rv.data = [d for d in self.ids.rv.data if d['isdir']]
        except Exception as e:
            log.error(f"Error updating files: {e}")

    def back(self):
        parent = os.path.dirname(self.current_path.rstrip(os.sep))
        if self.current_path == self.virtual_root:
            self.exit_manager(1)
            return
        elif self.is_windows and parent == '' and self.current_path.endswith(':/'):
            self.show(self.virtual_root)
            return
        self.show(parent if parent else '/')

    def select_dir_or_file(self, path, *args):
        """
        Handles the selection of a directory. Accepts extra arguments
        to prevent crashes from unexpected event callback signatures.
        """
        if os.path.isdir(path):
            self.show(path)
        else:
            self.select_path(path)


class ManageFoldersPopup(ModalView):
    settings_manager = ObjectProperty(None)
    library_manager = ObjectProperty(None)
    status_message = StringProperty("")
    folder_chooser = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_open(self):
        self.load_music_folders()

    def load_music_folders(self):
        folders = self.settings_manager.get_music_folders()
        if self.ids and 'folders_rv' in self.ids:
            self.ids.folders_rv.data = [{'path': f, 'root_popup': self} for f in folders]

    def remove_folder_from_list_item(self, path):
        """Called from the on_release of the button in the kv file."""
        self.settings_manager.remove_music_folder(path)
        self.load_music_folders()

    def open_folder_chooser(self):
        """Opens the file manager to select a new music folder."""
        log.info("Opening folder chooser.")
        try:
            self.folder_chooser = CustomFileManager(
                exit_manager=self.close_folder_chooser,
                select_path=self.on_folder_selected,
            )
            self.folder_chooser.show('C:/' if self.folder_chooser.is_windows else '/')
        except Exception as e:
            log.error(f"Error opening folder chooser: {e}")

    def close_folder_chooser(self, *args):
        self.folder_chooser.close()

    def on_folder_selected(self, path):
        if path == self.folder_chooser.virtual_root:
            log.warning("Cannot select virtual root; please choose a folder inside a drive.")
            return
        if not os.path.isdir(path):
            log.warning("Selected a file, not a folder; ignoring.")
            return
        try:
            log.info(f"Folder selected: {path}")
            self.settings_manager.add_music_folder(path)
            self.load_music_folders()
        except Exception as e:
            log.error(f"Error adding music folder {path}: {e}")
            self.status_message = "Error adding folder: possibly unsupported files or other issue."
        finally:
            self.close_folder_chooser()
