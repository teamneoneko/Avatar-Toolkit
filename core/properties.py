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
from ..functions.visemes import VisemePreview
from ..functions.eye_tracking import set_rotation

def update_validation_mode(self, context):
    logger.info(f"Updating validation mode to: {self.validation_mode}")
    save_preference("validation_mode", self.validation_mode)

def update_logging_state(self, context):
    logger.info(f"Updating logging state to: {self.enable_logging}")
    save_preference("enable_logging", self.enable_logging)
    from .logging_setup import configure_logging
    configure_logging(self.enable_logging)

def update_shape_intensity(self, context):
    if self.viseme_preview_mode:
        from ..functions.visemes import VisemePreview
        VisemePreview.update_preview(context)

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
        name=t("MMD.merge_twist_bones"),
        description=t("MMD.merge_twist_bones_desc"),
        default=True
    )

    keep_twist_bones: BoolProperty(
        name=t("MMD.keep_twist_bones"),
        description=t("MMD.keep_twist_bones_desc"),
        default=False
    )

    keep_upper_chest: BoolProperty(
        name=t("MMD.keep_upper_chest"),
        description=t("MMD.keep_upper_chest_desc"),
        default=True
    )

    merge_weights_threshold: FloatProperty(
        name=t("MMD.merge_weights_threshold"),
        description=t("MMD.merge_weights_threshold_desc"),
        default=0.01,
        min=0.0,
        max=1.0
    )

    viseme_preview_mode: BoolProperty(
        name=t("Visemes.preview_mode"),
        description=t("Visemes.preview_mode_desc"),
        default=False
    )
    
    viseme_preview_selection: StringProperty(
        name=t("Visemes.preview_selection"),
        description=t("Visemes.preview_selection_desc"),
        default="vrc.v_aa"
    )
    
    mouth_a: StringProperty(
        name=t("Visemes.mouth_a"),
        description=t("Visemes.mouth_a_desc")
    )
    
    mouth_o: StringProperty(
        name=t("Visemes.mouth_o"), 
        description=t("Visemes.mouth_o_desc")
    )
    
    mouth_ch: StringProperty(
        name=t("Visemes.mouth_ch"),
        description=t("Visemes.mouth_ch_desc")
    )

    shape_intensity: FloatProperty(
        name=t("Visemes.shape_intensity"),
        description=t("Visemes.shape_intensity_desc"),
        default=1.0,
        min=0.0,
        max=2.0,
        precision=3,
        update=update_shape_intensity
    )

    viseme_preview_selection: EnumProperty(
    name=t("Visemes.preview_selection"),
    description=t("Visemes.preview_selection_desc"),
    items=[
        ('vrc.v_aa', 'AA', 'A as in "bat"'),
        ('vrc.v_ch', 'CH', 'Ch as in "choose"'),
        ('vrc.v_dd', 'DD', 'D as in "dog"'),
        ('vrc.v_ih', 'IH', 'I as in "bit"'),
        ('vrc.v_ff', 'FF', 'F as in "fox"'),
        ('vrc.v_e', 'E', 'E as in "bet"'),
        ('vrc.v_kk', 'KK', 'K as in "cat"'),
        ('vrc.v_nn', 'NN', 'N as in "net"'),
        ('vrc.v_oh', 'OH', 'O as in "hot"'),
        ('vrc.v_ou', 'OU', 'O as in "go"'),
        ('vrc.v_pp', 'PP', 'P as in "pat"'),
        ('vrc.v_rr', 'RR', 'R as in "red"'),
        ('vrc.v_sil', 'SIL', 'Silence'),
        ('vrc.v_ss', 'SS', 'S as in "sit"'),
        ('vrc.v_th', 'TH', 'Th as in "think"')
    ],
    update=lambda s, c: VisemePreview.update_preview(c)
    
)
    
    eye_tracking_type: EnumProperty(
    name=t("EyeTracking.type"),
    description=t("EyeTracking.type_desc"),
    items=[
        ('AV3', t("EyeTracking.type.av3"), t("EyeTracking.type.av3_desc")),
        ('SDK2', t("EyeTracking.type.sdk2"), t("EyeTracking.type.sdk2_desc"))
    ],
    default='AV3'
)

    eye_mode: EnumProperty(
        name=t("EyeTracking.mode"),
        items=[
            ('CREATION', t("EyeTracking.mode.creation"), ""),
            ('TESTING', t("EyeTracking.mode.testing"), "")
        ],
        default='CREATION'
    )

    eye_rotation_x: FloatProperty(
        name=t("EyeTracking.rotation.x"),
        update=set_rotation
    )

    eye_rotation_y: FloatProperty(
        name=t("EyeTracking.rotation.y"), 
        update=set_rotation
    )

    mesh_name_eye: StringProperty(
        name=t("EyeTracking.mesh_name"),
        description=t("EyeTracking.mesh_name_desc")
    )

    head: StringProperty(
        name=t("EyeTracking.head_bone"),
        description=t("EyeTracking.head_bone_desc")
    )

    eye_left: StringProperty(
        name=t("EyeTracking.eye_left"),
        description=t("EyeTracking.eye_left_desc")
    )

    eye_right: StringProperty(
        name=t("EyeTracking.eye_right"), 
        description=t("EyeTracking.eye_right_desc")
    )

    disable_eye_movement: BoolProperty(
        name=t("EyeTracking.disable_movement"),
        description=t("EyeTracking.disable_movement_desc"),
        default=False
    )

    disable_eye_blinking: BoolProperty(
        name=t("EyeTracking.disable_blinking"),
        description=t("EyeTracking.disable_blinking_desc"),
        default=False
    )

    eye_distance: FloatProperty(
        name=t("EyeTracking.distance"),
        description=t("EyeTracking.distance_desc"),
        default=0.0,
        min=-1.0,
        max=1.0
    )

    iris_height: FloatProperty(
        name=t("EyeTracking.iris_height"),
        description=t("EyeTracking.iris_height_desc"),
        default=0.0,
        min=-1.0,
        max=1.0
    )

    eye_blink_shape: FloatProperty(
        name=t("EyeTracking.blink_shape"),
        description=t("EyeTracking.blink_shape_desc"),
        default=1.0,
        min=0.0,
        max=1.0
    )

    eye_lowerlid_shape: FloatProperty(
        name=t("EyeTracking.lowerlid_shape"),
        description=t("EyeTracking.lowerlid_shape_desc"),
        default=1.0,
        min=0.0,
        max=1.0
    )

    wink_left: StringProperty(
        name=t("EyeTracking.wink_left"),
        description=t("EyeTracking.wink_left_desc")
    )

    wink_right: StringProperty(
        name=t("EyeTracking.wink_right"),
        description=t("EyeTracking.wink_right_desc")
    )

    lowerlid_left: StringProperty(
        name=t("EyeTracking.lowerlid_left"),
        description=t("EyeTracking.lowerlid_left_desc")
    )

    lowerlid_right: StringProperty(
        name=t("EyeTracking.lowerlid_right"),
        description=t("EyeTracking.lowerlid_right_desc")
    )

    merge_mode: EnumProperty(
        name=t('CustomPanel.merge_mode'),
        description=t('CustomPanel.merge_mode_desc'),
        items=[
            ('ARMATURE', t('CustomPanel.mode.armature'), t('CustomPanel.mode.armature_desc')),
            ('MESH', t('CustomPanel.mode.mesh'), t('CustomPanel.mode.mesh_desc'))
        ],
        default='ARMATURE'
    )

    merge_armature_into: StringProperty(
        name=t('MergeArmature.into'),
        description=t('MergeArmature.into_desc'),
        default=""
    )

    merge_armature: StringProperty(
        name=t('MergeArmature.from'),
        description=t('MergeArmature.from_desc'),
        default=""
    )

    attach_mesh: StringProperty(
        name=t('AttachMesh.select'),
        description=t('AttachMesh.select_desc'),
        default=""
    )

    attach_bone: StringProperty(
        name=t('AttachBone.select'),
        description=t('AttachBone.select_desc'),
        default=""
    )

    merge_all_bones: BoolProperty(
        name=t('MergeArmature.merge_all'),
        description=t('MergeArmature.merge_all_desc'),
        default=True
    )

    apply_transforms: BoolProperty(
        name=t('MergeArmature.apply_transforms'),
        description=t('MergeArmature.apply_transforms_desc'),
        default=True
    )

    join_meshes: BoolProperty(
        name=t('MergeArmature.join_meshes'),
        description=t('MergeArmature.join_meshes_desc'),
        default=True
    )

    remove_zero_weights: BoolProperty(
        name=t('MergeArmature.remove_zero_weights'),
        description=t('MergeArmature.remove_zero_weights_desc'),
        default=True
    )

    cleanup_shape_keys: BoolProperty(
        name=t('MergeArmature.cleanup_shape_keys'),
        description=t('MergeArmature.cleanup_shape_keys_desc'),
        default=True
    )

    attach_mesh: StringProperty(
        name=t("Tools.attach_mesh_select"),
        description=t("Tools.attach_mesh_select_desc")
    )

    attach_bone: StringProperty(
        name=t("Tools.attach_bone_select"),
        description=t("Tools.attach_bone_select_desc")
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
