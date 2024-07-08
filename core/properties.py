import bpy
from ..functions.translations import t, get_languages_list, update_language
from ..core.addon_preferences import get_preference

def register() -> None:
    default_language = get_preference("language", 0)
    
    bpy.types.Scene.avatar_toolkit_language = bpy.props.EnumProperty(
        name=t("Settings.language.label", "Language"),
        description=t("Settings.language.desc", "Select the language for the addon"),
        items=get_languages_list,
        default=default_language,
        update=update_language
    )

    bpy.types.Scene.mouth_a = bpy.props.StringProperty(
        name=t("Scene.mouth_a.label"),
        description=t("Scene.mouth_a.desc")
    )
    bpy.types.Scene.mouth_o = bpy.props.StringProperty(
        name=t("Scene.mouth_o.label"),
        description=t("Scene.mouth_o.desc")
    )
    bpy.types.Scene.mouth_ch = bpy.props.StringProperty(
        name=t("Scene.mouth_ch.label"),
        description=t("Scene.mouth_ch.desc")
    )
    bpy.types.Scene.shape_intensity = bpy.props.FloatProperty(
        name=t("Scene.shape_intensity.label"),
        description=t("Scene.shape_intensity.desc"),
        default=1.0,
        min=0.0,
        max=2.0
    )

def unregister() -> None:
    del bpy.types.Scene.avatar_toolkit_language
    del bpy.types.Scene.mouth_a
    del bpy.types.Scene.mouth_o
    del bpy.types.Scene.mouth_ch
    del bpy.types.Scene.shape_intensity
