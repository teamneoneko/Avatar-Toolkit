import bpy
from bpy.types import Context, Operator
from ..core.register import register_wrap
from ..core.common import get_selected_armature, is_valid_armature, get_all_meshes
from ..functions.translations import t

@register_wrap
class AvatarToolKit_OT_ApplyTransforms(Operator):
    bl_idname = "avatar_toolkit.apply_transforms"
    bl_label = t("Tools.apply_transforms.label")
    bl_description = t("Tools.apply_transforms.desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return get_selected_armature(context) is not None

    def execute(self, context: Context) -> set[str]:
        armature = get_selected_armature(context)
        if not is_valid_armature(armature):
            self.report({'ERROR'}, t("Tools.apply_transforms.invalid_armature"))
            return {'CANCELLED'}

        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')

        armature.select_set(True)
        context.view_layer.objects.active = armature

        meshes = get_all_meshes(context)
        for mesh in meshes:
            mesh.select_set(True)

        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        self.report({'INFO'}, t("Tools.apply_transforms.success"))
        return {'FINISHED'}
