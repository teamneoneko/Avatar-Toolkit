import bpy
import math
from typing import Set, List
from bpy.types import Operator, Context, Armature, EditBone
from ...core.translations import t
from ...core.logging_setup import logger
from ...core.common import get_active_armature, get_all_meshes, get_vertex_weights, transfer_vertex_weights, validate_armature

class AvatarToolkit_OT_ConnectBones(Operator):
    """Connect disconnected bones in chain"""
    bl_idname = "avatar_toolkit.connect_bones"
    bl_label = t("Tools.connect_bones")
    bl_description = t("Tools.connect_bones_desc")
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context: Context) -> bool:
        armature = get_active_armature(context)
        if not armature:
            return False
        is_valid, _ = validate_armature(armature)
        return is_valid
        
    def execute(self, context: Context) -> Set[str]:
        try:
            armature = get_active_armature(context)
            logger.info("Starting bone connection operation")
            
            bpy.ops.object.mode_set(mode='EDIT')
            edit_bones = armature.data.edit_bones
            bones_connected = 0
            min_distance = context.scene.avatar_toolkit.connect_bones_min_distance
            
            excluded_bones = {'LeftEye', 'RightEye', 'Head', 'Hips'}
            
            for bone in edit_bones:
                if len(bone.children) == 1 and bone.name not in excluded_bones:
                    child = bone.children[0]
                    distance = math.dist(bone.tail, child.head)
                    
                    if distance > min_distance:
                        logger.debug(f"Connecting bone {bone.name} to {child.name}")
                        bone.tail = child.head
                        if bone.parent and len(bone.parent.children) == 1:
                            bone.use_connect = True
                        bones_connected += 1
                        
            bpy.ops.object.mode_set(mode='OBJECT')
            self.report({'INFO'}, t("Tools.connect_bones_success", count=bones_connected))
            return {'FINISHED'}
            
        except Exception as e:
            logger.error(f"Failed to connect bones: {str(e)}")
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

class AvatarToolkit_OT_MergeToActive(Operator):
    """Merge selected bones into active bone and transfer weights"""
    bl_idname = "avatar_toolkit.merge_to_active"
    bl_label = t("Tools.merge_to_active")
    bl_description = t("Tools.merge_to_active_desc")
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context: Context) -> bool:
        armature = get_active_armature(context)
        if not armature:
            return False
        return context.mode == 'EDIT_ARMATURE' and context.active_bone
        
    def execute(self, context: Context) -> Set[str]:
        try:
            armature = get_active_armature(context)
            active_bone = context.active_bone
            selected_bones = [b for b in context.selected_editable_bones if b != active_bone]
            
            if not selected_bones:
                self.report({'WARNING'}, t("Tools.no_bones_selected"))
                return {'CANCELLED'}
                
            logger.info(f"Merging {len(selected_bones)} bones into {active_bone.name}")
            
            # Store weights before merging
            meshes = get_all_meshes(context)
            weight_data = {}
            for bone in selected_bones:
                for mesh in meshes:
                    if bone.name in mesh.vertex_groups:
                        weights = get_vertex_weights(mesh, bone.name)
                        weight_data.setdefault(mesh.name, {})[bone.name] = weights
            
            # Transfer weights to active bone
            threshold = context.scene.avatar_toolkit.merge_weights_threshold
            for mesh_name, bone_weights in weight_data.items():
                mesh = bpy.data.objects[mesh_name]
                for bone_name, weights in bone_weights.items():
                    transfer_vertex_weights(mesh, bone_name, active_bone.name, threshold)
            
            # Delete merged bones
            for bone in selected_bones:
                armature.data.edit_bones.remove(bone)
            
            self.report({'INFO'}, t("Tools.merge_to_active_success", count=len(selected_bones)))
            return {'FINISHED'}
            
        except Exception as e:
            logger.error(f"Failed to merge bones: {str(e)}")
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

class AvatarToolkit_OT_MergeToParent(Operator):
    """Merge selected bones into their respective parents and transfer weights"""
    bl_idname = "avatar_toolkit.merge_to_parent"
    bl_label = t("Tools.merge_to_parent")
    bl_description = t("Tools.merge_to_parent_desc")
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context: Context) -> bool:
        armature = get_active_armature(context)
        if not armature:
            return False
        return context.mode == 'EDIT_ARMATURE'
        
    def execute(self, context: Context) -> Set[str]:
        try:
            armature = get_active_armature(context)
            selected_bones = [b for b in context.selected_editable_bones if b.parent]
            
            if not selected_bones:
                self.report({'WARNING'}, t("Tools.no_bones_with_parent"))
                return {'CANCELLED'}
                
            logger.info(f"Merging {len(selected_bones)} bones to their parents")
            
            # Store weights before merging
            meshes = get_all_meshes(context)
            merged_count = 0
            threshold = context.scene.avatar_toolkit.merge_weights_threshold
            
            for bone in selected_bones:
                parent = bone.parent
                if not parent:
                    continue
                    
                # Transfer weights to parent
                for mesh in meshes:
                    if bone.name in mesh.vertex_groups:
                        transfer_vertex_weights(mesh, bone.name, parent.name, threshold)
                
                # Delete merged bone
                armature.data.edit_bones.remove(bone)
                merged_count += 1
            
            self.report({'INFO'}, t("Tools.merge_to_parent_success", count=merged_count))
            return {'FINISHED'}
            
        except Exception as e:
            logger.error(f"Failed to merge bones: {str(e)}")
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
