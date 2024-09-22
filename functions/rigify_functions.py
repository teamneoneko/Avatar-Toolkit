# This code is heavily based on the Rigify-Move-DEF by NyankoNyan (https://github.com/NyankoNyan/Rigify-Move-DEF), which is licensed under the MIT License. We just heavily improve the code and add some new features.

import bpy
from ..core.register import register_wrap
from ..core.common import get_selected_armature, is_valid_armature
from ..functions.translations import t
from bpy.types import Operator, Context

import bpy
from ..core.register import register_wrap
from ..core.common import get_selected_armature, is_valid_armature
from ..functions.translations import t
from bpy.types import Operator, Context

@register_wrap
class AvatarToolKit_OT_ConvertRigifyToUnity(Operator):
    bl_idname = "avatar_toolkit.convert_rigify_to_unity"
    bl_label = t("Tools.convert_rigify_to_unity.label")
    bl_description = t("Tools.convert_rigify_to_unity.desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        armature = get_selected_armature(context)
        return armature is not None and is_valid_armature(armature) and "DEF-spine" in armature.data.bones

    def execute(self, context: Context) -> set[str]:
        armature = get_selected_armature(context)
        if not armature:
            self.report({'ERROR'}, t("Tools.no_armature_selected"))
            return {'CANCELLED'}

        self.move_def_bones(armature)
        self.rename_bones_for_unity(armature)
        if context.scene.merge_twist_bones:
            self.handle_twist_bones(armature)
        self.report({'INFO'}, t("Tools.convert_rigify_to_unity.success"))
        return {'FINISHED'}

    def move_def_bones(self, armature):
        remap = self.get_org_remap(armature)
        remap.update(self.get_special_remap())

        remove_bones_in_chain = [
            'DEF-upper_arm.L.001', 'DEF-forearm.L.001',
            'DEF-upper_arm.R.001', 'DEF-forearm.R.001',
            'DEF-thigh.L.001', 'DEF-shin.L.001',
            'DEF-thigh.R.001', 'DEF-shin.R.001'
        ]

        transform_copies = self.get_transform_copies(armature)

        # Add missing constraints
        bpy.ops.object.mode_set(mode='POSE')
        for bone_name in transform_copies:
            bone = armature.pose.bones[bone_name]
            org_name = 'ORG-' + self.get_proto_name(bone_name)
            if org_name in armature.pose.bones:
                constraint = bone.constraints.new('COPY_TRANSFORMS')
                constraint.target = armature
                constraint.subtarget = org_name
                constr_count = len(bone.constraints)
                if constr_count > 1:
                    bone.constraints.move(constr_count-1, 0)

        # Apply new parents
        bpy.ops.object.mode_set(mode='EDIT')
        for remap_key in remap:
            if remap_key in armature.data.edit_bones and remap[remap_key] in armature.data.edit_bones:
                armature.data.edit_bones[remap_key].parent = armature.data.edit_bones[remap[remap_key]]

        # Remove extra bones in chains
        bpy.ops.object.mode_set(mode='OBJECT')
        for bone_name in remove_bones_in_chain:
            if bone_name in armature.data.bones:
                armature.data.bones[bone_name].use_deform = False

        bpy.ops.object.mode_set(mode='EDIT')
        for bone_name in remove_bones_in_chain:
            if bone_name in armature.data.bones:
                remove_bone = armature.data.edit_bones[bone_name]
                parent_bone = remove_bone.parent
                parent_bone.tail = remove_bone.tail
                retarget_bones = list(remove_bone.children)
                for bone in retarget_bones:
                    bone.parent = parent_bone
                armature.data.edit_bones.remove(remove_bone)

    def rename_bones_for_unity(self, armature):
        unity_bone_names = {
            "DEF-spine": "Hips",
            "DEF-spine.001": "Spine",
            "DEF-spine.002": "Chest",
            "DEF-spine.003": "UpperChest",
            "DEF-neck": "Neck",
            "DEF-head": "Head",
            "DEF-shoulder.L": "LeftShoulder",
            "DEF-upper_arm.L": "LeftUpperArm",
            "DEF-forearm.L": "LeftLowerArm",
            "DEF-hand.L": "LeftHand",
            "DEF-shoulder.R": "RightShoulder",
            "DEF-upper_arm.R": "RightUpperArm",
            "DEF-forearm.R": "RightLowerArm",
            "DEF-hand.R": "RightHand",
            "DEF-thigh.L": "LeftUpperLeg",
            "DEF-shin.L": "LeftLowerLeg",
            "DEF-foot.L": "LeftFoot",
            "DEF-toe.L": "LeftToes",
            "DEF-thigh.R": "RightUpperLeg",
            "DEF-shin.R": "RightLowerLeg",
            "DEF-foot.R": "RightFoot",
            "DEF-toe.R": "RightToes"
        }

        for old_name, new_name in unity_bone_names.items():
            bone = armature.pose.bones.get(old_name)
            if bone:
                bone.name = new_name

    def handle_twist_bones(self, armature):
        twist_bones = [
            ("DEF-upper_arm_twist.L", "DEF-upper_arm.L"),
            ("DEF-upper_arm_twist.R", "DEF-upper_arm.R"),
            ("DEF-forearm_twist.L", "DEF-forearm.L"),
            ("DEF-forearm_twist.R", "DEF-forearm.R"),
            ("DEF-thigh_twist.L", "DEF-thigh.L"),
            ("DEF-thigh_twist.R", "DEF-thigh.R")
        ]

        bpy.ops.object.mode_set(mode='EDIT')
        for twist_bone, parent_bone in twist_bones:
            if twist_bone in armature.data.edit_bones and parent_bone in armature.data.edit_bones:
                twist = armature.data.edit_bones[twist_bone]
                parent = armature.data.edit_bones[parent_bone]
                parent.tail = twist.tail
                for child in twist.children:
                    child.parent = parent
                armature.data.edit_bones.remove(twist)

        bpy.ops.object.mode_set(mode='OBJECT')

    def get_org_remap(self, armature):
        remap = {}
        for bone in armature.data.bones:
            if self.is_def_bone(bone.name):
                name = self.get_proto_name(bone.name)
                parent = bone.parent
                while parent:
                    parent_name = self.get_proto_name(parent.name)
                    if parent_name != name:
                        if ('DEF-' + parent_name) in armature.data.bones:
                            remap[bone.name] = 'DEF-' + parent_name
                            break
                    parent = parent.parent
        return remap

    def get_special_remap(self):
        return {
            'DEF-thigh.L': 'DEF-pelvis.L',
            'DEF-thigh.R': 'DEF-pelvis.R',
            'DEF-upper_arm.L': 'DEF-shoulder.L',
            'DEF-upper_arm.R': 'DEF-shoulder.R',
        }

    def get_transform_copies(self, armature):
        result = []
        for bone in armature.pose.bones:
            if self.is_def_bone(bone.name) and not self.has_transform_copies(bone):
                result.append(bone.name)
        return result

    def has_transform_copies(self, bone):
        return any(constraint.type == 'COPY_TRANSFORMS' for constraint in bone.constraints)

    def is_def_bone(self, bone_name):
        return bone_name.startswith('DEF-')

    def is_org_bone(self, bone_name):
        return bone_name.startswith('ORG-')

    def get_proto_name(self, bone_name):
        if self.is_def_bone(bone_name) or self.is_org_bone(bone_name):
            return bone_name[4:]
        return bone_name
