import bpy
import numpy as np
from bpy.types import Operator, Context
from typing import Set
from ...core.translations import t
from ...core.logging_setup import logger
from ...core.common import get_active_armature, get_all_meshes, validate_armature, remove_unused_shapekeys

class AvatarToolkit_OT_ApplyTransforms(Operator):
    """Apply all transformations to armature and associated meshes"""
    bl_idname = "avatar_toolkit.apply_transforms"
    bl_label = t("Tools.apply_transforms")
    bl_description = t("Tools.apply_transforms_desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        armature = get_active_armature(context)
        if not armature:
            return False
        is_valid, _ = validate_armature(armature)
        return is_valid and context.mode == 'OBJECT'

    def execute(self, context: Context) -> Set[str]:
        try:
            armature = get_active_armature(context)
            logger.info(f"Applying transforms to {armature.name} and associated meshes")
            
            # Select armature and meshes
            bpy.ops.object.select_all(action='DESELECT')
            armature.select_set(True)
            context.view_layer.objects.active = armature
            
            meshes = get_all_meshes(context)
            for mesh in meshes:
                mesh.select_set(True)
                
            # Apply transforms
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            
            self.report({'INFO'}, t("Tools.transforms_applied"))
            return {'FINISHED'}
            
        except Exception as e:
            logger.error(f"Failed to apply transforms: {str(e)}")
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

class AvatarToolkit_OT_CleanShapekeys(Operator):
    """Remove unused shape keys from meshes"""
    bl_idname = "avatar_toolkit.clean_shapekeys"
    bl_label = t("Tools.clean_shapekeys")
    bl_description = t("Tools.clean_shapekeys_desc")
    bl_options = {'REGISTER', 'UNDO'}
    
    tolerance: bpy.props.FloatProperty(
        name=t("Tools.shapekey_tolerance"),
        description=t("Tools.shapekey_tolerance_desc"),
        default=0.001,
        min=0.0001,
        max=0.1
    )

    @classmethod
    def poll(cls, context: Context) -> bool:
        armature = get_active_armature(context)
        if not armature:
            return False
        is_valid, _ = validate_armature(armature)
        return is_valid and context.mode == 'OBJECT' and len(get_all_meshes(context)) > 0

    def execute(self, context: Context) -> Set[str]:
        try:
            logger.info("Starting shape key cleanup")
            removed_count = 0
            
            for mesh in get_all_meshes(context):
                if not mesh.data.shape_keys or not mesh.data.shape_keys.use_relative:
                    continue
                    
                removed = remove_unused_shapekeys(mesh, self.tolerance)
                removed_count += removed
                logger.debug(f"Removed {removed} shape keys from {mesh.name}")
            
            self.report({'INFO'}, t("Tools.shapekeys_removed", count=removed_count))
            return {'FINISHED'}
            
        except Exception as e:
            logger.error(f"Failed to clean shape keys: {str(e)}")
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
