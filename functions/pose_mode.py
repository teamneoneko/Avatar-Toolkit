import bpy
from typing import Set, Dict, List, Tuple, Optional, Any
from bpy.props import StringProperty
from bpy.types import Operator, Context, Object, Event, Modifier
from ..core.logging_setup import logger
from ..core.translations import t
from ..core.common import (
    get_active_armature,
    get_all_meshes,
    apply_pose_as_rest,
    validate_armature,
    cache_vertex_positions,
    apply_vertex_positions,
    validate_mesh_for_pose,
    process_armature_modifiers,
    ProgressTracker
)

class BatchPoseOperationMixin:
    """Base class for batch pose operations"""
    @classmethod
    def poll(cls, context: Context) -> bool:
        armature = get_active_armature(context)
        if not armature:
            return False
        valid, _ = validate_armature(armature)
        return valid and context.mode == 'POSE'
    
    def validate_meshes(self, meshes: List[Object]) -> List[Tuple[Object, str]]:
        """Validate meshes for pose operations"""
        invalid_meshes = []
        for mesh in meshes:
            valid, message = validate_mesh_for_pose(mesh)
            if not valid:
                invalid_meshes.append((mesh, message))
        return invalid_meshes

class AvatarToolkit_OT_StartPoseMode(Operator):
    bl_idname = 'avatar_toolkit.start_pose_mode'
    bl_label = t("QuickAccess.start_pose_mode.label")
    bl_description = t("QuickAccess.start_pose_mode.desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        armature = get_active_armature(context)
        if not armature or context.mode == "POSE":
            return False
        valid, _ = validate_armature(armature)
        return valid

    def execute(self, context: Context) -> Set[str]:
        try:
            armature = get_active_armature(context)
            logger.info(f"Starting pose mode for armature: {armature.name}")
            
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            
            context.view_layer.objects.active = armature
            armature.select_set(True)
            bpy.ops.object.mode_set(mode='POSE')
            
            return {'FINISHED'}
        except Exception as e:
            logger.error(f"Failed to start pose mode: {str(e)}")
            self.report({'ERROR'}, t("PoseMode.error.start", error=str(e)))
            return {'CANCELLED'}

class AvatarToolkit_OT_StopPoseMode(Operator):
    bl_idname = 'avatar_toolkit.stop_pose_mode'
    bl_label = t("QuickAccess.stop_pose_mode.label")
    bl_description = t("QuickAccess.stop_pose_mode.desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return get_active_armature(context) and context.mode == "POSE"

    def execute(self, context: Context) -> Set[str]:
        try:
            bpy.ops.pose.transforms_clear()
            bpy.ops.pose.select_all(action="INVERT")
            bpy.ops.pose.transforms_clear()
            bpy.ops.pose.select_all(action="INVERT")
            bpy.ops.object.mode_set(mode='OBJECT')
            return {'FINISHED'}
        except Exception as e:
            logger.error(f"Failed to stop pose mode: {str(e)}")
            self.report({'ERROR'}, t("PoseMode.error.stop", error=str(e)))
            return {'CANCELLED'}

class AvatarToolkit_OT_ApplyPoseAsRest(Operator, BatchPoseOperationMixin):
    bl_idname = 'avatar_toolkit.apply_pose_as_shapekey'
    bl_label = t("QuickAccess.apply_pose_as_shapekey.label")
    bl_description = t("QuickAccess.apply_pose_as_shapekey.desc")
    bl_options = {'REGISTER', 'UNDO'}
    
    shapekey_name: StringProperty(
        name=t("PoseMode.shapekey.name"),
        description=t("PoseMode.shapekey.description"),
        default=t("PoseMode.shapekey.default")
    )

    def invoke(self, context: Context, event: Event) -> Set[str]:
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context: Context) -> Set[str]:
        try:
            meshes = get_all_meshes(context)
            invalid_meshes = self.validate_meshes(meshes)
            
            if invalid_meshes:
                message = "\n".join(f"{mesh.name}: {reason}" for mesh, reason in invalid_meshes)
                self.report({'WARNING'}, t("PoseMode.skipped_meshes", message=message))
            
            valid_meshes = [mesh for mesh in meshes if mesh not in [m for m, _ in invalid_meshes]]
            
            with ProgressTracker(context, len(valid_meshes), "Applying Pose as Shape Key") as progress:
                for mesh_obj in valid_meshes:
                    if not mesh_obj.data.shape_keys:
                        mesh_obj.shape_key_add(name=t("PoseMode.basis"))
                    
                    new_shape = mesh_obj.shape_key_add(name=self.shapekey_name, from_mix=False)
                    cached_positions = cache_vertex_positions(
                        mesh_obj.evaluated_get(context.evaluated_depsgraph_get())
                    )
                    apply_vertex_positions(new_shape.data, cached_positions)
                    progress.step(f"Processed {mesh_obj.name}")

            return {'FINISHED'}
        except Exception as e:
            logger.error(f"Failed to apply pose as shape key: {str(e)}")
            self.report({'ERROR'}, t("PoseMode.error.shapekey", error=str(e)))
            return {'CANCELLED'}

class AvatarToolkit_OT_ApplyPoseAsShapekey(Operator, BatchPoseOperationMixin):
    bl_idname = 'avatar_toolkit.apply_pose_as_rest'
    bl_label = t("QuickAccess.apply_pose_as_rest.label")
    bl_description = t("QuickAccess.apply_pose_as_rest.desc")
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context: Context) -> Set[str]:
        try:
            armature_obj = get_active_armature(context)
            meshes = get_all_meshes(context)
            
            invalid_meshes = self.validate_meshes(meshes)
            if invalid_meshes:
                message = "\n".join(f"{mesh.name}: {reason}" for mesh, reason in invalid_meshes)
                self.report({'WARNING'}, t("PoseMode.skipped_meshes", message=message))
            
            valid_meshes = [mesh for mesh in meshes if mesh not in [m for m, _ in invalid_meshes]]
            
            with ProgressTracker(context, len(valid_meshes) + 2, "Applying Pose as Rest") as progress:
                success, message = apply_pose_as_rest(context, armature_obj, valid_meshes)
                if not success:
                    raise ValueError(message)
                progress.step("Applied pose to armature")
            
            logger.info("Successfully applied pose as rest")
            return {'FINISHED'}
        except Exception as e:
            logger.error(f"Failed to apply pose as rest: {str(e)}")
            self.report({'ERROR'}, t("PoseMode.error.rest_pose", error=str(e)))
            return {'CANCELLED'}
