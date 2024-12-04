import os
import json
import bpy
import logging
from bpy.app.translations import locale
from typing import Dict, List, Tuple, Optional, Any
from ..core.logging_setup import logger
from .addon_preferences import save_preference, get_preference

# Set up logging
logger = logging.getLogger(__name__)

# Use __file__ to get the current file's directory
current_dir = os.path.dirname(os.path.abspath(__file__))
main_dir = os.path.dirname(current_dir)
resources_dir = os.path.join(main_dir, "resources")
translations_dir = os.path.join(resources_dir, "translations")

dictionary: Dict[str, str] = dict()
languages: List[str] = []
_translation_cache: Dict[str, Dict[str, str]] = {}
verbose: bool = True

def get_fallback_language() -> str:
    """Return the default fallback language"""
    return "en_US"

def load_translations() -> bool:
    """Load translations for the selected language"""
    global dictionary, languages

    old_dictionary = dictionary.copy()

    dictionary = dict()
    languages = ["auto"]

    # Populate languages list
    for i in os.listdir(translations_dir):
        lang = i.split(".")[0]
        if lang != "auto":
            languages.append(lang)

    language_index: int = get_preference("language", 0)
    logger.debug(f"Loading translations for language index: {language_index}")

    if language_index == 0:  # "auto"
        language: str = bpy.context.preferences.view.language
    else:
        try:
            language = languages[language_index]
        except IndexError:
            language = bpy.context.preferences.view.language

    logger.debug(f"Selected language: {language}")

    # Check cache first
    if language in _translation_cache:
        dictionary = _translation_cache[language]
        return dictionary != old_dictionary

    translation_file: str = os.path.join(translations_dir, language + ".json")
    if os.path.exists(translation_file):
        dictionary = _load_translation_file(translation_file)
    else:
        custom_language: str = language.split("_")[0]
        custom_translation_file: str = os.path.join(translations_dir, custom_language + ".json")
        if os.path.exists(custom_translation_file):
            dictionary = _load_translation_file(custom_translation_file)
        else:
            logger.warning(f"Translation file not found for language: {language}")
            default_file: str = os.path.join(translations_dir, get_fallback_language() + ".json")
            if os.path.exists(default_file):
                dictionary = _load_translation_file(default_file)
            else:
                logger.error("Default translation file not found")

    _translation_cache[language] = dictionary
    return dictionary != old_dictionary

def _load_translation_file(file_path: str) -> Dict[str, str]:
    """Load and parse a translation file"""
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)["messages"]

def t(phrase: str, default: Optional[str] = None, **kwargs) -> str:
    """Get translation for a phrase with optional formatting"""
    output: Optional[str] = dictionary.get(phrase)
    if output is None:
        if verbose:
            logger.warning(f'Unknown phrase: {phrase}')
        return default if default is not None else phrase
    return output.format(**kwargs) if kwargs else output

def get_language_display_name(lang: str) -> str:
    """Get the display name for a language code"""
    return t(f"Language.{lang}", lang)

def get_languages_list(self: Any, context: Any) -> List[Tuple[str, str, str]]:
    """Get list of available languages for UI"""
    return [(str(i), get_language_display_name(lang), f"Use {lang} language") 
            for i, lang in enumerate(languages)]

def update_language(self: Any, context: Any) -> None:
    """Handle language update and UI refresh"""
    logger.info(f"Updating language to: {self.language}")
    save_preference("language", int(self.language))
    load_translations()
    context.scene.avatar_toolkit.language_changed = True
    bpy.ops.avatar_toolkit.translation_restart_popup('INVOKE_DEFAULT')

# Initial load of translations
load_translations()
