# main_dad_player.py

import os
import sys
from logging_config import setup_logging

# --- Logging Setup ---
# Configure logging BEFORE any Kivy modules are imported to avoid conflicts.
setup_logging()

# --- PyInstaller Path Helper ---
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores its path in _MEIPASS.
        base_path = sys._MEIPASS
    except Exception:
        # If not running in a PyInstaller bundle, use the normal path.
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# --- Environment and Path Setup ---

# Set Kivy GL backend. This must be done before importing Kivy.
os.environ['KIVY_GL_BACKEND'] = 'angle_sdl2'

# Add the project root to the Python path for module imports.
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Add the bundled resources path for Kivy to find assets like fonts and images.
from kivy.resources import resource_add_path
if hasattr(sys, '_MEIPASS'):
    resource_add_path(os.path.join(sys._MEIPASS))

# --- Application Mode Functions ---
def run_gui_app():
    """Initializes and runs the main Kivy application."""
    # Import the app class after all paths and configurations are set.
    from dad_player.app import DadPlayerApp
    DadPlayerApp().run()

# --- Main Entry Point ---
def main():
    """Main function to start the application."""
    # Logging is now handled at the start of the script.
    run_gui_app()

if __name__ == "__main__":
    main()
