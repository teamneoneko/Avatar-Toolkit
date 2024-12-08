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
from .logging_setup import logger
from .translations import t, get_languages_list, update_language
from .addon_preferences import get_preference, save_preference
from .updater import get_version_list
from .common import get_armature_list, get_active_armature, get_all_meshes

def update_validation_mode(self, context):
    logger.info(f"Updating validation mode to: {self.validation_mode}")
    save_preference("validation_mode", self.validation_mode)

def update_logging_state(self, context):
    logger.info(f"Updating logging state to: {self.enable_logging}")
    save_preference("enable_logging", self.enable_logging)
    from .logging_setup import configure_logging
    configure_logging(self.enable_logging)

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
        description=t("QuickAccess.select_armature"),
    )

    language: EnumProperty(
        name=t("Settings.language"),
        description=t("Settings.language_desc"),
        items=get_languages_list,
        update=update_language
    )

    validation_mode: EnumProperty(
        name=t("Settings.validation_mode"),
        description=t("Settings.validation_mode_desc"),
        items=[
            ('STRICT', t("Settings.validation_mode.strict"), t("Settings.validation_mode.strict_desc")),
            ('BASIC', t("Settings.validation_mode.basic"), t("Settings.validation_mode.basic_desc")),
            ('NONE', t("Settings.validation_mode.none"), t("Settings.validation_mode.none_desc"))
        ],
        default=get_preference("validation_mode", "STRICT"),
        update=update_validation_mode
    )

    enable_logging: BoolProperty(
        name=t("Settings.enable_logging"),
        description=t("Settings.enable_logging_desc"),
        default=False,
        update=update_logging_state
    )

    debug_expand: BoolProperty(
        name="Debug Settings Expanded",
        default=False
    )

    remove_doubles_merge_distance: FloatProperty(
        name=t("Optimization.merge_distance"),
        description=t("Optimization.merge_distance_desc"),
        default=0.0001,
        min=0.00001,
        max=0.1
    )
    
    remove_doubles_advanced: BoolProperty(
        name=t("Optimization.remove_doubles_advanced"),
        description=t("Optimization.remove_doubles_advanced_desc"),
        default=False
    )

    merge_twist_bones: BoolProperty(
        name=t("Tools.merge_twist_bones"),
        description=t("Tools.merge_twist_bones_desc"),
        default=True
    )

    clean_weights_threshold: FloatProperty(
        name=t("Tools.clean_weights_threshold"),
        description=t("Tools.clean_weights_threshold_desc"),
        default=0.01,
        min=0.0000001,
        max=0.9999999
    )

    connect_bones_min_distance: FloatProperty(
        name=t("Tools.connect_bones_min_distance"),
        description=t("Tools.connect_bones_min_distance_desc"),
        default=0.005,
        min=0.001,
        max=0.1
    )

    merge_weights_threshold: FloatProperty(
        name=t("Tools.merge_weights_threshold"),
        description=t("Tools.merge_weights_threshold_desc"),
        default=0.01,
        min=0.0001,
        max=1.0
    )

    mmd_process_twist_bones: BoolProperty(
        name=t("MMD.process_twist_bones"),
        description=t("MMD.process_twist_bones_desc"),
        default=True
    )
    
    mmd_connect_bones: BoolProperty(
        name=t("MMD.connect_bones"),
        description=t("MMD.connect_bones_desc"),
        default=True
    )

    save_backup_state: BoolProperty(
        name="Save Backup State",
        description="Save the initial state of the armature before standardizing bones",
        default=False
    )

def register() -> None:
    """Register the Avatar Toolkit property group"""
    logger.info("Registering Avatar Toolkit properties")
    bpy.types.Scene.avatar_toolkit = PointerProperty(type=AvatarToolkitSceneProperties)
    logger.debug("Properties registered successfully")

def unregister() -> None:
    """Unregister the Avatar Toolkit property group"""
    logger.info("Unregistering Avatar Toolkit properties")
    del bpy.types.Scene.avatar_toolkit
    logger.debug("Properties unregistered successfully")
