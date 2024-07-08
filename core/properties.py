import bpy
from ..functions.translations import t, get_languages_list, update_language
from ..core.addon_preferences import get_preference

def register():
    default_language = get_preference("language", 0)
    
    bpy.types.Scene.avatar_toolkit_language = bpy.props.EnumProperty(
        name=t("Settings.language.label", "Language"),
        description=t("Settings.language.desc", "Select the language for the addon"),
        items=get_languages_list,
        default=default_language,
        update=update_language
    )

def unregister():
    if hasattr(bpy.types.Scene, "avatar_toolkit_language"):
        del bpy.types.Scene.avatar_toolkit_language