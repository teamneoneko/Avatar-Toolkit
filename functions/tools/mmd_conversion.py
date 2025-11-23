"""
MMD Conversion Operator
Converts MMD armatures to standard Blender format
"""
import bpy
from bpy.types import Operator
from ...core.common import get_active_armature
from ...core.translations import t
from ...core.mmd_converter import (convert_mmd_armature, detect_mmd_armature, 
                                   translate_mmd_everything, restructure_mmd_to_unity_bones,
                                   remove_mmd_ik_bones, remove_mmd_twist_bones, remove_mmd_zero_weight_bones)
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
        restructure_bones = toolkit.mmd_restructure_bones
        remove_twist_bones = toolkit.mmd_remove_twist_bones
        remove_zero_weight_bones = toolkit.mmd_remove_zero_weight_bones
        
        logger.info(f"Conversion settings - Make parent: {make_parent}, Rename: {rename_armature}, " +
                   f"Restructure: {restructure_bones}")
        logger.info(f"Bone cleanup - IK: True (automatic), Twist: {remove_twist_bones}, Zero weight: {remove_zero_weight_bones}")
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
        
        # Step 2: Remove IK bones BEFORE translation (always automatic)
        logger.info("Starting IK bone removal (before translation)")
        self.report({'INFO'}, "Removing IK bones...")
        
        ik_success, ik_messages = remove_mmd_ik_bones(armature)
        
        if ik_success:
            logger.info("IK bone removal completed successfully")
        else:
            logger.warning("IK bone removal completed with errors")
        
        for msg in ik_messages:
            self.report({'INFO'}, msg)
        
        # Step 3: Remove twist bones BEFORE translation (if enabled)
        if remove_twist_bones:
            logger.info("Starting twist bone removal (before translation)")
            self.report({'INFO'}, "Removing twist bones...")
            
            twist_success, twist_messages = remove_mmd_twist_bones(armature)
            
            if twist_success:
                logger.info("Twist bone removal completed successfully")
            else:
                logger.warning("Twist bone removal completed with errors")
            
            for msg in twist_messages:
                self.report({'INFO'}, msg)
        
        # Step 4: Translation (if enabled)
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
        
        # Step 5: Restructure bones to Unity format (if enabled)
        if restructure_bones:
            logger.info("Starting bone restructuring to Unity format")
            self.report({'INFO'}, t("MMD.restructure_starting"))
            
            struct_success, struct_messages = restructure_mmd_to_unity_bones(armature)
            
            if struct_success:
                logger.info("Bone restructuring completed successfully")
            else:
                logger.warning("Bone restructuring completed with errors")
            
            for msg in struct_messages:
                self.report({'INFO'}, msg)
        
        # Step 6: Remove zero weight bones (if enabled)
        if remove_zero_weight_bones:
            logger.info("Starting zero weight bone removal")
            self.report({'INFO'}, "Removing zero weight bones...")
            
            zero_success, zero_messages = remove_mmd_zero_weight_bones(armature)
            
            if zero_success:
                logger.info("Zero weight bone removal completed successfully")
            else:
                logger.warning("Zero weight bone removal completed with errors")
            
            for msg in zero_messages:
                self.report({'INFO'}, msg)
        
        return {'FINISHED'}
