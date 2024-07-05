import bpy
from ..functions.translations import t, get_languages_list, update_ui
from ..core.register import register_property
from typing import Tuple

def register():
    register_property((bpy.types.Scene, "avatar_toolkit_language", bpy.props.EnumProperty(
        name=t("Settings.language.label"),
        description=t("Settings.language.desc"),
        items=get_languages_list,
        default=0,
        update=update_ui
    )))

def unregister():
    pass
