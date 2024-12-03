import bpy
from typing import List, Tuple, Optional
from bpy.types import PropertyGroup, Material, Scene, Object, Context
from bpy.props import (
    StringProperty, 
    BoolProperty, 
    EnumProperty, 
    IntProperty, 
    FloatProperty, 
    CollectionProperty,
    PointerProperty
)
from .translations import t, get_languages_list, update_language
from .addon_preferences import get_preference
from .updater import get_version_list
from .common import get_armature_list

class AvatarToolkitSceneProperties(PropertyGroup):
    """Property group containing Avatar Toolkit scene-level settings and properties"""
    
    avatar_toolkit_updater_version_list: EnumProperty(
        items=get_version_list,
        name=t("Scene.avatar_toolkit_updater_version_list.name"),
        description=t("Scene.avatar_toolkit_updater_version_list.description")
    )

    active_armature: EnumProperty(
        items=get_armature_list,
        name=t("QuickAccess.select_armature"),
        description=t("QuickAccess.select_armature")
    )

def register() -> None:
    """Register the Avatar Toolkit property group"""
    bpy.types.Scene.avatar_toolkit = PointerProperty(type=AvatarToolkitSceneProperties)

def unregister() -> None:
    """Unregister the Avatar Toolkit property group"""
    del bpy.types.Scene.avatar_toolkit
