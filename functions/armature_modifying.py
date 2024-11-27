import bpy
from ..core.register import register_wrap
from bpy.types import Context, Mesh, Panel, Operator, Armature, EditBone
from ..functions.translations import t
from ..core.common import get_selected_armature, get_all_meshes
from ..core import common
from ..core.dictionaries import bone_names
from mathutils import Matrix

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
        armature = common.get_selected_armature(context)
        return armature and context.mode == 'POSE'
        
    def execute(self, context):
        armature_obj = common.get_selected_armature(context)
        mesh_objects = common.get_all_meshes(context)

        for mesh_obj in mesh_objects:
            if not mesh_obj.data:
                continue

            # Ensure basis exists
            if not mesh_obj.data.shape_keys:
                mesh_obj.shape_key_add(name='Basis')
                
            # Store current pose as new shapekey
            new_shape = mesh_obj.shape_key_add(name='Pose_Shapekey', from_mix=False)
            
            # Evaluate mesh in current pose
            depsgraph = context.evaluated_depsgraph_get()
            eval_mesh = mesh_obj.evaluated_get(depsgraph)
            
            # Apply evaluated vertices to new shapekey
            for i, v in enumerate(eval_mesh.data.vertices):
                new_shape.data[i].co = v.co.copy()

        # Reset pose
        bpy.ops.pose.select_all(action='SELECT')
        bpy.ops.pose.transforms_clear()
        bpy.ops.object.mode_set(mode='OBJECT')

        self.report({'INFO'}, t('Tools.apply_pose_as_rest.success'))
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
        if not common.apply_pose_as_rest(armature_obj=get_selected_armature(context),
                                    meshes=get_all_meshes(context), 
                                    context=context):
            self.report({'ERROR'}, t("Quick_Access.apply_armature_failed"))
            return {'CANCELLED'}
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

        # Store initial transforms
        initial_transforms = {}
        bpy.ops.object.mode_set(mode='EDIT')
        for bone in armature.data.edit_bones:
            initial_transforms[bone.name] = {
                'head': bone.head.copy(),
                'tail': bone.tail.copy(),
                'roll': bone.roll,
                'matrix': bone.matrix.copy(),
                'parent': bone.parent.name if bone.parent else None
            }

        # Get weighted bones
        armature.select_set(True)
        context.view_layer.objects.active = armature

        meshes = common.get_all_meshes(context)
        for mesh in meshes:
            mesh_data: Mesh = mesh.data
            for vertex in mesh_data.vertices:
                for group in vertex.groups:
                    if group.weight > self.threshold: 
                        weighted_bones.append(mesh.vertex_groups[group.group].name)
        
        bpy.ops.object.mode_set(mode='EDIT')
        amature_data: Armature = armature.data
        unweighted_bones: list[str] = []

        # Identify unweighted bones
        for bone in amature_data.edit_bones:
            if bone.name not in weighted_bones:
                unweighted_bones.append(bone.name)

        # Process bone removal while preserving positions
        for bone_name in unweighted_bones:
            bone = amature_data.edit_bones[bone_name]
            
            # Store children data
            children = bone.children
            children_data = {}
            for child in children:
                children_data[child.name] = initial_transforms[child.name]
            
            # Reparent children
            for child in children:
                child.use_connect = False
                if bone.parent:
                    child.parent = bone.parent
            
            # Remove bone
            amature_data.edit_bones.remove(bone)
            
            # Restore children positions
            for child_name, data in children_data.items():
                if child_name in amature_data.edit_bones:
                    child = amature_data.edit_bones[child_name]
                    child.head = data['head']
                    child.tail = data['tail']
                    child.roll = data['roll']
                    child.matrix = data['matrix']

        # Final position verification
        for bone_name, transform in initial_transforms.items():
            if bone_name in amature_data.edit_bones:
                bone = amature_data.edit_bones[bone_name]
                bone.matrix = transform['matrix']

        bpy.ops.object.mode_set(mode='OBJECT')
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

    delete_old: bpy.props.BoolProperty(
        name=t("Tools.merge_bones_to_parents.delete_old.label"),
        description=t("Tools.merge_bones_to_parents.delete_old.desc"),
        default=False
    )

    @classmethod
    def poll(cls, context: Context) -> bool:
        armature = common.get_selected_armature(context)
        if armature and armature == context.view_layer.objects.active:
            if context.mode == "POSE":
                return len(context.selected_pose_bones) > 0
            elif context.mode == "EDIT_ARMATURE":
                return len(context.selected_editable_bones) > 0
        return False

    def execute(self, context: Context) -> set[str]:
        prev_mode = context.mode

        # Map 'EDIT_ARMATURE' to 'EDIT' for bpy.ops.object.mode_set
        if prev_mode == 'EDIT_ARMATURE':
            prev_mode = 'EDIT'

        # Switch to Edit Mode
        bpy.ops.object.mode_set(mode='EDIT')
        armature_data: Armature = context.view_layer.objects.active.data

        # Get selected bones in Edit Mode
        selected_bones = context.selected_editable_bones
        selected_bone_names = [bone.name for bone in selected_bones]

        if not selected_bone_names:
            self.report({'ERROR'}, t("No bones selected"))
            return {'CANCELLED'}

        for obj in common.get_all_meshes(context):
            for bone_name in selected_bone_names:
                bone = armature_data.edit_bones.get(bone_name)
                if bone and bone.parent:
                    # Transfer weights from bone to its parent
                    common.transfer_vertex_weights(
                        context=context,
                        obj=obj,
                        source_group=bone_name,
                        target_group=bone.parent.name
                    )
                    # Ensure we're in Edit Mode after transfer
                    bpy.ops.object.mode_set(mode='EDIT')
                else:
                    self.report({'WARNING'}, f"Bone '{bone_name}' has no parent or not found; skipping")

        # Optionally delete old bones
        if self.delete_old:
            for bone_name in selected_bone_names:
                bone = armature_data.edit_bones.get(bone_name)
                if bone:
                    # Reassign children to the parent of the bone being deleted
                    for child in bone.children:
                        child.parent = bone.parent
                    # Remove the bone
                    armature_data.edit_bones.remove(bone)
                else:
                    self.report({'WARNING'}, f"Bone '{bone_name}' not found in armature; cannot delete")

        # Return to previous mode
        bpy.ops.object.mode_set(mode=prev_mode)
        return {'FINISHED'}

@register_wrap
class AvatarToolkit_OT_MergeArmatures(Operator):
    bl_idname = "avatar_toolkit.merge_armatures"
    bl_label = t("MergeArmature.merge_armatures.label")
    bl_description = t("MergeArmature.merge_armatures.desc").format(selected_armature_label=t("MergeArmatures.selected_armature.label"))
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (common.get_selected_armature(context) is not None) and (common.get_merge_armature_source(context) is not None)

    def make_active(self, obj: bpy.types.Object, context: Context):
        context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        context.view_layer.objects.active = obj
        obj.select_set(True)

    def execute(cls, context: Context) -> set[str]:
        source_armature: bpy.types.Object = bpy.data.objects[context.scene.merge_armature_source]
        source_armature_data: Armature = source_armature.data
        target_armature: bpy.types.Object = common.get_selected_armature(context)
        target_armature_data: Armature = target_armature.data
        parent_dictionary: dict[str, list[str]] = {}

        cls.make_active(obj=source_armature, context=context)
        
        

        if context.scene.merge_armature_apply_transforms:
            target_armature.select_set(True)
            for obj in target_armature.children:
                obj.select_set(True)
            for obj in source_armature.children:
                obj.select_set(True)
            bpy.ops.object.transform_apply()

        
        if context.scene.merge_armature_align_bones:
            if not context.scene.merge_armature_apply_transforms:
                source_armature.matrix_world = target_armature.matrix_world

            def children_bone_recursive(parent_bone) -> list[bpy.types.PoseBone]:
                child_bones = []
                child_bones.append(parent_bone)
                for child in parent_bone.children:
                    child_bones.extend(children_bone_recursive(child))
                return child_bones
            bpy.ops.object.mode_set(mode='POSE')
            source_armature_bone_names = [j.name for j in children_bone_recursive(
                source_armature.pose.bones[
                    next(bone.name for bone in source_armature.pose.bones if common.simplify_bonename(bone.name) in bone_names['hips']) #Find bone that matches dictionary for hips before continuing.
                    ]
                    )] #bones are default in order of parent child.

            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            context.view_layer.objects.active = target_armature
            bpy.ops.object.mode_set(mode='EDIT')
            for source_bone_name in source_armature_bone_names:
                
                if source_bone_name in target_armature_data.edit_bones:
                    obj = source_armature
                    editbone = target_armature_data.edit_bones[source_bone_name]
                    bone = obj.pose.bones[source_bone_name]
                    bone.matrix = editbone.matrix
                else:
                    continue
            if not common.apply_pose_as_rest(armature_obj=source_armature,meshes=[i for i in source_armature.children if i.type == 'MESH'], context=context):
                cls.report({'ERROR'}, t("Quick_Access.apply_armature_failed"))
                return {'FINISHED'}
        
        



        cls.make_active(obj=source_armature, context=context)
        bpy.ops.object.mode_set(mode='EDIT')
        source_armature_data: Armature = source_armature.data
        for bone_name in [i.name for i in source_armature_data.edit_bones]:
            if bone_name in target_armature_data.bones:
                parent_dictionary[bone_name] = [i.name for i in source_armature_data.edit_bones[bone_name].children]
                source_armature_data.edit_bones.remove(source_armature_data.edit_bones[bone_name])
        bpy.ops.object.mode_set(mode='OBJECT')

        cls.make_active(obj=target_armature, context=context)
        source_armature.select_set(True)

        bpy.ops.object.join()
        target_armature: bpy.types.Object = common.get_selected_armature(context)
        cls.make_active(obj=target_armature, context=context)
        bpy.ops.object.mode_set(mode='EDIT')
        for bone_name, bone_name_list in parent_dictionary.items():
            if bone_name in target_armature_data.edit_bones:
                for bone_child in bone_name_list:
                    target_armature_data.edit_bones[bone_child].parent = target_armature_data.edit_bones[bone_name]
        bpy.ops.object.mode_set(mode='OBJECT')
        


        return {'FINISHED'}
