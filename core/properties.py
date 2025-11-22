import bpy
from typing import List, Tuple, Optional, Any, Dict, Union, Callable
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
from .common import get_armature_list, get_active_armature, get_all_meshes, SceneMatClass
from ..functions.visemes import VisemePreview
from ..functions.eye_tracking import set_rotation

class ValidationMessageItem(PropertyGroup):
    """Property group for validation message items"""
    name: StringProperty(name="Message")

class ZeroWeightBoneItem(PropertyGroup):
    """Property group for zero weight bone list items"""
    name: StringProperty(name="Bone Name")
    selected: BoolProperty(name="Selected", default=True)
    has_children: BoolProperty(name="Has Children", default=False)
    is_deform: BoolProperty(name="Is Deform Bone", default=False)


def update_validation_mode(self: PropertyGroup, context: Context) -> None:
    """Updates validation mode and saves preference"""
    logger.info(f"Updating validation mode to: {self.validation_mode}")
    save_preference("validation_mode", self.validation_mode)
    
    # Hide validation results if mode is set to NONE
    if self.validation_mode == 'NONE':
        self.show_validation_results = False
        logger.debug("Validation mode set to NONE, hiding validation results")


def update_logging_state(self: PropertyGroup, context: Context) -> None:
    """Updates logging state and configures logging"""
    logger.info(f"Updating logging state to: {self.enable_logging}")
    save_preference("enable_logging", self.enable_logging)
    from .logging_setup import configure_logging
    configure_logging(self.enable_logging)

def update_log_level(self: PropertyGroup, context: Context) -> None:
    """Updates log level and configures logging"""
    logger.info(f"Updating log level to: {self.log_level}")
    save_preference("log_level", self.log_level)
    from .logging_setup import configure_logging
    configure_logging(self.enable_logging, self.log_level)


def update_shape_intensity(self: PropertyGroup, context: Context) -> None:
    """Updates shape key intensity and refreshes preview"""
    if self.viseme_preview_mode:
        VisemePreview.update_preview(context)

def highlight_problem_bones(self: PropertyGroup, context: Context) -> None:
    """Updates problem bone highlighting state and saves preference"""
    logger.info(f"Updating problem bone highlighting to: {self.highlight_problem_bones}")
    save_preference("highlight_problem_bones", self.highlight_problem_bones)

def get_mesh_objects(self, context):
    meshes = [(obj.name, obj.name, "") for obj in bpy.data.objects if obj.type == 'MESH']
    if not meshes:
        return [('NONE', t("Visemes.no_meshes"), '')]
    return meshes

def auto_populate_merge_armatures(context: Context) -> None:
    """Auto-populate merge armature fields when there are 2+ armatures"""
    armatures = [obj for obj in bpy.data.objects if obj.type == 'ARMATURE']
    
    if len(armatures) >= 2:
        toolkit = context.scene.avatar_toolkit
        
        if not toolkit.merge_armature_into and not toolkit.merge_armature:
            toolkit.merge_armature_into = armatures[0].name
            toolkit.merge_armature = armatures[1].name
            logger.debug(f"Auto-populated merge armatures: {armatures[0].name} <- {armatures[1].name}")

        elif toolkit.merge_armature_into and not toolkit.merge_armature:
            for armature in armatures:
                if armature.name != toolkit.merge_armature_into:
                    toolkit.merge_armature = armature.name
                    logger.debug(f"Auto-populated merge_armature: {armature.name}")
                    break

        elif not toolkit.merge_armature_into and toolkit.merge_armature:
            for armature in armatures:
                if armature.name != toolkit.merge_armature:
                    toolkit.merge_armature_into = armature.name
                    logger.debug(f"Auto-populated merge_armature_into: {armature.name}")
                    break

def update_merge_armature_into(self: PropertyGroup, context: Context) -> None:
    """Update function for merge_armature_into property"""
    auto_populate_merge_armatures(context)

def update_merge_armature(self: PropertyGroup, context: Context) -> None:
    """Update function for merge_armature property"""
    auto_populate_merge_armatures(context)

@bpy.app.handlers.persistent
def depsgraph_update_handler(scene: Scene, depsgraph) -> None:
    """Handler to auto-populate merge armatures when objects change"""
    # Check for any armature-related updates
    armature_updated = False
    for update in depsgraph.updates:
        if hasattr(update, 'id') and update.id and hasattr(update.id, 'type'):
            if update.id.type == 'ARMATURE':
                armature_updated = True
                break
    
    if armature_updated:
        # Use a timer to defer the update to avoid context issues
        bpy.app.timers.register(lambda: auto_populate_safe(), first_interval=0.1)

def auto_populate_safe() -> None:
    """Safe auto-populate function that can be called from timer"""
    try:
        if bpy.context and hasattr(bpy.context, 'scene') and hasattr(bpy.context.scene, 'avatar_toolkit'):
            auto_populate_merge_armatures(bpy.context)
    except (AttributeError, ReferenceError):
        pass
    return None  # Don't repeat the timer

@bpy.app.handlers.persistent
def undo_post_handler(scene: Scene) -> None:
    """Handler for undo operations that might add/remove armatures"""
    bpy.app.timers.register(lambda: auto_populate_safe(), first_interval=0.1)

@bpy.app.handlers.persistent  
def redo_post_handler(scene: Scene) -> None:
    """Handler for redo operations that might add/remove armatures"""
    bpy.app.timers.register(lambda: auto_populate_safe(), first_interval=0.1)

class AvatarToolkitSceneProperties(PropertyGroup):
    """Property group containing Avatar Toolkit scene-level settings and properties"""

    show_found_bones: BoolProperty(
        name="Show Found Bones",
        default=False
    )
    
    show_non_standard: BoolProperty(
        name="Show Non-Standard Bones", 
        default=False
    )

    show_hierarchy: BoolProperty(
        name="Show Hierarchy Issues",
        default=False
    )

    show_validation_results: BoolProperty(
        name="Show Validation Results",
        default=False,
        description="Show the validation results section"
    )

    material_search_filter: StringProperty(
        name=t("TextureAtlas.search_materials"),
        description=t("TextureAtlas.search_materials_desc"),
        default=""
    )

    def get_texture_node_list(self: Material, context: Context) -> list[tuple]:
        if self.use_nodes:
            Object.Enum = [((i.image.name if i.image else i.name+"_image"),
                        (i.image.name if i.image else "node with no image..."),
                        (i.image.name if i.image else i.name), index+1) 
                        for index, i in enumerate(self.node_tree.nodes) 
                        if i.bl_idname == "ShaderNodeTexImage"]
            if not len(Object.Enum):
                Object.Enum = [(t("TextureAtlas.error.label"), 
                            t("TextureAtlas.no_images_error.desc"),
                            t("TextureAtlas.error.label"), 0)]
        else:
            Object.Enum = [(t("TextureAtlas.error.label"),
                        t("TextureAtlas.no_nodes_error.desc"),
                        t("TextureAtlas.error.label"), 0)]
        Object.Enum.append((t("TextureAtlas.none.label"),
                        t("TextureAtlas.none.label"),
                        t("TextureAtlas.none.label"), 0))
        return Object.Enum

    Material.texture_atlas_albedo = EnumProperty(
        name=t("TextureAtlas.albedo"),
        description=t("TextureAtlas.texture_use_atlas.desc").format(name=t("TextureAtlas.albedo").lower()),
        default=0,
        items=get_texture_node_list
    )

    Material.texture_atlas_normal = EnumProperty(
        name=t("TextureAtlas.normal"),
        description=t("TextureAtlas.texture_use_atlas.desc").format(name=t("TextureAtlas.normal").lower()),
        default=0,
        items=get_texture_node_list
    )

    Material.texture_atlas_emission = EnumProperty(
        name=t("TextureAtlas.emission"),
        description=t("TextureAtlas.texture_use_atlas.desc").format(name=t("TextureAtlas.emission").lower()),
        default=0,
        items=get_texture_node_list
    )

    Material.texture_atlas_ambient_occlusion = EnumProperty(
        name=t("TextureAtlas.ambient_occlusion"),
        description=t("TextureAtlas.texture_use_atlas.desc").format(name=t("TextureAtlas.ambient_occlusion").lower()),
        default=0,
        items=get_texture_node_list
    )

    Material.texture_atlas_height = EnumProperty(
        name=t("TextureAtlas.height"),
        description=t("TextureAtlas.texture_use_atlas.desc").format(name=t("TextureAtlas.height").lower()),
        default=0,
        items=get_texture_node_list
    )

    Material.texture_atlas_roughness = EnumProperty(
        name=t("TextureAtlas.roughness"),
        description=t("TextureAtlas.texture_use_atlas.desc").format(name=t("TextureAtlas.roughness").lower()),
        default=0,
        items=get_texture_node_list
    )

    list_only_mode: BoolProperty(
        name=t("Tools.list_only_mode"),
        description=t("Tools.list_only_mode_desc"),
        default=False
    )

    Material.include_in_atlas = BoolProperty(
        name=t("TextureAtlas.include_in_atlas"),
        description=t("TextureAtlas.include_in_atlas_desc"),
        default=False
    )

    Material.material_expanded = BoolProperty(
        name=t("TextureAtlas.material_expanded"),
        description=t("TextureAtlas.material_expanded_desc"),
        default=False
    )

    texture_atlas_Has_Mat_List_Shown: BoolProperty(
        name=t("TextureAtlas.list_shown"),
        description=t("TextureAtlas.list_shown_desc"),
        default=False
    )

    texture_atlas_material_index: IntProperty(
        default=-1,
        get=lambda self: -1,
        set=lambda self, context: None
    )

    materials: CollectionProperty(
        type=SceneMatClass
    )
    
    avatar_toolkit_updater_version_list: EnumProperty(
        items=get_version_list,
        name=t("Scene.avatar_toolkit_updater_version_list.name"),
        description=t("Scene.avatar_toolkit_updater_version_list.description")
    )

    active_armature: EnumProperty(
        items=get_armature_list,
        name=t("QuickAccess.select_armature"),
        description=t("QuickAccess.select_armature"),
        update=lambda self, context: update_active_armature(self, context)
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
        default=get_preference("validation_mode", "NONE"),
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

    connect_bones_min_distance: FloatProperty(
        name=t("Tools.connect_bones_min_distance"),
        description=t("Tools.connect_bones_min_distance_desc"),
        default=0.001,
        min=0.0001,
        max=0.1,
        precision=4
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

    viseme_mesh: EnumProperty(
        name=t("Visemes.mesh_select"),
        description=t("Visemes.mesh_select_desc"),
        items=get_mesh_objects
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
        default="",
        update=update_merge_armature_into
    )

    merge_armature: StringProperty(
        name=t('MergeArmature.from'),
        description=t('MergeArmature.from_desc'),
        default="",
        update=update_merge_armature
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

    preserve_parent_bones: BoolProperty(
        name=t("Tools.preserve_parent_bones"),
        description=t("Tools.preserve_parent_bones_desc"),
        default=True
    )

    target_bone_type: EnumProperty(
        name=t("Tools.target_bone_type"),
        description=t("Tools.target_bone_type_desc"),
        items=[
            ('ALL', t("Tools.target_all_bones"), ""),
            ('DEFORM', t("Tools.target_deform_bones"), ""),
            ('NON_DEFORM', t("Tools.target_non_deform_bones"), "")
        ],
        default='ALL'
    )

    zero_weight_bones: CollectionProperty(
        type=ZeroWeightBoneItem,
        name="Zero Weight Bones",
        description="List of bones with zero weights"
    )
    
    zero_weight_bones_index: IntProperty(
        name="Zero Weight Bone Index",
        default=0
    )

    list_only_mode: BoolProperty(
        name=t("Tools.list_only_mode"),
        description=t("Tools.list_only_mode_desc"),
        default=False
    )

    cleanup_shape_keys: BoolProperty(
        name=t('MergeArmature.cleanup_shape_keys'),
        description=t('MergeArmature.cleanup_shape_keys_desc'),
        default=True
    )
      
    merge_twist_bones: BoolProperty(
        name=t("Tools.merge_twist_bones"),
        description=t("Tools.merge_twist_bones_desc"),
        default=True
    )

    highlight_problem_bones: BoolProperty(
        name=t("Settings.highlight_problem_bones"),
        description=t("Settings.highlight_problem_bones_desc"),
        default=get_preference("highlight_problem_bones", True),
        update=highlight_problem_bones
    )

    show_scale_issues: BoolProperty(
        name="Show Scale Issues",
        default=False
    )

    tpose_validation_result: BoolProperty(
        name="T-Pose Validation Result",
        default=True
    )
    
    tpose_validation_messages: CollectionProperty(
        type=bpy.types.PropertyGroup,
        name="T-Pose Validation Messages"
    )
    
    show_tpose_validation: BoolProperty(
        name="Show T-Pose Validation Results",
        default=False
    )

    standardize_fix_names: BoolProperty(
        name=t("Tools.standardize_fix_names"),
        description=t("Tools.standardize_fix_names_desc"),
        default=True
    )

    standardize_fix_hierarchy: BoolProperty(
        name=t("Tools.standardize_fix_hierarchy"),
        description=t("Tools.standardize_fix_hierarchy_desc"),
        default=True
    )

    standardize_fix_scale: BoolProperty(
        name=t("Tools.standardize_fix_scale"),
        description=t("Tools.standardize_fix_scale_desc"),
        default=True
    )

    log_level: EnumProperty(
        name=t("Settings.log_level"),
        description=t("Settings.log_level_desc"),
        items=[
            ('DEBUG', t("Settings.log_level.debug"), t("Settings.log_level.debug_desc")),
            ('INFO', t("Settings.log_level.info"), t("Settings.log_level.info_desc")),
            ('WARNING', t("Settings.log_level.warning"), t("Settings.log_level.warning_desc")),
            ('ERROR', t("Settings.log_level.error"), t("Settings.log_level.error_desc")),
        ],
        default=get_preference("log_level", "WARNING"),
        update=update_log_level
    )

    # VRM Conversion Properties
    vrm_remove_colliders: BoolProperty(
        name=t("VRM.remove_colliders"),
        description=t("VRM.remove_colliders_desc"),
        default=True
    )
    
    vrm_remove_root: BoolProperty(
        name=t("VRM.remove_root"),
        description=t("VRM.remove_root_desc"),
        default=True
    )

    # Translation System Properties
    translation_service: EnumProperty(
        name=t("Translation.service"),
        description=t("Translation.service_desc"),
        items=[
            ('mymemory', t("Translation.service.mymemory"), t("Translation.service.mymemory_desc")),
            ('libretranslate', t("Translation.service.libretranslate"), t("Translation.service.libretranslate_desc")),
            ('deepl', t("Translation.service.deepl"), t("Translation.service.deepl_desc"))
        ],
        default=get_preference("translation_service", "mymemory"),
        update=lambda self, context: update_translation_service(self, context)
    )
    
    translation_mode: EnumProperty(
        name=t("Translation.mode"),
        description=t("Translation.mode_desc"),
        items=[
            ('hybrid', t("Translation.mode.hybrid"), t("Translation.mode.hybrid_desc")),
            ('dictionary_only', t("Translation.mode.dictionary_only"), t("Translation.mode.dictionary_only_desc")),
            ('api_only', t("Translation.mode.api_only"), t("Translation.mode.api_only_desc"))
        ],
        default=get_preference("translation_mode", "hybrid"),
        update=lambda self, context: update_translation_mode(self, context)
    )
    
    translation_expand: BoolProperty(
        name="Translation Settings Expanded",
        default=False
    )
    
    
    translation_target_language: EnumProperty(
        name=t("Translation.target_language"),
        description=t("Translation.target_language_desc"),
        items=[
            ('en', 'English', 'Translate to English'),
            ('ja', 'Japanese', 'Translate to Japanese'),
            ('ko', 'Korean', 'Translate to Korean'),
            ('zh', 'Chinese', 'Translate to Chinese'),
            ('es', 'Spanish', 'Translate to Spanish'),
            ('fr', 'French', 'Translate to French'),
            ('de', 'German', 'Translate to German')
        ],
        default='en'
    )
    
    translation_source_language: EnumProperty(
        name=t("Translation.source_language"),
        description=t("Translation.source_language_desc"),
        items=[
            ('auto', 'Auto-detect', 'Automatically detect source language'),
            ('ja', 'Japanese', 'Source is Japanese'),
            ('en', 'English', 'Source is English'),
            ('ko', 'Korean', 'Source is Korean'),
            ('zh', 'Chinese', 'Source is Chinese')
        ],
        default='ja'
    )


def update_translation_service(self: PropertyGroup, context: Context) -> None:
    """Update translation service preference"""
    logger.info(f"Updating translation service to: {self.translation_service}")
    save_preference("translation_service", self.translation_service)
    
    # Clear module-level translation caches when service changes
    try:
        from ..ui.translation_panel import _ui_cache
        _ui_cache['deepl_config'].clear()
        _ui_cache['libretranslate_config'].clear()
        _ui_cache['translation_status'].clear()
        if 'batch_info' in _ui_cache:
            del _ui_cache['batch_info']  # Clear batch info cache when service changes
    except ImportError:
        pass  # UI module might not be loaded yet
    
    # Set the primary service
    try:
        from .translation_manager import get_avatar_translation_manager
        manager = get_avatar_translation_manager()
        manager.service_manager.set_primary_service(self.translation_service)
    except Exception as e:
        logger.error(f"Failed to update translation service: {e}")


def update_translation_mode(self: PropertyGroup, context: Context) -> None:
    """Update translation mode preference"""
    logger.info(f"Updating translation mode to: {self.translation_mode}")
    save_preference("translation_mode", self.translation_mode)
    
    # Clear module-level translation status cache when mode changes
    try:
        from ..ui.translation_panel import _ui_cache
        _ui_cache['translation_status'].clear()
        if 'batch_info' in _ui_cache:
            del _ui_cache['batch_info']  # Clear batch info cache when mode changes
    except ImportError:
        pass  # UI module might not be loaded yet
    
    try:
        from .translation_manager import get_avatar_translation_manager, TranslationMode
        manager = get_avatar_translation_manager()
        manager.set_translation_mode(TranslationMode(self.translation_mode))
    except Exception as e:
        logger.error(f"Failed to update translation mode: {e}")


def update_active_armature(self: PropertyGroup, context: Context) -> None:
    """Update the active armature when selection changes"""
    if self.active_armature and self.active_armature != 'NONE':
        # Get the actual armature object from the identifier
        armature = get_active_armature(context)
        
        if armature:
            logger.info(f"Active armature set to: {armature.name}")
            # Deselect all objects first
            bpy.ops.object.select_all(action='DESELECT')
            # Select and make active the chosen armature
            armature.select_set(True)
            context.view_layer.objects.active = armature
            logger.info(f"Selected and activated armature: {armature.name}")
            
            # Clear armature caches when armature changes to ensure fresh validation
            try:
                from ..ui.quick_access_panel import clear_armature_caches
                clear_armature_caches()
            except ImportError:
                pass  # UI module might not be loaded yet
        else:
            logger.warning("Failed to get armature object from identifier")
    else:
        logger.info("No armature selected")






def register() -> None:
    """Register the Avatar Toolkit property group"""
    logger.info("Registering Avatar Toolkit properties")
    
    # Only register the property, not the classes (auto_load will handle that)
    bpy.types.Scene.avatar_toolkit = PointerProperty(type=AvatarToolkitSceneProperties)
    
    # Register handlers for auto-populating merge armatures
    bpy.app.handlers.depsgraph_update_post.append(depsgraph_update_handler)
    bpy.app.handlers.undo_post.append(undo_post_handler)
    bpy.app.handlers.redo_post.append(redo_post_handler)
    
    # Initial auto-populate
    bpy.app.timers.register(lambda: auto_populate_safe(), first_interval=1.0)
    
    logger.debug("Properties registered successfully")


def unregister() -> None:
    """Unregister the Avatar Toolkit property group"""
    logger.info("Unregistering Avatar Toolkit properties")
    
    # Remove handlers
    if depsgraph_update_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(depsgraph_update_handler)
    if undo_post_handler in bpy.app.handlers.undo_post:
        bpy.app.handlers.undo_post.remove(undo_post_handler)
    if redo_post_handler in bpy.app.handlers.redo_post:
        bpy.app.handlers.redo_post.remove(redo_post_handler)
    
    # Remove the property
    if hasattr(bpy.types.Scene, "avatar_toolkit"):
        try:
            del bpy.types.Scene.avatar_toolkit
            logger.debug("Removed avatar_toolkit property")
        except Exception as e:
            logger.warning(f"Failed to remove avatar_toolkit property: {e}")
        # Not fatal - continue
