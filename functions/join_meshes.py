import bpy
from typing import List, Optional, Set
from bpy.types import Operator, Context, Object
from ..core.register import register_wrap
from ..core.common import fix_uv_coordinates, get_selected_armature, is_valid_armature, select_current_armature, get_all_meshes, init_progress, update_progress, finish_progress
from ..functions.translations import t

@register_wrap
class AvatarToolKit_OT_JoinAllMeshes(Operator):
    bl_idname = "avatar_toolkit.join_all_meshes"
    bl_label = t("Optimization.join_all_meshes.label")
    bl_description = t("Optimization.join_all_meshes.desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        armature = get_selected_armature(context)
        return armature is not None and is_valid_armature(armature)

    def execute(self, context: Context) -> Set[str]:
        try:
            self.join_all_meshes(context)
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"{t('Optimization.join_error')}: {str(e)}")
            return {'CANCELLED'}

    def join_all_meshes(self, context: Context) -> None:
        if not select_current_armature(context):
            raise ValueError(t("Optimization.no_armature_selected"))

        armature = get_selected_armature(context)
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')

        meshes: List[Object] = get_all_meshes(context)
        if not meshes:
            raise ValueError(t("Optimization.no_meshes_found"))

        init_progress(context, 5)  # 5 steps in total

        update_progress(self, context, t("Optimization.selecting_meshes"))
        for mesh in meshes:
            mesh.select_set(True)

        if bpy.context.selected_objects:
            bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]
            
            update_progress(self, context, t("Optimization.joining_meshes"))
            try:
                bpy.ops.object.join()
            except RuntimeError as e:
                raise RuntimeError(f"{t('Optimization.join_operation_failed')}: {str(e)}")

            update_progress(self, context, t("Optimization.applying_transforms"))
            try:
                bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            except RuntimeError as e:
                raise RuntimeError(f"{t('Optimization.transform_apply_failed')}: {str(e)}")

            update_progress(self, context, t("Optimization.fixing_uv_coordinates"))
            fix_uv_coordinates(context)
            
            update_progress(self, context, t("Optimization.finalizing"))
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            self.report({'INFO'}, t("Optimization.meshes_joined"))
        else:
            raise ValueError(t("Optimization.no_mesh_selected"))

        context.view_layer.objects.active = armature
        finish_progress(context)

@register_wrap
class AvatarToolKit_OT_JoinSelectedMeshes(Operator):
    bl_idname = "avatar_toolkit.join_selected_meshes"
    bl_label = t("Optimization.join_selected_meshes.label")
    bl_description = t("Optimization.join_selected_meshes.desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return context.mode == 'OBJECT' and len([obj for obj in context.selected_objects if obj.type == 'MESH']) > 1

    def execute(self, context: Context) -> Set[str]:
        try:
            self.join_selected_meshes(context)
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"{t('Optimization.join_error')}: {str(e)}")
            return {'CANCELLED'}

    def join_selected_meshes(self, context: Context) -> None:
        selected_objects: List[Object] = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']

        if len(selected_objects) < 2:
            raise ValueError(t("Optimization.select_at_least_two_meshes"))

        init_progress(context, 5)  # 5 steps in total

        update_progress(self, context, t("Optimization.preparing_meshes"))
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')

        update_progress(self, context, t("Optimization.selecting_meshes"))
        for obj in selected_objects:
            obj.select_set(True)

        if bpy.context.selected_objects:
            bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]
            
            update_progress(self, context, t("Optimization.joining_meshes"))
            try:
                bpy.ops.object.join()
            except RuntimeError as e:
                raise RuntimeError(f"{t('Optimization.join_operation_failed')}: {str(e)}")

            update_progress(self, context, t("Optimization.applying_transforms"))
            try:
                bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            except RuntimeError as e:
                raise RuntimeError(f"{t('Optimization.transform_apply_failed')}: {str(e)}")

            update_progress(self, context, t("Optimization.fixing_uv_coordinates"))
            fix_uv_coordinates(context)
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            self.report({'INFO'}, t("Optimization.selected_meshes_joined"))
        else:
            raise ValueError(t("Optimization.no_mesh_selected"))

        finish_progress(context)
