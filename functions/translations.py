import os
import json
import bpy
from bpy.app.translations import locale
from typing import Dict, List, Tuple
from ..core.addon_preferences import save_preference, get_preference

# Use __file__ to get the current file's directory
current_dir = os.path.dirname(os.path.abspath(__file__))
main_dir = os.path.dirname(current_dir)
resources_dir = os.path.join(main_dir, "resources")
translations_dir = os.path.join(resources_dir, "translations")

dictionary: Dict[str, str] = dict()
languages: List[str] = []
verbose: bool = True

def load_translations() -> bool:
    global dictionary, languages

    old_dictionary = dictionary.copy()

    dictionary = dict()
    languages = ["auto"]

    # Populate languages list
    for i in os.listdir(translations_dir):
        lang = i.split(".")[0]
        if lang != "auto":
            languages.append(lang)

    language_index = get_preference("language", 0)
    print(f"Loading translations for language index: {language_index}")  # Debug print

    if language_index == 0:  # "auto"
        language = bpy.context.preferences.view.language
    else:
        try:
            language = languages[language_index]
        except IndexError:
            language = bpy.context.preferences.view.language

    print(f"Selected language: {language}")  # Debug print

    translation_file: str = os.path.join(translations_dir, language + ".json")
    if os.path.exists(translation_file):
        with open(translation_file, 'r', encoding='utf-8') as file:
            dictionary = json.load(file)["messages"]
        print(f"Loaded translations: {dictionary}")  # Debug print
    else:
        custom_language: str = language.split("_")[0]
        custom_translation_file: str = os.path.join(translations_dir, custom_language + ".json")
        if os.path.exists(custom_translation_file):
            with open(custom_translation_file, 'r', encoding='utf-8') as file:
                dictionary = json.load(file)["messages"]
            print(f"Loaded custom translations: {dictionary}")  # Debug print
        else:
            print(f"Translation file not found for language: {language}")
            default_file: str = os.path.join(translations_dir, "en_US.json")
            if os.path.exists(default_file):
                with open(default_file, 'r', encoding='utf-8') as file:
                    dictionary = json.load(file)["messages"]
                print(f"Loaded default translations: {dictionary}")  # Debug print
            else:
                print("Default translation file 'en_US.json' not found.")
    return dictionary != old_dictionary

def t(phrase: str, default: str = None) -> str:
    output: str = dictionary.get(phrase)
    if output is None:
        if verbose:
            print(f'Warning: Unknown phrase: {phrase}')
        return default if default is not None else phrase
    print(f"Translating '{phrase}' to '{output}'")  # Debug print
    return output

def get_language_display_name(lang: str) -> str:
    if lang == "auto":
        return t("Language.auto", "Automatic")
    return t(f"Language.{lang}", lang)

def get_languages_list(self, context) -> List[Tuple[str, str, str]]:
    return [(str(i), get_language_display_name(lang), f"Use {lang} language") for i, lang in enumerate(languages)]

def update_language(self, context):
    print(f"Updating language to: {self.avatar_toolkit_language}")  # Debug print
    save_preference("language", int(self.avatar_toolkit_language))
    load_translations()
    # Set a flag to indicate that a language change has occurred
    context.scene.avatar_toolkit_language_changed = True
    # Show popup after language change
    bpy.ops.avatar_toolkit.translation_restart_popup('INVOKE_DEFAULT')

# Initial load of translations
print("Performing initial load of translations")  # Debug print
load_translations()
