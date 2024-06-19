import bpy
from ..core.register import register_wrap
from ..core.common import fix_uv_coordinates
from ..core.translation import t

@register_wrap
class JoinAllMeshes(bpy.types.Operator):
    bl_idname = "avatar_toolkit.join_all_meshes"
    bl_label = t("avatar_toolkit.join_all_meshes.label")
    bl_description = t("avatar_toolkit.join_all_meshes.desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        self.join_all_meshes(context)
        return {'FINISHED'}

    def join_all_meshes(self, context):
        if not bpy.data.objects:
            self.report({'INFO'}, "No objects in the scene")
            return

        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')

        meshes = [obj for obj in bpy.data.objects if obj.type == 'MESH']
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

@register_wrap
class JoinSelectedMeshes(bpy.types.Operator):
    bl_idname = "avatar_toolkit.join_selected_meshes"
    bl_label = t("avatar_toolkit.join_selected_meshes.label")
    bl_description = t("avatar_toolkit.join_selected_meshes.desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        self.join_selected_meshes(context)
        return {'FINISHED'}

    def join_selected_meshes(self, context):
        selected_objects = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']

        if not selected_objects:
            self.report({'WARNING'}, "No mesh objects selected")
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
