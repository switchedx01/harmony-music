# main_dad_player.py

import os
import sys
from logging_config import setup_logging

# --- Logging Setup ---
setup_logging()

# --- PyInstaller Path Helper ---
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# --- Environment and Path Setup ---

os.environ['KIVY_GL_BACKEND'] = 'angle_sdl2'

project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from kivy.resources import resource_add_path
if hasattr(sys, '_MEIPASS'):
    resource_add_path(os.path.join(sys._MEIPASS))

# --- Application Mode Functions ---
def run_gui_app():
    """Initializes and runs the main Kivy application."""
    from dad_player.app import DadPlayerApp
    DadPlayerApp().run()

# --- Main Entry Point ---
def main():
    """Main function to start the application."""
    run_gui_app()

if __name__ == "__main__":
    main()
