import bpy
from typing import Tuple, Set, Dict
from bpy.types import Operator, Context, Object
from mathutils import Vector
from ..core.common import (
    ProgressTracker, 
    get_active_armature,
    validate_meshes,
    simplify_bonename,
    duplicate_bone_chain,
    save_armature_state,
    restore_armature_state,
    get_all_meshes,
    validate_bone_hierarchy,
    transfer_vertex_weights,
    get_vertex_weights
)
from ..core.logging_setup import logger
from ..core.translations import t
from ..core.dictionaries import bone_names

class AvatarToolkit_OT_StandardizeMMDBones(Operator):
    bl_idname = "avatar_toolkit.mmd_standardize_bones"
    bl_label = t("MMD.standardize_bones")
    bl_options = {'REGISTER', 'UNDO'}

    def standardize_bone_names(self, armature: Object) -> None:
        """Standardize bone names using MMD to Unity/VRChat conventions"""
        for bone in armature.data.bones:
            simplified_name = simplify_bonename(bone.name)
            for standard_name, variations in bone_names.items():
                if simplified_name in variations:
                    bone.name = standard_name
                    break

    def process_lr_bones(self, armature: Object) -> None:
        """Process left/right bone pairs for consistency"""
        for bone in armature.data.bones:
            if bone.name.endswith(('_l', '_r', '.l', '.r', 'Left', 'Right')):
                base_name = bone.name.rsplit('_', 1)[0]
                side = '_l' if any(s in bone.name.lower() for s in ('left', '_l', '.l')) else '_r'
                bone.name = f"{base_name}{side}"

    def resolve_name_conflicts(self, armature: Object) -> None:
        """Handle duplicate bone names"""
        used_names = set()
        for bone in armature.data.bones:
            base_name = bone.name
            counter = 1
            while bone.name in used_names:
                bone.name = f"{base_name}_{counter}"
                counter += 1
            used_names.add(bone.name)

    def process_spine_chain(self, armature: Object) -> None:
        """Process spine bones for VRChat compatibility"""
        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = armature.data.edit_bones
        
        spine_bones = {
            'hips': None,
            'spine': None,
            'chest': None,
            'upper_chest': None,
            'neck': None,
            'head': None
        }
        
        # Map existing spine bones
        for bone in edit_bones:
            simplified = simplify_bonename(bone.name)
            for spine_name in spine_bones.keys():
                if simplified in bone_names[spine_name]:
                    spine_bones[spine_name] = bone
                    break
        
        # Create missing spine bones
        if spine_bones['spine'] and not spine_bones['chest']:
            chest = edit_bones.new('chest')
            chest.head = spine_bones['spine'].tail
            chest.tail = spine_bones['neck'].head if spine_bones['neck'] else spine_bones['head'].head
            spine_bones['chest'] = chest
        
        # Set up spine hierarchy
        if spine_bones['hips']:
            for i, key in enumerate(['spine', 'chest', 'upper_chest', 'neck', 'head']):
                if spine_bones[key]:
                    prev_key = list(spine_bones.keys())[i]
                    if spine_bones[prev_key]:
                        spine_bones[key].parent = spine_bones[prev_key]

    def correct_bone_orientations(self, armature: Object) -> None:
        """Automatically correct bone orientations to align with Unity's axes"""
        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = armature.data.edit_bones
        
        # Define standard orientations
        orientations = {
            'spine': Vector((0, 0, 1)),    # Points up
            'chest': Vector((0, 0, 1)),
            'neck': Vector((0, 0, 1)),
            'head': Vector((0, 0, 1)),
            'shoulder': Vector((1, 0, 0)),  # Points outward
            'arm': Vector((0, -1, 0)),     # Points down
            'elbow': Vector((0, -1, 0)),
            'leg': Vector((0, -1, 0)),
            'knee': Vector((0, -1, 0)),
            'foot': Vector((1, 0, 0)),     # Points forward
        }
        
        for bone in edit_bones:
            simplified_name = simplify_bonename(bone.name)
            for bone_type, direction in orientations.items():
                if bone_type in simplified_name:
                    # Calculate new tail position while maintaining length
                    length = (bone.tail - bone.head).length
                    bone.tail = bone.head + direction * length
                    break

    @classmethod
    def poll(cls, context: Context) -> bool:
        """Check if there is an active armature in the scene"""
        return get_active_armature(context) is not None

    def execute(self, context: Context) -> Set[str]:
        try:
            armature = get_active_armature(context)
            
            # Save initial state if enabled
            if context.scene.avatar_toolkit.save_backup_state:
                self.initial_state = save_armature_state(armature)
            
            with ProgressTracker(context, 6, "Standardizing Bones") as progress:
                # Step 1: Standardize bone names
                self.standardize_bone_names(armature)
                progress.step("Standardized bone names")
                
                # Step 3: Process left/right bones
                self.process_lr_bones(armature)
                progress.step("Processed left/right bones")
                
                # Step 4: Handle name conflicts
                self.resolve_name_conflicts(armature)
                progress.step("Resolved naming conflicts")
                
                # Step 5: Process spine chain
                self.process_spine_chain(armature)
                progress.step("Processed spine chain")
                
                # Step 6: Correct bone orientations
                self.correct_bone_orientations(armature)
                progress.step("Corrected bone orientations")

            self.report({'INFO'}, t("MMD.bones_standardized"))
            return {'FINISHED'}
            
        except Exception as e:
            logger.error(f"Bone standardization failed: {str(e)}")
            if hasattr(self, 'initial_state'):
                restore_armature_state(armature, self.initial_state)
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

class AvatarToolkit_OT_ProcessMMDWeights(Operator):
    bl_idname = "avatar_toolkit.mmd_process_weights"
    bl_label = t("MMD.process_weights")
    bl_options = {'REGISTER', 'UNDO'}

    def merge_bone_weights(self, context: Context, mesh: Object, source: str, target: str) -> None:
        """Transfer weights from source bone to target bone"""
        transfer_vertex_weights(
            mesh, 
            source, 
            target, 
            context.scene.avatar_toolkit.merge_weights_threshold
        )

    def process_eye_weights(self, context: Context, mesh: Object) -> None:
        """Handle special cases for eye bone weights"""
        eye_bones = {
            'eye_l': ['eyel', 'lefteye', 'eye.l'],
            'eye_r': ['eyer', 'righteye', 'eye.r']
        }
        
        for target, sources in eye_bones.items():
            for source in sources:
                if source in mesh.vertex_groups:
                    self.merge_bone_weights(context, mesh, source, target)

    def process_twist_bones(self, context: Context, mesh: Object) -> None:
        """Process and merge twist bone weights"""
        if not context.scene.avatar_toolkit.mmd_process_twist_bones:
            return
            
        twist_pairs = [
            ('arm_twist_l', 'left_arm'),
            ('arm_twist_r', 'right_arm'),
            ('forearm_twist_l', 'left_elbow'),
            ('forearm_twist_r', 'right_elbow')
        ]
        
        for twist, target in twist_pairs:
            if twist in mesh.vertex_groups:
                self.merge_bone_weights(context, mesh, twist, target)

    def cleanup_vertex_groups(self, context: Context, mesh: Object) -> None:
        """Remove empty and unused vertex groups"""
        threshold = context.scene.avatar_toolkit.clean_weights_threshold
        
        # Get list of used bones from armature
        armature = mesh.find_armature()
        if not armature:
            return
            
        valid_bones = set(bone.name for bone in armature.data.bones)
        
        # Remove unused groups
        for group in mesh.vertex_groups[:]:
            if group.name not in valid_bones:
                mesh.vertex_groups.remove(group)
                continue
                
            # Check if group has any weights above threshold
            has_weights = False
            for vert in mesh.data.vertices:
                for group_element in vert.groups:
                    if group_element.group == group.index:
                        if group_element.weight > threshold:
                            has_weights = True
                            break
                if has_weights:
                    break
                    
            if not has_weights:
                mesh.vertex_groups.remove(group)

    def merge_remaining_weights(self, context: Context, mesh: Object) -> None:
        """Process remaining weight merging cases"""
        # Common MMD weight merge pairs
        merge_pairs = [
            # Finger weights
            ('pinky', 'pinkie'),
            ('thumb0', 'thumb_0'),
            ('index0', 'index_0'),
            ('middle0', 'middle_0'),
            ('ring0', 'ring_0'),
            
            # Additional arm weights
            ('upperarm', 'arm'),
            ('lowerarm', 'elbow'),
            ('wrist', 'hand'),
            
            # Leg weights
            ('upperleg', 'leg'),
            ('lowerleg', 'knee'),
            ('ankle', 'foot'),
            
            # Spine weights
            ('spine1', 'chest'),
            ('spine2', 'upper_chest'),
        ]
        
        for source, target in merge_pairs:
            for suffix in ['_l', '_r', '.l', '.r']:
                source_name = f"{source}{suffix}"
                target_name = f"{target}{suffix}"
                if source_name in mesh.vertex_groups:
                    self.merge_bone_weights(context, mesh, source_name, target_name)

    @classmethod
    def poll(cls, context: Context) -> bool:
        """Check if there is an active armature in the scene"""
        return get_active_armature(context) is not None

    def execute(self, context: Context) -> Set[str]:
        try:
            meshes = get_all_meshes(context)
            
            # Save initial state
            if context.scene.avatar_toolkit.save_backup_state:
                self.initial_states = {mesh: get_vertex_weights(mesh) for mesh in meshes}
            
            with ProgressTracker(context, len(meshes) * 4, "Processing Weights") as progress:
                for mesh in meshes:
                    # Step 1: Process eye weights
                    self.process_eye_weights(context, mesh)
                    progress.step(f"Processed eye weights for {mesh.name}")
                    
                    # Step 2: Process twist bones
                    self.process_twist_bones(context, mesh)
                    progress.step(f"Processed twist bones for {mesh.name}")
                    
                    # Step 3: Merge remaining weights
                    self.merge_remaining_weights(context, mesh)
                    progress.step(f"Merged weights for {mesh.name}")
                    
                    # Step 4: Cleanup
                    self.cleanup_vertex_groups(context, mesh)
                    progress.step(f"Cleaned up weights for {mesh.name}")

            self.report({'INFO'}, t("MMD.weights_processed"))
            return {'FINISHED'}
            
        except Exception as e:
            logger.error(f"Weight processing failed: {str(e)}")
            if hasattr(self, 'initial_states'):
                for mesh, state in self.initial_states.items():
                    restore_mesh_weights_state(mesh, state)
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

class AvatarToolkit_OT_FixMMDHierarchy(Operator):
    bl_idname = "avatar_toolkit.mmd_fix_hierarchy"
    bl_label = t("MMD.fix_hierarchy")
    bl_options = {'REGISTER', 'UNDO'}

    def fix_bone_parenting(self, armature: Object) -> None:
        """Fix bone parenting to match standard hierarchy"""
        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = armature.data.edit_bones
        
        # Define parent-child relationships
        hierarchy_map = {
            'hips': ['spine', 'left_leg', 'right_leg'],
            'spine': ['chest'],
            'chest': ['upper_chest', 'left_shoulder', 'right_shoulder'],
            'upper_chest': ['neck'],
            'neck': ['head'],
            'head': ['left_eye', 'right_eye'],
            'left_shoulder': ['left_arm'],
            'right_shoulder': ['right_arm'],
            'left_arm': ['left_elbow'],
            'right_arm': ['right_elbow'],
            'left_elbow': ['left_wrist'],
            'right_elbow': ['right_wrist'],
            'left_leg': ['left_knee'],
            'right_leg': ['right_knee'],
            'left_knee': ['left_ankle'],
            'right_knee': ['right_ankle'],
            'left_ankle': ['left_toe'],
            'right_ankle': ['right_toe']
        }
        
        # Apply parenting
        for parent_name, children in hierarchy_map.items():
            parent_bone = None
            for bone in edit_bones:
                if simplify_bonename(bone.name) in bone_names[parent_name]:
                    parent_bone = bone
                    break
                    
            if parent_bone:
                for child_name in children:
                    for bone in edit_bones:
                        if simplify_bonename(bone.name) in bone_names[child_name]:
                            bone.parent = parent_bone

    def connect_bones(self, context: Context, armature: Object) -> None:
        """Connect bones to their children where appropriate"""
        if not context.scene.avatar_toolkit.mmd_connect_bones:
            return
            
        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = armature.data.edit_bones
        min_distance = context.scene.avatar_toolkit.connect_bones_min_distance
        
        for bone in edit_bones:
            if bone.children:
                for child in bone.children:
                    # Check if bones are close enough to connect
                    distance = (bone.tail - child.head).length
                    if distance < min_distance:
                        bone.tail = child.head
                        child.use_connect = True

    def validate_hierarchy(self, armature: Object) -> bool:
        """Validate final bone hierarchy"""
        # Check essential parent-child relationships
        essential_pairs = [
            ('spine', 'hips'),
            ('chest', 'spine'),
            ('neck', 'chest'),
            ('head', 'neck')
        ]
        
        for child, parent in essential_pairs:
            if not validate_bone_hierarchy(armature.data.bones, parent, child):
                return False
                
        return True

    def execute(self, context: Context) -> Set[str]:
        try:
            armature = get_active_armature(context)
            
            # Save initial state
            if context.scene.avatar_toolkit.save_backup_state:
                self.initial_state = save_armature_state(armature)
            
            with ProgressTracker(context, 3, "Fixing Bone Hierarchy") as progress:
                # Step 1: Fix bone parenting
                self.fix_bone_parenting(armature)
                progress.step("Fixed bone parenting")
                
                # Step 2: Connect bones
                self.connect_bones(context, armature)
                progress.step("Connected bones")
                
                # Step 3: Validate hierarchy
                if not self.validate_hierarchy(armature):
                    self.report({'WARNING'}, t("MMD.hierarchy_validation_warning"))
                progress.step("Validated hierarchy")

            self.report({'INFO'}, t("MMD.hierarchy_fixed"))
            return {'FINISHED'}
            
        except Exception as e:
            logger.error(f"Hierarchy fix failed: {str(e)}")
            if hasattr(self, 'initial_state'):
                restore_armature_state(armature, self.initial_state)
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

class AvatarToolkit_OT_CleanupMMDArmature(Operator):
    bl_idname = "avatar_toolkit.mmd_cleanup_armature"
    bl_label = t("MMD.cleanup_armature")
    bl_options = {'REGISTER', 'UNDO'}

    def remove_unused_bones(self, context: Context, armature: Object) -> None:
        """Remove bones that aren't in the standard hierarchy or affecting weights"""
        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = armature.data.edit_bones
        
        # Get all bones affecting vertex groups
        used_bones = set()
        for mesh in get_all_meshes(context):
            used_bones.update(group.name for group in mesh.vertex_groups)
            
        # Add essential bones from dictionary
        essential_bones = set(bone_names.keys())
        
        # Remove non-essential, unused bones
        for bone in edit_bones[:]:  # Slice to avoid modification during iteration
            simplified_name = simplify_bonename(bone.name)
            if (not any(simplified_name in variations for variations in bone_names.values()) and 
                bone.name not in used_bones):
                edit_bones.remove(bone)

    def fix_bone_orientations(self, armature: Object) -> None:
        """Fix bone orientations for Unity/VRChat compatibility"""
        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = armature.data.edit_bones
        
        # Standard bone alignments
        alignments = {
            'spine': (0, 0, 1),    # Points up
            'chest': (0, 0, 1),
            'neck': (0, 0, 1),
            'head': (0, 0, 1),
            'shoulder': (1, 0, 0),  # Points outward
            'arm': (0, -1, 0),     # Points down
            'elbow': (0, -1, 0),
            'leg': (0, -1, 0),
            'knee': (0, -1, 0),
            'foot': (1, 0, 0),     # Points forward
        }
        
        for bone in edit_bones:
            simplified_name = simplify_bonename(bone.name)
            for bone_type, direction in alignments.items():
                if bone_type in simplified_name:
                    # Calculate new tail position while maintaining length
                    length = (bone.tail - bone.head).length
                    bone.tail = bone.head + Vector(direction) * length
                    break

    def execute(self, context: Context) -> Set[str]:
        try:
            armature = get_active_armature(context)
            
            # Save initial state
            if context.scene.avatar_toolkit.save_backup_state:
                self.initial_state = save_armature_state(armature)
            
            with ProgressTracker(context, 2, "Cleaning Up Armature") as progress:
                # Step 1: Remove unused bones
                self.remove_unused_bones(context, armature)
                progress.step("Removed unused bones")
                
                # Step 2: Fix bone orientations
                self.fix_bone_orientations(armature)
                progress.step("Fixed bone orientations")

            self.report({'INFO'}, t("MMD.cleanup_completed"))
            return {'FINISHED'}
            
        except Exception as e:
            logger.error(f"Armature cleanup failed: {str(e)}")
            if hasattr(self, 'initial_state'):
                restore_armature_state(armature, self.initial_state)
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
