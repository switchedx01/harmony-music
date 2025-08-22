# dad_player/ui/popups/manage_folders_popup.py

import logging
import os
from kivy.properties import ObjectProperty, ListProperty, StringProperty
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton
from kivy.uix.modalview import ModalView

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

class FolderChooserPopup(ModalView):
    settings_manager = ObjectProperty(None)
    parent_popup = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _on_select_folder(self):
        """Called when the 'Select This Folder' button is pressed."""
        selection = self.ids.folder_chooser_fc.selection
        if selection:
            selected_path = selection[0]
            log.info(f"Folder selected: {selected_path}")
            self.settings_manager.add_music_folder(selected_path)
            if self.parent_popup:
                self.parent_popup.load_music_folders()
            self.dismiss()
        else:
            log.warning("No folder selected.")


class ManageFoldersPopup(ModalView):
    settings_manager = ObjectProperty(None)
    library_manager = ObjectProperty(None)
    status_message = StringProperty("")

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
        """Opens the popup to select a new music folder."""
        log.info("Opening folder chooser popup.")
        popup = FolderChooserPopup(
            settings_manager=self.settings_manager,
            parent_popup=self
        )
        popup.open()
