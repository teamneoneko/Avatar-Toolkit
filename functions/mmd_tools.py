import bpy
from mathutils import Vector
from typing import Dict, List, Tuple, Set, Optional
from bpy.types import Object, Armature, EditBone, Bone, Operator, Context
from ..core.logging_setup import logger
from ..core.common import (
    ProgressTracker, 
    get_active_armature,
    validate_armature,
    get_vertex_weights,
    transfer_vertex_weights
)
from ..core.translations import t
from ..core.dictionaries import bone_names

class AVATAR_TOOLKIT_OT_StandardizeMmd(Operator):
    """MMD Bone standardization system"""
    bl_idname = "avatar_toolkit.standardize_mmd"
    bl_label = t("MMD.standardize")
    bl_options = {'REGISTER', 'UNDO'}
    
    def __init__(self):
        self.bone_mapping: Dict[str, str] = {}
        self.processed_bones: Set[str] = set()
        
    def execute(self, context: Context) -> Set[str]:
        self.armature = get_active_armature(context)
        
        if not self.armature:
            self.report({'ERROR'}, t("MMD.no_armature"))
            return {'CANCELLED'}
            
        try:
            with ProgressTracker(context, 5, "MMD Standardization") as progress:
                # Step 1: Process bone names
                self.process_bone_names(context)
                progress.step("Processed bone names")
                
                # Step 2: Fix bone structure
                self.fix_bone_structure(context)
                progress.step("Fixed bone structure")
                
                # Step 3: Process weights
                self.process_weights(context)
                progress.step("Processed weights")
                
                # Step 4: Clean up
                self.cleanup_armature(context)
                progress.step("Cleaned up armature")
                
                # Step 5: Final validation
                self.validate_results(context)
                progress.step("Validated results")
                
            self.report({'INFO'}, t("MMD.standardization_complete"))
            return {'FINISHED'}
            
        except Exception as e:
            logger.error(f"MMD Standardization failed: {str(e)}")
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        
    def standardize_armature(self) -> Tuple[bool, str]:
        """Main standardization process"""
        if not self.armature:
            return False, t("MMD.no_armature")
            
        try:
            with ProgressTracker(self.context, 5, "MMD Standardization") as progress:
                # Step 1: Process bone names
                self.process_bone_names()
                progress.step("Processed bone names")
                
                # Step 2: Fix bone structure
                self.fix_bone_structure()
                progress.step("Fixed bone structure")
                
                # Step 3: Process weights
                self.process_weights()
                progress.step("Processed weights")
                
                # Step 4: Clean up
                self.cleanup_armature()
                progress.step("Cleaned up armature")
                
                # Step 5: Final validation
                self.validate_results()
                progress.step("Validated results")
                
            return True, t("MMD.standardization_complete")
            
        except Exception as e:
            logger.error(f"MMD Standardization failed: {str(e)}")
            return False, str(e)
    
    def process_bone_names(self, context: Context) -> None:
        """Process and standardize bone names"""
        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.armature.data.edit_bones
        
        for bone in edit_bones:
            new_name = self.standardize_bone_name(bone.name)
            if new_name != bone.name:
                self.bone_mapping[bone.name] = new_name
                bone.name = new_name
                
    def translate_japanese_bone_name(self, name: str) -> str:
        """Translate Japanese bone names to English standardized names"""
        from ..core.dictionaries import bone_names
        
        # Convert to lowercase for matching
        name_lower = name.lower()
        
        # Check each bone category for Japanese character matches
        for bone_category, variations in bone_names.items():
            for variation in variations:
                if variation in name_lower:
                    # If Japanese characters are found, return the standardized name
                    return bone_category
                    
        # If no match found, return original name
        return name

    def standardize_bone_name(self, name: str) -> str:
        """Standardize individual bone names"""
        # First translate Japanese names
        result = self.translate_japanese_bone_name(name)
        
        # Remove common prefixes
        prefixes = ['ValveBiped_', 'Bip01_', 'MMD_', 'Armature|']
        for prefix in prefixes:
            if result.lower().startswith(prefix.lower()):
                result = result[len(prefix):]
        
        # Handle left/right conventions
        if result.endswith('_L') or result.endswith('.L'):
            result = f"{result[:-2]}.L"
        elif result.endswith('_R') or result.endswith('.R'):
            result = f"{result[:-2]}.R"
        
        return result
    
    def fix_bone_structure(self, context: Context) -> None:
        """Fix bone hierarchy and orientations"""
        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.armature.data.edit_bones
        
        # Process spine hierarchy
        self.process_spine_chain(context)
        
        # Fix bone orientations
        self.fix_bone_orientations(context)
        
        # Connect appropriate bones
        self.connect_bones(context)
    
    def process_weights(self, context: Context) -> None:
        """Process and clean up vertex weights"""
        for mesh in self.get_associated_meshes(context):
            # Transfer weights based on bone mapping
            for old_name, new_name in self.bone_mapping.items():
                if old_name != new_name:
                    transfer_vertex_weights(mesh, old_name, new_name)
            
            # Clean up zero weights
            self.cleanup_vertex_groups(mesh, context)
    
    def cleanup_armature(self, context: Context) -> None:
        """Perform final cleanup operations"""
        # Remove unused bones
        self.remove_unused_bones(context)
        
        # Clean up constraints
        self.cleanup_constraints(context)
        
        # Fix zero-length bones
        self.fix_zero_length_bones(context)
    
    def get_associated_meshes(self, context: Context) -> List[Object]:
        """Get all mesh objects associated with the armature"""
        return [obj for obj in bpy.data.objects 
                if obj.type == 'MESH' 
                and obj.parent == self.armature]
                
    def process_spine_chain(self, context: Context) -> None:
        """Process and fix spine bone chain hierarchy"""
        edit_bones = self.armature.data.edit_bones
        spine_bones = {
            'hips': None,
            'spine': None,
            'chest': None,
            'upper_chest': None,
            'neck': None,
            'head': None
        }
        
        # Find spine bones using bone_names dictionary
        for bone in edit_bones:
            for spine_part, _ in spine_bones.items():
                if any(alt_name in bone.name.lower() for alt_name in bone_names[spine_part]):
                    spine_bones[spine_part] = bone
                    break
        
        # Set up spine hierarchy
        hierarchy = [
            ('hips', 'spine'),
            ('spine', 'chest'),
            ('chest', 'neck'),
            ('neck', 'head')
        ]
        
        for parent_name, child_name in hierarchy:
            parent = spine_bones.get(parent_name)
            child = spine_bones.get(child_name)
            if parent and child:
                child.parent = parent
                child.use_connect = True

    def fix_bone_orientations(self, context: Context) -> None:
        """Fix bone orientations for standard pose compatibility"""
        edit_bones = self.armature.data.edit_bones
        
        # Process arm bones
        arm_pairs = [
            ('upper_arm', 'forearm'),
            ('forearm', 'hand')
        ]
        
        for side in ['.L', '.R']:
            for parent, child in arm_pairs:
                parent_bone = next((b for b in edit_bones if b.name.lower().startswith(parent) and b.name.endswith(side)), None)
                child_bone = next((b for b in edit_bones if b.name.lower().startswith(child) and b.name.endswith(side)), None)
                
                if parent_bone and child_bone:
                    child_bone.use_connect = True
                    child_bone.use_inherit_rotation = True
        
        # Process leg bones
        leg_pairs = [
            ('thigh', 'shin'),
            ('shin', 'foot')
        ]
        
        for side in ['.L', '.R']:
            for parent, child in leg_pairs:
                parent_bone = next((b for b in edit_bones if b.name.lower().startswith(parent) and b.name.endswith(side)), None)
                child_bone = next((b for b in edit_bones if b.name.lower().startswith(child) and b.name.endswith(side)), None)
                
                if parent_bone and child_bone:
                    child_bone.use_connect = True
                    child_bone.use_inherit_rotation = True

    def remove_unused_bones(self, context: Context) -> None:
        """Remove unused and unnecessary bones from the armature"""
        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.armature.data.edit_bones
        
        # Get list of bones that have vertex weights
        used_bones = set()
        for mesh in self.get_associated_meshes(context):
            for group in mesh.vertex_groups:
                used_bones.add(group.name)
        
        # Get list of bones to keep based on settings
        toolkit = context.scene.avatar_toolkit
        keep_upper_chest = toolkit.keep_upper_chest
        keep_twist = toolkit.keep_twist_bones
        
        # Remove unused bones
        for bone in edit_bones:
            # Skip if bone has weights
            if bone.name in used_bones:
                continue
                
            # Skip if bone is upper chest and we want to keep it
            if 'upper_chest' in bone.name.lower() and keep_upper_chest:
                continue
                
            # Skip if bone is twist bone and we want to keep them
            if 'twist' in bone.name.lower() and keep_twist:
                continue
                
            # Remove the bone
            edit_bones.remove(bone)

    def connect_bones(self, context: Context) -> None:
        """Connect bones that should be connected in the hierarchy"""
        edit_bones = self.armature.data.edit_bones
        
        connect_chains = [
            ['hips', 'spine', 'chest', 'neck', 'head'],
            ['shoulder.L', 'upper_arm.L', 'forearm.L', 'hand.L'],
            ['shoulder.R', 'upper_arm.R', 'forearm.R', 'hand.R'],
            ['thigh.L', 'shin.L', 'foot.L', 'toe.L'],
            ['thigh.R', 'shin.R', 'foot.R', 'toe.R']
        ]
        
        for chain in connect_chains:
            prev_bone = None
            for bone_name in chain:
                bone = next((b for b in edit_bones if b.name.lower().endswith(bone_name.lower())), None)
                if bone and prev_bone:
                    bone.parent = prev_bone
                    bone.use_connect = True
                prev_bone = bone

    def cleanup_vertex_groups(self, mesh_obj: Object, context: Context) -> None:
        """Clean up vertex groups by removing zero weights and merging similar groups"""
        threshold = context.scene.avatar_toolkit.merge_weights_threshold
        
        # Get list of vertex groups
        vertex_groups = mesh_obj.vertex_groups
        
        # Track groups to remove
        groups_to_remove = set()
        
        # Check each vertex group
        for group in vertex_groups:
            weights = get_vertex_weights(mesh_obj, group.name)
            
            # If no weights above threshold, mark for removal
            if not any(weight > threshold for weight in weights.values()):
                groups_to_remove.add(group.name)
        
        # Remove empty groups
        for group_name in groups_to_remove:
            group = vertex_groups.get(group_name)
            if group:
                vertex_groups.remove(group)

    def validate_results(self, context: Context) -> None:
        """Validate the results of standardization"""
        valid, messages = validate_armature(self.armature)
        if not valid:
            raise ValueError("\n".join(messages))
        
    def cleanup_constraints(self, context: Context) -> None:
        """Clean up and fix bone constraints"""
        bpy.ops.object.mode_set(mode='POSE')
        
        # Process each pose bone
        for pose_bone in self.armature.pose.bones:
            constraints_to_remove = []
            
            for constraint in pose_bone.constraints:
                should_remove = False
                
                # Handle IK constraints
                if constraint.type == 'IK':
                    if not constraint.target or constraint.target != self.armature:
                        should_remove = True
                    elif not constraint.subtarget or constraint.subtarget not in self.armature.data.bones:
                        should_remove = True
                
                # Handle MMD additional rotation constraints
                elif constraint.name == 'mmd_additional_rotation':
                    if not constraint.target or constraint.target != self.armature:
                        should_remove = True
                    elif not constraint.subtarget or constraint.subtarget not in self.armature.data.bones:
                        should_remove = True
                
                # Handle transformation constraints
                elif constraint.type in {'COPY_ROTATION', 'COPY_LOCATION', 'COPY_TRANSFORMS'}:
                    if not constraint.target or constraint.target != self.armature:
                        should_remove = True
                    elif not constraint.subtarget or constraint.subtarget not in self.armature.data.bones:
                        should_remove = True
                
                if should_remove:
                    constraints_to_remove.append(constraint)
            
            # Remove invalid constraints
            for constraint in constraints_to_remove:
                pose_bone.constraints.remove(constraint)

    def fix_zero_length_bones(self, context: Context) -> None:
        """Fix zero-length bones by setting minimal length"""
        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.armature.data.edit_bones
        
        min_length = 0.01  # Minimum bone length in Blender units
        
        for bone in edit_bones:
            # Calculate bone length
            bone_length = (bone.tail - bone.head).length
            
            if bone_length < min_length:
                # Set minimal length while preserving direction
                if bone.parent:
                    # Use parent's orientation as reference
                    direction = bone.parent.tail - bone.parent.head
                    direction.normalize()
                else:
                    # Default to Z-axis if no parent
                    direction = mathutils.Vector((0, 0, 1))
                
                bone.tail = bone.head + (direction * min_length)

class FixUnmovableBonesOperator(bpy.types.Operator):
    bl_idname = "avatar_toolkit.fix_unmovable_bones"
    bl_label = t("MMD.fix_unmovable_bones")
    bl_description = t("MMD.fix_unmovable_bones_desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        armature = get_active_armature(context)
        return armature is not None and armature.type == 'ARMATURE'

    def execute(self, context):
        armature = get_active_armature(context)
        if not armature:
            self.report({'ERROR'}, t("MMD.no_armature"))
            return {'CANCELLED'}

        try:
            with ProgressTracker(context, 2, "Unlocking Transforms") as progress:
                # Unlock armature transforms
                progress.step("Unlocking armature transforms")
                for attr in ('location', 'rotation', 'scale'):
                    for i in range(3):
                        setattr(armature, f"lock_{attr}", [False] * 3)

                # Unlock bone transforms
                progress.step("Unlocking bone transforms")
                for bone in armature.pose.bones:
                    for attr in ('location', 'rotation', 'scale'):
                        setattr(bone, f"lock_{attr}", [False] * 3)

            self.report({'INFO'}, t("MMD.transforms_unlocked"))
            return {'FINISHED'}

        except Exception as e:
            logger.error(f"Error unlocking transforms: {str(e)}")
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

class ReparentMeshesOperator(bpy.types.Operator):
    bl_idname = "avatar_toolkit.reparent_meshes"
    bl_label = t("MMD.reparent_meshes")
    bl_description = t("MMD.reparent_meshes_desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        armature = get_active_armature(context)
        return armature is not None and get_all_meshes(context)

    def execute(self, context):
        armature = get_active_armature(context)
        if not armature:
            self.report({'ERROR'}, t("MMD.no_armature"))
            return {'CANCELLED'}

        meshes = get_all_meshes(context)
        if not meshes:
            self.report({'ERROR'}, t("MMD.no_meshes"))
            return {'CANCELLED'}

        try:
            with ProgressTracker(context, len(meshes) + 1, "Reparenting Meshes") as progress:
                # Get or create main collection
                main_collection = self._get_main_collection(context)
                progress.step("Setting up collections")

                # Process each mesh
                for mesh in meshes:
                    progress.step(f"Processing {mesh.name}")
                    self._process_mesh(mesh, armature, main_collection)

            self.report({'INFO'}, t("MMD.reparenting_complete"))
            return {'FINISHED'}

        except Exception as e:
            logger.error(f"Error reparenting meshes: {str(e)}")
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

    def _get_main_collection(self, context) -> bpy.types.Collection:
        """Get or create the main collection for the armature"""
        if hasattr(context.scene, 'collection'):
            return context.scene.collection
        return context.scene.collection

    def _process_mesh(self, mesh: bpy.types.Object, 
                     armature: bpy.types.Object,
                     main_collection: bpy.types.Collection) -> None:
        """Process individual mesh parenting and collection management"""
        # Unlink from other collections
        for col in mesh.users_collection:
            if col != main_collection:
                col.objects.unlink(mesh)

        # Ensure mesh is in main collection
        if mesh.name not in main_collection.objects:
            main_collection.objects.link(mesh)

        # Set parent to armature
        mesh.parent = armature
        if not mesh.parent_type == 'ARMATURE':
            mesh.parent_type = 'ARMATURE'