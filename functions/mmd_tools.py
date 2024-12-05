import bpy
import numpy as np
from typing import Set, Dict, List, Optional, Tuple
from bpy.types import Operator, Context, Object, EditBone, Mesh
from ..core.logging_setup import logger
from ..core.translations import t
from ..core.common import (
    get_active_armature,
    validate_armature,
    get_all_meshes,
    ProgressTracker,
    transfer_vertex_weights,
    remove_unused_shapekeys
)
from ..core.dictionaries import bone_names, mmd_bone_renames

class AvatarToolkit_OT_FixBoneNames(Operator):
    """Standardize and fix bone names"""
    bl_idname = "avatar_toolkit.fix_bone_names"
    bl_label = t("MMDTools.fix_bone_names")
    bl_description = t("MMDTools.fix_bone_names_desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        armature = get_active_armature(context)
        if not armature:
            return False
        valid, _ = validate_armature(armature)
        return valid

    def execute(self, context: Context) -> Set[str]:
        armature = get_active_armature(context)
        
        with ProgressTracker(context, 3, "Fixing Bone Names") as progress:
            bpy.ops.object.mode_set(mode='EDIT')
            
            # First pass - standardize names
            for bone in armature.data.edit_bones:
                bone.name = self.standardize_bone_name(bone.name)
            progress.step("Standardized names")

            # Second pass - apply MMD mappings
            for bone in armature.data.edit_bones:
                if bone.name in mmd_bone_renames:
                    bone.name = mmd_bone_renames[bone.name]
            progress.step("Applied MMD mappings")

            # Third pass - fix common names
            for bone in armature.data.edit_bones:
                self.fix_common_names(bone)
            progress.step("Fixed common names")

        self.report({'INFO'}, t("MMDTools.bones_renamed"))
        return {'FINISHED'}

    def standardize_bone_name(self, name: str) -> str:
        """Standardize bone naming convention"""
        prefixes = ['def-', 'def_', 'sk_', 'b_', 'bone_', 'mmd_']
        name_lower = name.lower()
        
        # Remove common prefixes
        for prefix in prefixes:
            if name_lower.startswith(prefix):
                name = name[len(prefix):]
                break
                
        # Fix side indicators
        name = name.replace('_l', '_L').replace('_r', '_R')
        name = name.replace('.l', '_L').replace('.r', '_R')
        name = name.replace('左', '_L').replace('右', '_R')
        
        return name

    def fix_common_names(self, bone: EditBone) -> None:
        """Fix common bone names to standard names"""
        for standard_name, variations in bone_names.items():
            if bone.name.lower() in variations:
                bone.name = standard_name
                break

class AvatarToolkit_OT_FixBoneHierarchy(Operator):
    """Fix bone parenting and hierarchy"""
    bl_idname = "avatar_toolkit.fix_bone_hierarchy"
    bl_label = t("MMDTools.fix_hierarchy")
    bl_description = t("MMDTools.fix_hierarchy_desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        armature = get_active_armature(context)
        if not armature:
            return False
        valid, _ = validate_armature(armature)
        return valid

    def execute(self, context: Context) -> Set[str]:
        armature = get_active_armature(context)
        
        with ProgressTracker(context, 3, "Fixing Bone Hierarchy") as progress:
            bpy.ops.object.mode_set(mode='EDIT')
            
            # Fix spine chain
            self.fix_spine_chain(armature)
            progress.step("Fixed spine chain")
            
            # Fix limb chains
            self.fix_limb_chains(armature)
            progress.step("Fixed limb chains")
            
            # Fix bone orientations
            self.fix_bone_orientations(armature)
            progress.step("Fixed bone orientations")

        self.report({'INFO'}, t("MMDTools.hierarchy_fixed"))
        return {'FINISHED'}

    def fix_spine_chain(self, armature: Object) -> None:
        """Fix the spine bone chain hierarchy"""
        edit_bones = armature.data.edit_bones
        spine_chain = ['Hips', 'Spine', 'Chest', 'Neck', 'Head']
        previous = None
        
        for bone_name in spine_chain:
            if bone_name in edit_bones:
                bone = edit_bones[bone_name]
                if previous:
                    bone.parent = edit_bones[previous]
                previous = bone_name

    def fix_limb_chains(self, armature: Object) -> None:
        """Fix arm and leg bone chains"""
        edit_bones = armature.data.edit_bones
        limb_chains = {
            'Left': {
                'arm': ['Left shoulder', 'Left arm', 'Left elbow', 'Left wrist'],
                'leg': ['Left leg', 'Left knee', 'Left ankle', 'Left toe']
            },
            'Right': {
                'arm': ['Right shoulder', 'Right arm', 'Right elbow', 'Right wrist'],
                'leg': ['Right leg', 'Right knee', 'Right ankle', 'Right toe']
            }
        }
        
        for side in limb_chains:
            for chain in limb_chains[side].values():
                previous = None
                for bone_name in chain:
                    if bone_name in edit_bones:
                        bone = edit_bones[bone_name]
                        if previous:
                            bone.parent = edit_bones[previous]
                        previous = bone_name

    def fix_bone_orientations(self, armature: Object) -> None:
        """Fix bone roll and axis orientations"""
        edit_bones = armature.data.edit_bones
        
        # Fix spine chain orientations
        spine_bones = ['Hips', 'Spine', 'Chest']
        for name in spine_bones:
            if name in edit_bones:
                bone = edit_bones[name]
                bone.roll = 0
                bone.tail.y = bone.head.y
                
        # Fix arm orientations
        arm_bones = ['Left arm', 'Right arm', 'Left elbow', 'Right elbow']
        for name in arm_bones:
            if name in edit_bones:
                bone = edit_bones[name]
                bone.roll = 0 if 'Left' in name else np.pi

class AvatarToolkit_OT_FixBoneWeights(Operator):
    """Fix and clean up bone weights"""
    bl_idname = "avatar_toolkit.fix_bone_weights"
    bl_label = t("MMDTools.fix_weights")
    bl_description = t("MMDTools.fix_weights_desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        armature = get_active_armature(context)
        if not armature:
            return False
        valid, _ = validate_armature(armature)
        return valid

    def execute(self, context: Context) -> Set[str]:
        armature = get_active_armature(context)
        meshes = get_all_meshes(context)
        
        if not meshes:
            self.report({'WARNING'}, t("MMDTools.no_meshes"))
            return {'CANCELLED'}
            
        with ProgressTracker(context, len(meshes), "Fixing Bone Weights") as progress:
            for mesh in meshes:
                # Clean weights
                self.clean_weights(mesh, context.scene.avatar_toolkit.clean_weights_threshold)
                
                # Handle twist bones
                if context.scene.avatar_toolkit.merge_twist_bones:
                    self.process_twist_bones(mesh)
                
                # Remove empty groups
                self.remove_empty_groups(mesh)
                
                # Normalize weights
                self.normalize_weights(mesh)
                
                progress.step(f"Processed {mesh.name}")

        self.report({'INFO'}, t("MMDTools.weights_fixed"))
        return {'FINISHED'}

    def clean_weights(self, mesh: Object, threshold: float) -> None:
        """Remove weights below threshold"""
        for vertex_group in mesh.vertex_groups:
            for vertex in mesh.data.vertices:
                try:
                    weight = vertex_group.weight(vertex.index)
                    if weight < threshold:
                        vertex_group.remove([vertex.index])
                except RuntimeError:
                    continue

    def process_twist_bones(self, mesh: Object) -> None:
        """Process and merge twist bone weights"""
        twist_groups = [g for g in mesh.vertex_groups if 'twist' in g.name.lower()]
        for group in twist_groups:
            base_name = group.name.lower().replace('twist', '').strip('_')
            for target in mesh.vertex_groups:
                if target.name.lower() == base_name:
                    transfer_vertex_weights(mesh, group.name, target.name)
                    break

    def remove_empty_groups(self, mesh: Object) -> None:
        """Remove vertex groups with no weights"""
        empty_groups = []
        for group in mesh.vertex_groups:
            has_weights = False
            for vert in mesh.data.vertices:
                for g in vert.groups:
                    if g.group == group.index and g.weight > 0:
                        has_weights = True
                        break
                if has_weights:
                    break
            if not has_weights:
                empty_groups.append(group)
                
        for group in empty_groups:
            mesh.vertex_groups.remove(group)

    def normalize_weights(self, mesh: Object) -> None:
        """Normalize vertex weights"""
        for vertex in mesh.data.vertices:
            total_weight = sum(group.weight for group in vertex.groups)
            if total_weight > 0:
                for group in vertex.groups:
                    group.weight /= total_weight

class AvatarToolkit_OT_FixMMDFeatures(Operator):
    """Fix MMD-specific features and settings"""
    bl_idname = "avatar_toolkit.fix_mmd_features"
    bl_label = t("MMDTools.fix_mmd_features")
    bl_description = t("MMDTools.fix_mmd_features_desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        armature = get_active_armature(context)
        if not armature:
            return False
        valid, _ = validate_armature(armature)
        return valid

    def execute(self, context: Context) -> Set[str]:
        armature = get_active_armature(context)
        meshes = get_all_meshes(context)
        
        with ProgressTracker(context, 4, "Fixing MMD Features") as progress:
            # Process shape keys
            for mesh in meshes:
                self.process_shape_keys(mesh)
            progress.step("Processed shape keys")
            
            # Fix MMD shading
            self.fix_mmd_shading(meshes)
            progress.step("Fixed MMD shading")
            
            # Handle physics cleanup
            self.cleanup_physics(armature)
            progress.step("Cleaned up physics")
            
            # Remove unused data
            self.cleanup_unused_data(context)
            progress.step("Cleaned up unused data")
            
        return {'FINISHED'}

    def process_shape_keys(self, mesh: Object) -> None:
        """Process and clean up shape keys"""
        if not mesh.data.shape_keys:
            return
            
        # Clean unused shape keys
        remove_unused_shapekeys(mesh)
        
        # Sort and rename shape keys
        shape_keys = mesh.data.shape_keys.key_blocks
        for key in shape_keys:
            # Handle Japanese prefixes
            if key.name.startswith('防'):
                key.name = key.name[1:]
            # Handle common MMD prefixes    
            if key.name.startswith('表情'):
                key.name = key.name[2:]

    def fix_mmd_shading(self, meshes: List[Object]) -> None:
        """Fix MMD material shading settings"""
        for mesh in meshes:
            for material in mesh.data.materials:
                if material:
                    material.use_backface_culling = True
                    material.blend_method = 'HASHED'
                    if material.node_tree:
                        for node in material.node_tree.nodes:
                            if node.type == 'BSDF_PRINCIPLED':
                                node.inputs['Alpha'].default_value = 1.0

    def cleanup_physics(self, armature: Object) -> None:
        """Clean up MMD physics objects"""
        physics_objects = [obj for obj in bpy.data.objects 
                         if obj.parent == armature and 
                         (obj.rigid_body or obj.rigid_body_constraint)]
        
        for obj in physics_objects:
            bpy.data.objects.remove(obj, do_unlink=True)

    def cleanup_unused_data(self, context: Context) -> None:
        """Clean up unused MMD data"""
        # Remove unused actions
        for action in bpy.data.actions:
            if not action.users:
                bpy.data.actions.remove(action)
                
        # Remove empty vertex groups
        for mesh in get_all_meshes(context):
            self.remove_empty_groups(mesh)

    def remove_empty_groups(self, mesh: Object) -> None:
        """Remove empty vertex groups"""
        empty_groups = []
        for group in mesh.vertex_groups:
            has_weights = False
            for vert in mesh.data.vertices:
                for g in vert.groups:
                    if g.group == group.index and g.weight > 0:
                        has_weights = True
                        break
                if has_weights:
                    break
            if not has_weights:
                empty_groups.append(group)
                
        for group in empty_groups:
            mesh.vertex_groups.remove(group)

class AvatarToolkit_OT_AdvancedBoneOps(Operator):
    """Advanced bone operations and fixes"""
    bl_idname = "avatar_toolkit.advanced_bone_ops"
    bl_label = t("MMDTools.advanced_bone_ops")
    bl_description = t("MMDTools.advanced_bone_ops_desc")
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context: Context) -> Set[str]:
        armature = get_active_armature(context)
        
        with ProgressTracker(context, 4, "Advanced Bone Operations") as progress:
            # Fix zero length bones
            self.fix_zero_length_bones(armature)
            progress.step("Fixed zero length bones")
            
            # Connect bones with children
            self.connect_bone_chains(armature)
            progress.step("Connected bone chains")
            
            # Handle bone roll values
            self.fix_bone_rolls(armature)
            progress.step("Fixed bone rolls")
            
            # Fix bone orientations
            self.fix_bone_orientations(armature)
            progress.step("Fixed bone orientations")
            
        return {'FINISHED'}

    def fix_zero_length_bones(self, armature: Object) -> None:
        """Fix bones with zero length by extending them"""
        min_length = 0.001
        for bone in armature.data.edit_bones:
            length = (bone.tail - bone.head).length
            if length < min_length:
                if bone.parent:
                    bone.tail = bone.head + bone.parent.vector * 0.1
                else:
                    bone.tail.z = bone.head.z + 0.1

    def connect_bone_chains(self, armature: Object) -> None:
        """Connect bones that should form chains"""
        min_distance = bpy.context.scene.avatar_toolkit.connect_bones_min_distance
        
        for bone in armature.data.edit_bones:
            if len(bone.children) == 1:
                child = bone.children[0]
                distance = (bone.tail - child.head).length
                if distance < min_distance:
                    child.use_connect = True
                    child.head = bone.tail

    def fix_bone_rolls(self, armature: Object) -> None:
        """Fix bone roll values for proper orientation"""
        for bone in armature.data.edit_bones:
            if 'spine' in bone.name.lower() or 'chest' in bone.name.lower():
                bone.roll = 0
            elif 'shoulder' in bone.name.lower():
                bone.roll = 0 if 'left' in bone.name.lower() else np.pi

class AvatarToolkit_OT_CleanupOperations(Operator):
    """Cleanup unused data and objects"""
    bl_idname = "avatar_toolkit.cleanup_operations"
    bl_label = t("MMDTools.cleanup_operations")
    bl_description = t("MMDTools.cleanup_operations_desc")
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context: Context) -> Set[str]:
        armature = get_active_armature(context)
        
        with ProgressTracker(context, 4, "Cleanup Operations") as progress:
            # Remove rigidbodies and joints
            self.remove_physics_objects(armature)
            progress.step("Removed physics objects")
            
            # Clear unused animation data
            self.clear_unused_animations(armature)
            progress.step("Cleared unused animations")
            
            # Remove empty objects
            self.remove_empty_objects()
            progress.step("Removed empty objects")
            
            # Clean up collections
            self.cleanup_collections(armature)
            progress.step("Cleaned up collections")
            
        return {'FINISHED'}

    def remove_physics_objects(self, armature: Object) -> None:
        """Remove all physics objects and constraints"""
        physics_objects = [obj for obj in bpy.data.objects 
                         if obj.parent == armature and 
                         (obj.rigid_body or obj.rigid_body_constraint)]
        
        for obj in physics_objects:
            bpy.data.objects.remove(obj, do_unlink=True)

    def clear_unused_animations(self, armature: Object) -> None:
        """Remove unused animation data"""
        if armature.animation_data:
            if armature.animation_data.action and armature.animation_data.action.users == 0:
                bpy.data.actions.remove(armature.animation_data.action)
            
            # Clear unused NLA tracks
            if armature.animation_data.nla_tracks:
                for track in armature.animation_data.nla_tracks:
                    if not track.strips:
                        armature.animation_data.nla_tracks.remove(track)

    def remove_empty_objects(self) -> None:
        """Remove empty objects from the scene"""
        empty_objects = [obj for obj in bpy.data.objects 
                        if obj.type == 'EMPTY' and not obj.children]
        
        for obj in empty_objects:
            bpy.data.objects.remove(obj, do_unlink=True)

    def cleanup_collections(self, armature: Object) -> None:
        """Clean up and organize collections"""
        # Remove empty collections
        for collection in bpy.data.collections:
            if not collection.objects and not collection.children:
                bpy.data.collections.remove(collection)
                
        # Ensure armature is in main collection
        if armature.users_collection[0] != bpy.context.scene.collection:
            bpy.context.scene.collection.objects.link(armature)