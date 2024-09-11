import bpy
from ..core import common
from bpy.types import Operator, Context, Mesh, Armature, EditBone
from ..core.register import register_wrap
from .translations import t

@register_wrap
class AvatarToolkit_OT_RemoveZeroWeightBones(Operator):
    bl_idname = "avatar_toolkit.remove_zero_weight_bones"
    bl_label = t("Tools.remove_zero_weight_bones.label")
    bl_description = t("Tools.remove_zero_weight_bones.desc")
    bl_options = {'REGISTER', 'UNDO'}

    threshold: bpy.props.FloatProperty(
        default=0.01,
        name=t("Tools.remove_zero_weight_bones.threshold.label"),
        description=t("Tools.remove_zero_weight_bones.threshold.desc"),
        min=0.0000001, 
        max=0.9999999)

    @classmethod
    def poll(cls, context: Context) -> bool:
        return common.get_selected_armature(context) is not None

    def execute(self, context: Context) -> set[str]:
        armature = common.get_selected_armature(context)
        if not common.is_valid_armature(armature):
            self.report({'ERROR'}, t("Tools.apply_transforms.invalid_armature"))
            return {'CANCELLED'}

        weighted_bones: list[str] = []


        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')

        armature.select_set(True)
        context.view_layer.objects.active = armature

        meshes = common.get_all_meshes(context)
        for mesh in meshes:
            mesh_data: Mesh = mesh.data
            for vertex in mesh_data.vertices:
                for group in vertex.groups:
                    if group.weight > self.threshold: 
                        weighted_bones.append(mesh.vertex_groups[group.group].name) #add bone name to list of bones that are greater than the weight threshold
        
        bpy.ops.object.mode_set(mode='EDIT')
        amature_data: Armature = armature.data
        unweighted_bones: list[str] = []

        #doing 2 loops to prevent modification of array during iteration
        for bone in amature_data.edit_bones:
            if bone.name not in weighted_bones:
                unweighted_bones.append(bone.name) #add bones that arent in the list of bones that have weight into the list of bones that don't

        for bone_name in unweighted_bones:
            for edit_bone in amature_data.edit_bones[bone_name].children: 
                edit_bone.use_connect = False #to fix randomly moving bones
                edit_bone.parent = amature_data.edit_bones[bone_name].parent #to fix unparented bones.
            amature_data.edit_bones.remove(amature_data.edit_bones[bone_name]) #delete list of unweighted bones from the armature

        self.report({'INFO'}, t("Tools.remove_zero_weight_bones.success"))
        return {'FINISHED'}

@register_wrap
class AvatarToolkit_OT_MergeBonesToActive(Operator):
    bl_idname = "avatar_toolkit.merge_bones_to_active"
    bl_label = t("Tools.merge_bones_to_active.label")
    bl_description = t("Tools.merge_bones_to_active.desc")
    bl_options = {'REGISTER', 'UNDO'}

    delete_old: bpy.props.BoolProperty(name=t("Tools.merge_bones_to_active.delete_old.label"), description=t("Tools.merge_bones_to_active.delete_old.desc"), default=False)

    @classmethod
    def poll(cls, context: Context) -> bool:
        if common.get_selected_armature(context) is not None:
            if common.get_selected_armature(context) == context.view_layer.objects.active:
                if context.mode == "POSE":
                    return len(context.selected_pose_bones) > 1
                elif context.mode == "EDIT_ARMATURE":
                    return len(context.selected_bones) > 1
        return False

    def execute(cls, context: Context) -> set[str]:
        
        prev_mode: str = "EDIT"
        if context.mode == "POSE":
            prev_mode = "POSE"

        #get active bone and a list of all other selected bones
        bpy.ops.object.mode_set(mode='EDIT')
        target_bone: str = context.active_bone.name

        armature_data: Armature = context.view_layer.objects.active.data


        bones: list[str] = [i.name for i in context.selected_bones]
        bones.remove(target_bone)

        for obj in common.get_all_meshes(context):
            for bone in bones:
                bone_name: str = armature_data.edit_bones[bone].name
                common.transfer_vertex_weights(context=context,obj=obj,source_group=bone_name,target_group=armature_data.edit_bones[target_bone].name)
                bpy.ops.object.mode_set(mode='EDIT')
        for bone in bones:   
            if cls.delete_old:
                for bone_child in armature_data.edit_bones[bone].children:
                    bone_child.parent = armature_data.edit_bones[bone].parent
                armature_data.edit_bones.remove(armature_data.edit_bones[bone])
        
        bpy.ops.object.mode_set(mode=prev_mode)
        return {'FINISHED'}
    
@register_wrap
class AvatarToolkit_OT_MergeBonesToParents(Operator):
    bl_idname = "avatar_toolkit.merge_bones_to_parents"
    bl_label = t("Tools.merge_bones_to_parents.label")
    bl_description = t("Tools.merge_bones_to_parents.desc")
    bl_options = {'REGISTER', 'UNDO'}

    delete_old: bpy.props.BoolProperty(name=t("Tools.merge_bones_to_parents.delete_old.label"), description=t("Tools.merge_bones_to_parents.delete_old.desc"), default=False)

    @classmethod
    def poll(cls, context: Context) -> bool:
        if common.get_selected_armature(context) is not None:
            if common.get_selected_armature(context) == context.view_layer.objects.active:
                if context.mode == "POSE":
                    return len(context.selected_pose_bones) > 0
                elif context.mode == "EDIT_ARMATURE":
                    return len(context.selected_bones) > 0
        return False

    def execute(cls, context: Context) -> set[str]:

        prev_mode: str = "EDIT"
        if context.mode == "POSE":
            prev_mode = "POSE"
        #get active bone and a list of all other selected bones
        bpy.ops.object.mode_set(mode='EDIT')
        armature_data: Armature = context.view_layer.objects.active.data

        for obj in common.get_all_meshes(context):
            for bone in [i.name for i in context.selected_bones]:
                if armature_data.edit_bones[bone].parent != None:
                    bone_name: str = armature_data.edit_bones[bone].name
                    common.transfer_vertex_weights(context=context,obj=obj,source_group=bone_name,target_group=armature_data.edit_bones[bone].parent.name)
                    bpy.ops.object.mode_set(mode='EDIT')
        
        for bone in [i.name for i in context.selected_bones]:   
            if cls.delete_old:
                for bone_child in armature_data.edit_bones[bone].children:
                    bone_child.parent = armature_data.edit_bones[bone].parent
                armature_data.edit_bones.remove(armature_data.edit_bones[bone])
        
        
        bpy.ops.object.mode_set(mode=prev_mode)
        return {'FINISHED'}