"""
MMD Conversion Operator
Converts MMD armatures to standard Blender format
"""
import bpy
from bpy.types import Operator
from ...core.common import get_active_armature
from ...core.translations import t
from ...core.mmd_converter import (convert_mmd_armature, detect_mmd_armature, 
                                   translate_mmd_everything)
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
        
        # Get conversion settings
        toolkit = context.scene.avatar_toolkit
        make_parent = toolkit.mmd_make_parent
        rename_armature = toolkit.mmd_rename_armature
        translate_names = toolkit.mmd_translate_names
        translate_bones = toolkit.mmd_translate_bones
        translate_materials = toolkit.mmd_translate_materials
        translate_shapekeys = toolkit.mmd_translate_shapekeys
        translate_objects = toolkit.mmd_translate_objects
        
        logger.info(f"Conversion settings - Make parent: {make_parent}, Rename: {rename_armature}")
        logger.info(f"Translation settings - Enabled: {translate_names}, Bones: {translate_bones}, " +
                   f"Materials: {translate_materials}, Shapekeys: {translate_shapekeys}, Objects: {translate_objects}")
        
        # Step 1: Basic conversion (parent and rename)
        success, messages = convert_mmd_armature(armature, make_parent, rename_armature)
        
        if not success:
            logger.warning(f"MMD conversion failed: {messages}")
            for msg in messages:
                self.report({'WARNING'}, msg)
            return {'CANCELLED'}
        
        logger.info(f"MMD basic conversion completed successfully")
        for msg in messages:
            self.report({'INFO'}, msg)
        
        # Step 2: Translation (if enabled)
        if translate_names:
            logger.info("Starting MMD name translation")
            self.report({'INFO'}, t("MMD.translation_starting"))
            
            trans_success, trans_messages = translate_mmd_everything(
                armature,
                translate_bones=translate_bones,
                translate_materials=translate_materials,
                translate_shapekeys=translate_shapekeys,
                translate_objects=translate_objects
            )
            
            if trans_success:
                logger.info("MMD name translation completed successfully")
            else:
                logger.warning("MMD name translation completed with some failures")
            
            for msg in trans_messages:
                self.report({'INFO'}, msg)
        
        return {'FINISHED'}
