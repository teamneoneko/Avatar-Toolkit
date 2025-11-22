"""
MMD Conversion Operator
Converts MMD armatures to standard Blender format
"""
import bpy
from bpy.types import Operator
from ...core.common import get_active_armature
from ...core.translations import t
from ...core.mmd_converter import convert_mmd_armature, detect_mmd_armature
from ...core.logging_setup import logger


class AvatarToolkit_OT_ConvertMMDArmature(Operator):
    """Convert MMD armature to standard Blender format"""
    bl_idname = "avatar_toolkit.convert_mmd_armature"
    bl_label = t("MMD.convert_armature.label")
    bl_description = t("MMD.convert_armature.desc")
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        armature = get_active_armature(context)
        return armature is not None
    
    def execute(self, context):
        armature = get_active_armature(context)
        if not armature:
            logger.warning("No active armature found for MMD conversion")
            self.report({'ERROR'}, t("MMD.no_armature_selected"))
            return {'CANCELLED'}
        
        logger.info(f"Starting MMD conversion for armature: {armature.name}")
        
        # Check if it's an MMD armature
        if not detect_mmd_armature(armature):
            logger.warning(f"Armature '{armature.name}' does not appear to be an MMD armature")
            self.report({'WARNING'}, t("MMD.not_mmd_armature"))
            return {'CANCELLED'}
        
        # conversion settings
        toolkit = context.scene.avatar_toolkit
        make_parent = toolkit.mmd_make_parent
        rename_armature = toolkit.mmd_rename_armature
        
        logger.info(f"Conversion settings - Make parent: {make_parent}, Rename: {rename_armature}")
        success, messages = convert_mmd_armature(armature, make_parent, rename_armature)
        
        if not success:
            logger.warning(f"MMD conversion failed: {messages}")
            for msg in messages:
                self.report({'WARNING'}, msg)
            return {'CANCELLED'}
        
        logger.info(f"MMD conversion completed successfully")
        for msg in messages:
            self.report({'INFO'}, msg)
        
        return {'FINISHED'}
