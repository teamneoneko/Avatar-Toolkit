import bpy
import os
import tomllib
import json
from bpy.types import AddonPreferences
from typing import Any, Dict

# Get the directory of the current file
PREFERENCES_DIR = os.path.dirname(os.path.abspath(__file__))
PREFERENCES_FILE = os.path.join(PREFERENCES_DIR, "preferences.json")

def get_current_version():
    main_dir = os.path.dirname(os.path.dirname(__file__))
    manifest_path = os.path.join(main_dir, "blender_manifest.toml")
    with open(manifest_path, 'r') as f:
        manifest_data = toml.load(f)
    return manifest_data.get('version', 'Unknown')

def save_preference(key: str, value: Any) -> None:
    """Save a single preference to the JSON file."""
    prefs = load_preferences()
    prefs[key] = value
    with open(PREFERENCES_FILE, 'w') as f:
        json.dump(prefs, f, indent=4)

def load_preferences() -> Dict[str, Any]:
    """Load all preferences from the JSON file."""
    if os.path.exists(PREFERENCES_FILE):
        with open(PREFERENCES_FILE, 'r') as f:
            return json.load(f)
    return {}

def get_preference(key: str, default: Any = None) -> Any:
    """Get a single preference from the JSON file."""
    prefs = load_preferences()
    return prefs.get(key, default)

class AvatarToolkitPreferences(AddonPreferences):
    bl_idname = __package__.rsplit('.', 1)[0]

    def draw(self, context):
        layout = self.layout
        layout.label(text="Preferences are managed internally.")
        # You can add more UI elements here if needed

def get_addon_preferences(context):
    return context.preferences.addons[AvatarToolkitPreferences.bl_idname].preferences

# Initialize preferences if the file doesn't exist
if not os.path.exists(PREFERENCES_FILE):
    save_preference("language", 0)  # Set default language to 0 (auto)