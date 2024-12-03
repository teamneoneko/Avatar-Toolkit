import bpy
import numpy as np
from bpy.types import Operator, Context, Object
from typing import List
from ..core.translations import t
from ..core.common import (
    get_active_armature,
    get_all_meshes,
    apply_pose_as_rest,
    apply_armature_to_mesh,
    apply_armature_to_mesh_with_shapekeys,
    validate_armature
)

class AvatarToolkit_OT_StartPoseMode(Operator):
    bl_idname = 'avatar_toolkit.start_pose_mode'
    bl_label = t("Quick_Access.start_pose_mode.label")
    bl_description = t("Quick_Access.start_pose_mode.desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        armature = get_active_armature(context)
        if not armature or context.mode == "POSE":
            return False
        is_valid, _ = validate_armature(armature)
        return is_valid
    
    def execute(self, context: Context) -> set[str]:
        armature = get_active_armature(context)
        context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        armature.select_set(True)
        bpy.ops.object.mode_set(mode='POSE')
        return {'FINISHED'}

class AvatarToolkit_OT_StopPoseMode(Operator):
    bl_idname = 'avatar_toolkit.stop_pose_mode'
    bl_label = t("Quick_Access.stop_pose_mode.label")
    bl_description = t("Quick_Access.stop_pose_mode.desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return get_active_armature(context) and context.mode == "POSE"
    
    def execute(self, context: Context) -> set[str]:
        bpy.ops.pose.transforms_clear()
        bpy.ops.pose.select_all(action="INVERT")
        bpy.ops.pose.transforms_clear()
        bpy.ops.pose.select_all(action="INVERT")
        bpy.ops.object.mode_set(mode='OBJECT')
        return {'FINISHED'}

class AvatarToolkit_OT_ApplyPoseAsShapekey(Operator):
    bl_idname = 'avatar_toolkit.apply_pose_as_shapekey'
    bl_label = t("Quick_Access.apply_pose_as_shapekey.label")
    bl_description = t("Quick_Access.apply_pose_as_shapekey.desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        armature = get_active_armature(context)
        if not armature or context.mode != 'POSE':
            return False
        is_valid, _ = validate_armature(armature)
        return is_valid
        
    def execute(self, context):
        armature_obj = get_active_armature(context)
        mesh_objects = get_all_meshes(context)
        
        for mesh_obj in mesh_objects:
            if not mesh_obj.data:
                continue
                
            if not mesh_obj.data.shape_keys:
                mesh_obj.shape_key_add(name='Basis')
                
            new_shape = mesh_obj.shape_key_add(name='Pose_Shapekey', from_mix=False)
            
            depsgraph = context.evaluated_depsgraph_get()
            eval_mesh = mesh_obj.evaluated_get(depsgraph)
            
            for i, v in enumerate(eval_mesh.data.vertices):
                new_shape.data[i].co = v.co.copy()

        bpy.ops.pose.select_all(action='SELECT')
        bpy.ops.pose.transforms_clear()
        bpy.ops.object.mode_set(mode='OBJECT')
        
        self.report({'INFO'}, t('Tools.apply_pose_as_rest.success'))
        return {'FINISHED'}

class AvatarToolkit_OT_ApplyPoseAsRest(Operator):
    bl_idname = 'avatar_toolkit.apply_pose_as_rest'
    bl_label = t("Quick_Access.apply_pose_as_rest.label")
    bl_description = t("Quick_Access.apply_pose_as_rest.desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        armature = get_active_armature(context)
        if not armature or context.mode != "POSE":
            return False
        is_valid, _ = validate_armature(armature)
        return is_valid
    
    def execute(self, context):
        if not apply_pose_as_rest(
            context=context,
            armature_obj=get_active_armature(context),
            meshes=get_all_meshes(context)
        ):
            self.report({'ERROR'}, t("Quick_Access.apply_armature_failed"))
            return {'CANCELLED'}
        
        self.report({'INFO'}, t("Tools.apply_pose_as_rest.success"))
        return {'FINISHED'}
