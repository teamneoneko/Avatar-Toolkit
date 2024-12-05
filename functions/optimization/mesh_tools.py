import bpy
from typing import Set, List, Tuple, ClassVar
from bpy.types import Operator, Context, Object
from ...core.logging_setup import logger
from ...core.translations import t
from ...core.common import (
    get_active_armature,
    get_all_meshes,
    validate_armature,
    validate_meshes,
    join_mesh_objects,
    ProgressTracker
)

class AvatarToolkit_OT_JoinAllMeshes(Operator):
    """Operator to join all meshes in the scene"""
    bl_idname: ClassVar[str] = "avatar_toolkit.join_all_meshes"
    bl_label: ClassVar[str] = t("Optimization.join_all_meshes")
    bl_description: ClassVar[str] = t("Optimization.join_all_meshes_desc")
    bl_options: ClassVar[Set[str]] = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        armature: Object | None = get_active_armature(context)
        if not armature:
            return False
        valid: bool
        valid, _ = validate_armature(armature)
        return valid

    def execute(self, context: Context) -> Set[str]:
        try:
            armature: Object = get_active_armature(context)
            meshes: List[Object] = get_all_meshes(context)
            
            valid: bool
            message: str
            valid, message = validate_meshes(meshes)
            if not valid:
                self.report({'WARNING'}, message)
                return {'CANCELLED'}

            with ProgressTracker(context, 5, "Joining All Meshes") as progress:
                success: bool
                success, message = join_mesh_objects(context, meshes, progress)
                
                if success:
                    context.view_layer.objects.active = armature
                    self.report({'INFO'}, message)
                    return {'FINISHED'}
                else:
                    self.report({'ERROR'}, message)
                    return {'CANCELLED'}
                    
        except Exception as e:
            logger.error(f"Failed to join meshes: {str(e)}")
            self.report({'ERROR'}, t("Optimization.error.join_meshes", error=str(e)))
            return {'CANCELLED'}

class AvatarToolkit_OT_JoinSelectedMeshes(Operator):
    """Operator to join selected meshes"""
    bl_idname: ClassVar[str] = "avatar_toolkit.join_selected_meshes"
    bl_label: ClassVar[str] = t("Optimization.join_selected_meshes")
    bl_description: ClassVar[str] = t("Optimization.join_selected_meshes_desc")
    bl_options: ClassVar[Set[str]] = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        armature: Object | None = get_active_armature(context)
        if not armature:
            return False
        valid: bool
        valid, _ = validate_armature(armature)
        return (valid and 
                context.mode == 'OBJECT' and 
                len([obj for obj in context.selected_objects if obj.type == 'MESH']) > 1)

    def execute(self, context: Context) -> Set[str]:
        try:
            selected_meshes: List[Object] = [obj for obj in context.selected_objects if obj.type == 'MESH']
            
            valid: bool
            message: str
            valid, message = validate_meshes(selected_meshes)
            if not valid:
                self.report({'WARNING'}, message)
                return {'CANCELLED'}

            with ProgressTracker(context, 5, "Joining Selected Meshes") as progress:
                success: bool
                success, message = join_mesh_objects(context, selected_meshes, progress)
                
                if success:
                    self.report({'INFO'}, message)
                    return {'FINISHED'}
                else:
                    self.report({'ERROR'}, message)
                    return {'CANCELLED'}
                
        except Exception as e:
            logger.error(f"Failed to join selected meshes: {str(e)}")
            self.report({'ERROR'}, t("Optimization.error.join_selected", error=str(e)))
            return {'CANCELLED'}
