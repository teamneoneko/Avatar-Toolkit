import bpy
import math
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
    
@register_wrap
class AvatarToolKit_OT_ConnectBones(Operator):
    bl_idname = "avatar_toolkit.connect_bones"
    bl_label = t("Tools.connect_bones.label")
    bl_description = t("Tools.connect_bones.desc")
    bl_options = {'REGISTER', 'UNDO'}

    min_distance: bpy.props.FloatProperty(
        name=t("Tools.connect_bones.min_distance.label"),
        description=t("Tools.connect_bones.min_distance.desc"),
        default=0.005,
        min=0.001,
        max=0.1
    )

    @classmethod
    def poll(cls, context: Context) -> bool:
        return get_selected_armature(context) is not None

    def execute(self, context: Context) -> set[str]:
        armature = get_selected_armature(context)
        if not is_valid_armature(armature):
            self.report({'ERROR'}, t("Tools.connect_bones.invalid_armature"))
            return {'CANCELLED'}

        bpy.ops.object.mode_set(mode='EDIT')
        
        edit_bones = armature.data.edit_bones
        bones_connected = 0

        for bone in edit_bones:
            if len(bone.children) == 1 and bone.name not in ['LeftEye', 'RightEye', 'Head', 'Hips']:
                child = bone.children[0]
                distance = math.dist(bone.head, child.head)

                if distance > self.min_distance:
                    bone.tail = child.head
                    if bone.parent and len(bone.parent.children) == 1:
                        bone.use_connect = True
                    bones_connected += 1

        bpy.ops.object.mode_set(mode='OBJECT')

        self.report({'INFO'}, t("Tools.connect_bones.success").format(bones_connected=bones_connected))
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "min_distance")

@register_wrap
class AvatarToolKit_OT_DeleteBoneConstraints(Operator):
    bl_idname = "avatar_toolkit.delete_bone_constraints"
    bl_label = t("Tools.delete_bone_constraints.label")
    bl_description = t("Tools.delete_bone_constraints.desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return get_selected_armature(context) is not None

    def execute(self, context: Context) -> set[str]:
        armature = get_selected_armature(context)
        if not is_valid_armature(armature):
            self.report({'ERROR'}, t("Tools.delete_bone_constraints.invalid_armature"))
            return {'CANCELLED'}

        bpy.ops.object.mode_set(mode='POSE')
        
        constraints_removed = 0
        for bone in armature.pose.bones:
            while bone.constraints:
                bone.constraints.remove(bone.constraints[0])
                constraints_removed += 1

        bpy.ops.object.mode_set(mode='OBJECT')

        self.report({'INFO'}, t("Tools.delete_bone_constraints.success").format(constraints_removed=constraints_removed))
        return {'FINISHED'}
