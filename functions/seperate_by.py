import bpy
from bpy.types import Context, Operator
from ..core.register import register_wrap
from ..functions.translations import t

@register_wrap
class AvatarToolKit_OT_SeparateByMaterials(Operator):
    bl_idname = "avatar_toolkit.separate_by_materials"
    bl_label = t("Tools.separate_by_materials.label")
    bl_description = t("Tools.separate_by_materials.desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return context.active_object and context.active_object.type == 'MESH'

    def execute(self, context: Context) -> set[str]:
        obj = context.active_object
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.separate(type='MATERIAL')
        bpy.ops.object.mode_set(mode='OBJECT')
        self.report({'INFO'}, t("Tools.separate_by_materials.success"))
        return {'FINISHED'}

@register_wrap
class AvatarToolKit_OT_SeparateByLooseParts(Operator):
    bl_idname = "avatar_toolkit.separate_by_loose_parts"
    bl_label = t("Tools.separate_by_loose_parts.label")
    bl_description = t("Tools.separate_by_loose_parts.desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return context.active_object and context.active_object.type == 'MESH'

    def execute(self, context: Context) -> set[str]:
        obj = context.active_object
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.separate(type='LOOSE')
        bpy.ops.object.mode_set(mode='OBJECT')
        self.report({'INFO'}, t("Tools.separate_by_loose_parts.success"))
        return {'FINISHED'}
