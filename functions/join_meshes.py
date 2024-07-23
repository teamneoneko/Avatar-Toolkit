import bpy
from typing import List, Optional, Set
from bpy.types import Operator, Context, Object
from ..core.register import register_wrap
from ..core.common import fix_uv_coordinates, get_selected_armature, is_valid_armature, select_current_armature, get_all_meshes
from ..functions.translations import t

@register_wrap
class JoinAllMeshes(Operator):
    bl_idname = "avatar_toolkit.join_all_meshes"
    bl_label = t("Optimization.join_all_meshes.label")
    bl_description = t("Optimization.join_all_meshes.desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        armature = get_selected_armature(context)
        return armature is not None and is_valid_armature(armature)

    def execute(self, context: Context) -> Set[str]:
        self.join_all_meshes(context)
        return {'FINISHED'}

    def join_all_meshes(self, context: Context) -> None:
        if not select_current_armature(context):
            self.report({'WARNING'}, "No armature selected")
            return

        armature = get_selected_armature(context)
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')

        meshes: List[Object] = get_all_meshes(context)
        for mesh in meshes:
            mesh.select_set(True)

        if bpy.context.selected_objects:
            bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]
            bpy.ops.object.join()
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            fix_uv_coordinates(context)
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            self.report({'INFO'}, "Meshes joined successfully")
        else:
            self.report({'WARNING'}, "No mesh objects selected")

        context.view_layer.objects.active = armature

@register_wrap
class JoinSelectedMeshes(Operator):
    bl_idname = "avatar_toolkit.join_selected_meshes"
    bl_label = t("Optimization.join_selected_meshes.label")
    bl_description = t("Optimization.join_selected_meshes.desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return context.mode == 'OBJECT' and len([obj for obj in context.selected_objects if obj.type == 'MESH']) > 1

    def execute(self, context: Context) -> Set[str]:
        self.join_selected_meshes(context)
        return {'FINISHED'}

    def join_selected_meshes(self, context: Context) -> None:
        selected_objects: List[Object] = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']

        if len(selected_objects) < 2:
            self.report({'WARNING'}, "Please select at least two mesh objects")
            return

        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')

        for obj in selected_objects:
            obj.select_set(True)

        if bpy.context.selected_objects:
            bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]
            bpy.ops.object.join()
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            fix_uv_coordinates(context)
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            self.report({'INFO'}, "Selected meshes joined successfully")
        else:
            self.report({'WARNING'}, "No mesh objects selected")

