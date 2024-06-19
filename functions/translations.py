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

    language: str = bpy.context.preferences.view.language

    for i in os.listdir(translations_dir):
        languages.append(i.split(".")[0])

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
    choices: List[Tuple[str, str, str]] = []
    for language in languages:
        choices.append((language, language, language))
    return choices

def update_ui(self, context) -> None:
    load_translations()
    bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

load_translations()
