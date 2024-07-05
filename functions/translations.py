import os
import json
import bpy
from bpy.app.translations import locale
from ..core.register import register_wrap
from typing import Dict, List, Tuple

main_dir: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
resources_dir: str = os.path.join(main_dir, "resources")
translations_dir: str = os.path.join(resources_dir, "translations")

dictionary: Dict[str, str] = dict()
languages: List[str] = []
verbose: bool = True

def load_translations() -> None:
    global dictionary, languages

    dictionary = dict()
    languages = ["auto"]

    # Populate languages list
    for i in os.listdir(translations_dir):
        lang = i.split(".")[0]
        if lang != "auto":
            languages.append(lang)

    # Check if the context and scene are available
    if hasattr(bpy.context, "scene"):
        # Check if the property exists before trying to access it
        if hasattr(bpy.context.scene, "avatar_toolkit_language"):
            language_index = bpy.context.scene.avatar_toolkit_language
            if isinstance(language_index, str):
                language_index = int(language_index)
            if language_index == 0:  # "auto"
                language = bpy.context.preferences.view.language
            else:
                language = languages[language_index]
        else:
            language = bpy.context.preferences.view.language
    else:
        # Set a default language if the context or scene is not available
        language = "en_US"

    translation_file: str = os.path.join(translations_dir, language + ".json")
    if os.path.exists(translation_file):
        with open(translation_file, 'r', encoding='utf-8') as file:
            dictionary = json.load(file)["messages"]
    else:
        custom_language: str = language.split("_")[0]
        custom_translation_file: str = os.path.join(translations_dir, custom_language + ".json")
        if os.path.exists(custom_translation_file):
            with open(custom_translation_file, 'r', encoding='utf-8') as file:
                dictionary = json.load(file)["messages"]
        else:
            print(f"Translation file not found for language: {language}")
            default_file: str = os.path.join(translations_dir, "en_US.json")
            if os.path.exists(default_file):
                with open(default_file, 'r', encoding='utf-8') as file:
                    dictionary = json.load(file)["messages"]
            else:
                print("Default translation file 'en_US.json' not found.")

def t(phrase: str, *args, **kwargs) -> str:
    output: str = dictionary.get(phrase)
    if output is None:
        if verbose:
            print('Warning: Unknown phrase: ' + phrase)
        return phrase
    return output.format(*args, **kwargs)

def get_languages_list(self, context) -> List[Tuple[str, str, str]]:
    return [(str(i), lang, f"Use {lang} language") for i, lang in enumerate(languages)]

def refresh_translations():
    load_translations()
    # Force a full UI update
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            area.tag_redraw()

def update_ui(self, context):
    refresh_translations()
    # Force Blender to redraw all UI elements
    for screen in bpy.data.screens:
        for area in screen.areas:
            area.tag_redraw()
    # Update the Scene to trigger a full UI refresh
    bpy.context.scene.update_tag()

# Initial load of translations
load_translations()
