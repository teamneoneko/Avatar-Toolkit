import bpy
from ..core.register import register_wrap
from bpy.types import Context, Mesh, Panel, Operator, Armature, EditBone
from ..functions.translations import t
from ..core.common import get_selected_armature, get_all_meshes
from ..core import common

@register_wrap
class AvatarToolkit_OT_StartPoseMode(Operator):
    bl_idname = 'avatar_toolkit.start_pose_mode'
    bl_label = t("Quick_Access.start_pose_mode.label")
    bl_description = t("Quick_Access.start_pose_mode.desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return get_selected_armature(context) != None and context.mode != "POSE"
    
    def execute(self, context: Context) -> set[str]:
        
        #give an active object so the next line doesn't throw an error.
        context.view_layer.objects.active = get_selected_armature(context)

        bpy.ops.object.mode_set(mode='OBJECT')

        #deselect everything and select just our armature, then go into pose on just our selected armature. - @989onan
        bpy.ops.object.select_all(action='DESELECT')
        context.view_layer.objects.active = get_selected_armature(context)
        context.view_layer.objects.active.select_set(True)
        bpy.ops.object.mode_set(mode='POSE')

        return {'FINISHED'}

@register_wrap
class AvatarToolkit_OT_StopPoseMode(Operator):
    bl_idname = 'avatar_toolkit.stop_pose_mode'
    bl_label = t("Quick_Access.stop_pose_mode.label")
    bl_description = t("Quick_Access.stop_pose_mode.desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return get_selected_armature(context) != None and context.mode == "POSE"
    
    def execute(self, context: Context) -> set[str]:
        #this is done so that transforms are cleared but user selection is respected. - @989onan
        bpy.ops.pose.transforms_clear()
        bpy.ops.pose.select_all(action="INVERT")
        bpy.ops.pose.transforms_clear()
        bpy.ops.pose.select_all(action="INVERT")

        bpy.ops.object.mode_set(mode='OBJECT')

        return {'FINISHED'}

@register_wrap
class AvatarToolkit_OT_ApplyPoseAsShapekey(Operator):
    bl_idname = 'avatar_toolkit.apply_pose_as_shapekey'
    bl_label = t("Quick_Access.apply_pose_as_shapekey.label")
    bl_description = t("Quick_Access.apply_pose_as_shapekey.desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return get_selected_armature(context) != None and context.mode == "POSE"
    
    def execute(self, context: Context):
        bpy.ops.object.mode_set(mode="OBJECT")
        for obj in get_all_meshes(context):

            modifier_armature_name: str = ""
            context.view_layer.objects.active = obj
                    
            bpy.ops.object.mode_set(mode="OBJECT")
            bpy.ops.object.select_all(action="DESELECT")
            context.view_layer.objects.active = obj
            obj.select_set(True)
            for modifier in obj.modifiers:
                if modifier.type == "ARMATURE":
                    arm_modifier: bpy.types.ArmatureModifier = modifier
                    modifier_armature_name = arm_modifier.object.name
            bpy.ops.object.modifier_apply_as_shapekey(modifier=modifier_armature_name,keep_modifier=True,report=True)
        
        return {'FINISHED'}

@register_wrap
class AvatarToolkit_OT_ApplyPoseAsRest(Operator):
    bl_idname = 'avatar_toolkit.apply_pose_as_rest'
    bl_label = t("Quick_Access.apply_pose_as_rest.label")
    bl_description = t("Quick_Access.apply_pose_as_rest.desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return get_selected_armature(context) != None and context.mode == "POSE"
    
    def execute(self, context: Context):
        for obj in get_all_meshes(context):
            mesh_data: Mesh = obj.data



            if mesh_data.shape_keys:
                shape_key_obj_list: list[bpy.types.Object] = []
                modifier_armature_name: str = ""

                for modifier in obj.modifiers:
                    if modifier.type == "ARMATURE":
                        arm_modifier: bpy.types.ArmatureModifier = modifier
                        modifier_armature_name = arm_modifier.object.name
                for idx,shape in enumerate(mesh_data.shape_keys.key_blocks):
                    if idx == 0:
                        continue
                    context.view_layer.objects.active = obj
                    
                    bpy.ops.object.mode_set(mode="OBJECT")
                    bpy.ops.object.select_all(action="DESELECT")
                    context.view_layer.objects.active = obj
                    obj.select_set(True)

                    #create duplicate of object
                    bpy.ops.object.duplicate()

                    shape_obj = context.view_layer.objects.active

                    #make current shapekey a separate object
                    shape_obj.active_shape_key_index = idx
                    shape_obj.name = shape.name
                    
                    bpy.ops.object.shape_key_move(type="TOP")

                    bpy.ops.object.mode_set(mode="EDIT")
                    bpy.ops.object.mode_set(mode="OBJECT")

                    bpy.ops.object.shape_key_remove(all=True)

                    bpy.ops.object.modifier_apply(modifier=modifier_armature_name)

                    #for modifier_name in [i.name for i in shape_obj.modifiers]:
                    #    bpy.ops.object.modifier_remove(modifier=modifier_name)

                    shape_key_obj_list.append(shape_obj) #add to a list of shape key objects
                context.view_layer.objects.active = obj
                    
                bpy.ops.object.mode_set(mode="OBJECT")
                context.view_layer.objects.active.select_set(True)
                bpy.ops.object.shape_key_remove(all=True)
                bpy.ops.object.modifier_apply(modifier=modifier_armature_name)
                bpy.ops.object.select_all(action="DESELECT")

                for shapekey_obj in shape_key_obj_list:
                    shapekey_obj.select_set(True)
                context.view_layer.objects.active = obj
                context.view_layer.objects.active.select_set(True)

                try:
                    bpy.ops.object.join_shapes()
                except:
                    self.report({'ERROR'}, t("Quick_Access.apply_armature_failed"))
                    #delete shapekey objects to not leave ourselves in a bad exit state - @989onan
                    context.view_layer.objects.active = shape_key_obj_list[0]
                    obj.select_set(False)
                    bpy.ops.object.delete(confirm=False)
                    return {'CANCELLED'}
                context.view_layer.objects.active = shape_key_obj_list[0]
                obj.select_set(False)
                bpy.ops.object.delete(confirm=False)
            else:
                modifier_armature_name: str = ""

                for modifier in obj.modifiers:
                    if modifier.type == "ARMATURE":
                        arm_modifier: bpy.types.ArmatureModifier = modifier
                        modifier_armature_name = arm_modifier.object.name
                context.view_layer.objects.active = obj
                bpy.ops.object.mode_set(mode="OBJECT")
                bpy.ops.object.select_all(action="DESELECT")
                context.view_layer.objects.active.select_set(True)
                bpy.ops.object.modifier_apply(modifier=modifier_armature_name)

            armature_obj: bpy.types.Object = get_selected_armature(context)
            
            context.view_layer.objects.active = armature_obj
            armature_obj.select_set(True)
            bpy.ops.object.mode_set(mode="OBJECT")
            bpy.ops.object.mode_set(mode="POSE")

            bpy.ops.pose.armature_apply(selected=False)

        return {'FINISHED'}

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
