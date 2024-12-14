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
    transfer_vertex_weights,
    get_all_meshes
)
from ..core.translations import t
from ..core.dictionaries import bone_names, dont_delete_these_main_bones

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
    
    def process_bone_names(self, context: Context) -> None:
        """Process and standardize bone names"""
        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.armature.data.edit_bones
        
        # First pass - handle IK bones
        ik_bones = [bone for bone in edit_bones if 'IK' in bone.name or 'ＩＫ' in bone.name]
        for bone in ik_bones:
            new_name = f"ik_{self.standardize_bone_name(bone.name.replace('IK', '').replace('ＩＫ', ''))}"
            self.bone_mapping[bone.name] = new_name
            bone.name = new_name
        
        # Second pass - standard bones
        for bone in edit_bones:
            if bone not in ik_bones:
                new_name = self.standardize_bone_name(bone.name)
                if new_name != bone.name:
                    self.bone_mapping[bone.name] = new_name
                    bone.name = new_name
                
    def translate_japanese_bone_name(self, name: str) -> str:
        """Translate Japanese bone names to English standardized names"""
        name_lower = name.lower()
        
        for bone_category, variations in bone_names.items():
            for variation in variations:
                if variation in name_lower:
                    return bone_category
                    
        return name

    def standardize_bone_name(self, name: str) -> str:
        """Standardize individual bone names"""
        result = self.translate_japanese_bone_name(name)
        
        prefixes = ['ValveBiped_', 'Bip01_', 'MMD_', 'Armature|']
        for prefix in prefixes:
            if result.lower().startswith(prefix.lower()):
                result = result[len(prefix):]
        
        if result.endswith('_L') or result.endswith('.L'):
            result = f"{result[:-2]}.L"
        elif result.endswith('_R') or result.endswith('.R'):
            result = f"{result[:-2]}.R"
        
        return result
        return result
    
    def fix_bone_structure(self, context: Context) -> None:
        """Fix bone hierarchy and orientations"""
        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.armature.data.edit_bones
        
        self.process_spine_chain(context)
        self.fix_bone_orientations(context)
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
        self.remove_unused_bones(context)
        self.cleanup_constraints(context)
        self.fix_zero_length_bones(context)
    
    def get_associated_meshes(self, context: Context) -> List[Object]:
        """Get all mesh objects associated with the armature"""
        return [obj for obj in bpy.data.objects 
                if obj.type == 'MESH' 
                and obj.parent == self.armature]
                
    def process_spine_chain(self, context: Context) -> None:
        """Process and fix spine bone chain hierarchy"""
        bpy.ops.object.mode_set(mode='EDIT')
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
        
        # Define standardized roll values for key bones
        roll_values = {
            'upper_arm.L': -0.1,
            'upper_arm.R': 0.1,
            'forearm.L': -0.1,
            'forearm.R': 0.1,
            'thigh.L': 0.0,
            'thigh.R': 0.0,
            'shin.L': 0.0,
            'shin.R': 0.0,
            'foot.L': 0.0,
            'foot.R': 0.0,
            'spine': 0.0,
            'chest': 0.0,
            'neck': 0.0
        }
        
        # Apply roll corrections
        for bone in edit_bones:
            if bone.name.lower() in roll_values:
                bone.roll = roll_values[bone.name.lower()]
        
        # Process arm chains
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
        
        # Process leg chains
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
                    
        # Align twist bones if present
        twist_bones = [b for b in edit_bones if 'twist' in b.name.lower()]
        for twist_bone in twist_bones:
            if twist_bone.parent:
                twist_bone.roll = twist_bone.parent.roll

    def remove_unused_bones(self, context: Context) -> None:
        """Remove unused and unnecessary bones from the armature"""
        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.armature.data.edit_bones
        
        # Get list of bones that have vertex weights
        used_bones = set()
        for mesh in self.get_associated_meshes(context):
            for group in mesh.vertex_groups:
                used_bones.add(group.name)
        
        # Get list of essential bones to always keep
        essential_bones = {
            'hips', 'spine', 'chest', 'upper_chest', 'neck', 'head',
            'left_leg', 'right_leg', 'left_knee', 'right_knee',
            'left_ankle', 'right_ankle', 'left_toe', 'right_toe'
        }
        
        # Add any additional bones you want to preserve
        essential_bones.update(dont_delete_these_main_bones)
        
        # Remove unused bones
        for bone in edit_bones:
            # Skip if bone is essential
            if bone.name.lower() in essential_bones:
                continue
            
            # Skip if bone has weights
            if bone.name in used_bones:
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
        
        vertex_groups = mesh_obj.vertex_groups
        
        groups_to_remove = set()
        
        for group in vertex_groups:
            weights = get_vertex_weights(mesh_obj, group.name)
            
            if not any(weight > threshold for weight in weights.values()):
                groups_to_remove.add(group.name)
        
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
        """Remove all constraints from the armature."""
        bpy.ops.object.mode_set(mode='POSE')

        for pose_bone in self.armature.pose.bones:
            constraints_to_remove = [constraint for constraint in pose_bone.constraints]
            for constraint in constraints_to_remove:
                pose_bone.constraints.remove(constraint)

    def fix_zero_length_bones(self, context: Context) -> None:
        """Fix zero-length bones by setting minimal length"""
        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.armature.data.edit_bones
        
        min_length = 0.01  # Minimum bone length in Blender units
        
        for bone in edit_bones:
            bone_length = (bone.tail - bone.head).length
            
            if bone_length < min_length:
                if bone.parent:
                    direction = bone.parent.tail - bone.parent.head
                    direction.normalize()
                else:
                    direction = Vector((0, 0, 1))
                
                bone.tail = bone.head + (direction * min_length)


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

class AVATAR_TOOLKIT_OT_ConvertMmdMorphs(Operator):
    """Convert MMD morph data to shape keys"""
    bl_idname = "avatar_toolkit.convert_mmd_morphs"
    bl_label = t("MMD.convert_morphs") 
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

        try:
            with ProgressTracker(context, 3, "Converting MMD Morphs") as progress:
                # Convert bone morphs to shape keys
                if hasattr(armature, 'mmd_root') and armature.mmd_root.bone_morphs:
                    self.process_bone_morphs(context, armature, progress)
                    
                progress.step("Processed bone morphs")
                
                # Clean up unused data
                self.cleanup_unused_data(context)
                progress.step("Cleaned up data")
                
                # Validate results  
                self.validate_results(context)
                progress.step("Validated results")

            self.report({'INFO'}, t("MMD.conversion_complete"))
            return {'FINISHED'}

        except Exception as e:
            logger.error(f"Error converting MMD morphs: {str(e)}")
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

    def process_bone_morphs(self, context, armature, progress):
        """Process bone morphs into shape keys"""
        for morph in armature.mmd_root.bone_morphs:
            for mesh in get_all_meshes(context):
                # Create armature modifier
                mod = mesh.modifiers.new(morph.name, 'ARMATURE')
                mod.object = armature
                
                # Apply as shape key
                with context.temp_override(object=mesh):
                    bpy.ops.object.modifier_apply(modifier=mod.name)

class AVATAR_TOOLKIT_OT_CleanupMmdModel(Operator):
    """Clean up MMD model by removing unused data and fixing display settings"""
    bl_idname = "avatar_toolkit.cleanup_mmd"
    bl_label = t("MMD.cleanup")
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        armature = get_active_armature(context)
        if not armature:
            self.report({'ERROR'}, t("MMD.no_armature"))
            return {'CANCELLED'}

        try:
            with ProgressTracker(context, 4, "Cleaning MMD Model") as progress:
                # Remove rigid bodies and joints
                self.remove_physics_objects(armature)
                progress.step("Removed physics objects")
                
                # Clean up collections and hierarchy
                self.cleanup_hierarchy(context, armature)
                progress.step("Cleaned hierarchy")
                
                # Fix viewport settings
                self.fix_viewport_settings(context)
                progress.step("Fixed viewport")
                
                # Final cleanup
                clear_unused_data_blocks()
                progress.step("Cleared unused data")

            self.report({'INFO'}, t("MMD.cleanup_complete"))
            return {'FINISHED'}

        except Exception as e:
            logger.error(f"Error cleaning MMD model: {str(e)}")
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

    def remove_physics_objects(self, armature):
        """Remove physics-related objects"""
        to_delete = []
        for child in armature.children:
            if any(x in child.name.lower() for x in ['rigidbodies', 'joints', 'physics']):
                to_delete.append(child)
                
        for obj in to_delete:
            bpy.data.objects.remove(obj, do_unlink=True)

    def cleanup_hierarchy(self, context, armature):
        """Clean up object hierarchy and collections"""
        meshes = get_all_meshes(context)
        for mesh in meshes:
            # Ensure proper parenting
            mesh.parent = armature
            mesh.parent_type = 'ARMATURE'
            
            # Clean up collections
            for col in mesh.users_collection:
                if col != context.scene.collection:
                    col.objects.unlink(mesh)
            
            if mesh.name not in context.scene.collection.objects:
                context.scene.collection.objects.link(mesh)

    def fix_viewport_settings(self, context):
        """Fix viewport display settings"""
        # Set armature display
        armature = get_active_armature(context)
        armature.data.display_type = 'OCTAHEDRAL'
        armature.show_in_front = True
        
        # Set viewport shading
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                space = area.spaces[0]
                space.shading.type = 'MATERIAL'
                space.clip_start = 0.01
                space.clip_end = 300

class AVATAR_TOOLKIT_OT_FixMeshes(Operator):
    """Clean up and optimize mesh materials, shading, and shape keys"""
    bl_idname = "avatar_toolkit.fix_meshes"
    bl_label = t("Optimization.fix_meshes")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        armature = get_active_armature(context)
        return armature is not None and get_all_meshes(context)

    def execute(self, context):
        try:
            meshes = get_all_meshes(context)
            if not meshes:
                self.report({'ERROR'}, t("Optimization.no_meshes"))
                return {'CANCELLED'}

            with ProgressTracker(context, len(meshes), "Fixing Meshes") as progress:
                for mesh in meshes:
                    self.process_mesh(context, mesh)
                    progress.step(f"Processed {mesh.name}")

            self.report({'INFO'}, t("Optimization.meshes_fixed"))
            return {'FINISHED'}

        except Exception as e:
            logger.error(f"Error fixing meshes: {str(e)}")
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

    def process_mesh(self, context: Context, mesh: Object) -> None:
        """Process and fix individual mesh"""
        # Unlock transforms
        for i in range(3):
            mesh.lock_location[i] = False
            mesh.lock_rotation[i] = False
            mesh.lock_scale[i] = False

        # Process shape keys
        if mesh.data.shape_keys:
            self.fix_shape_keys(mesh)

        # Process materials
        self.fix_materials(context, mesh)

    def fix_shape_keys(self, mesh: Object) -> None:
        """Fix and clean up shape keys"""
        if not mesh.data.shape_keys:
            return

        shape_keys = mesh.data.shape_keys.key_blocks
        
        # Rename basis
        if shape_keys[0].name != "Basis":
            shape_keys[0].name = "Basis"

        # Clean up names
        for key in shape_keys:
            # Remove common prefixes/suffixes
            clean_name = key.name
            for prefix in ['Face.M F00 000 Fcl ', 'Face.M F00 000 00 Fcl ']:
                clean_name = clean_name.replace(prefix, '')
            
            # Replace underscores with spaces
            clean_name = clean_name.replace('_', ' ')
            key.name = clean_name

        # Sort shape keys by category
        categories = ['MTH', 'EYE', 'BRW', 'ALL']
        
        # Create sorted list of shape key names
        ordered_names = []
        
        # Add categorized keys first
        for category in categories:
            category_keys = [key.name for key in shape_keys if key.name.startswith(category)]
            ordered_names.extend(sorted(category_keys))
        
        # Add remaining keys
        remaining = [key.name for key in shape_keys if not any(key.name.startswith(c) for c in categories)]
        ordered_names.extend(sorted(remaining))
        
        # Reorder using context override
        with bpy.context.temp_override(active_object=mesh, selected_objects=[mesh]):
            for idx, name in enumerate(ordered_names):
                mesh.active_shape_key_index = shape_keys.find(name)
                while mesh.active_shape_key_index > idx:
                    bpy.ops.object.shape_key_move(type='UP')


    def fix_materials(self, context: Context, mesh: Object) -> None:
        """Fix and optimize materials"""
        for slot in mesh.material_slots:
            if not slot.material:
                continue
                
            material = slot.material
            
            # Set up basic material properties
            material.use_backface_culling = True
            material.blend_method = 'HASHED'
            material.shadow_method = 'HASHED'
            
            # Clean up material name
            material.name = self.clean_material_name(material.name)
            
            # Consolidate similar materials
            for other_slot in mesh.material_slots:
                if other_slot.material and other_slot.material != material:
                    if materials_match(material, other_slot.material):
                        other_slot.material = material

    def clean_material_name(self, name: str) -> str:
        """Clean up material name"""
        # Remove common prefixes/suffixes
        prefixes = ['material', 'mat', 'mtl', 'material.']
        for prefix in prefixes:
            if name.lower().startswith(prefix):
                name = name[len(prefix):]
                
        # Remove numbers at end
        while name and name[-1].isdigit():
            name = name[:-1]
            
        return name.strip()

class AVATAR_TOOLKIT_OT_ValidateMeshes(Operator):
    """Validate meshes and UV maps for common issues"""
    bl_idname = "avatar_toolkit.validate_meshes"
    bl_label = t("Validation.check_meshes")
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        armature = get_active_armature(context)
        if not armature:
            self.report({'ERROR'}, t("Validation.no_armature"))
            return {'CANCELLED'}

        try:
            with ProgressTracker(context, 3, "Validating Meshes") as progress:
                # Check bone hierarchy
                hierarchy_issues = self.validate_bone_hierarchy(armature)
                progress.step("Checked bone hierarchy")
                
                # Check UV coordinates
                uv_issues = self.validate_uv_maps(context)
                progress.step("Checked UV maps")
                
                # Generate report
                self.generate_validation_report(context, hierarchy_issues, uv_issues)
                progress.step("Generated report")

            return {'FINISHED'}

        except Exception as e:
            logger.error(f"Error validating meshes: {str(e)}")
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

    def validate_bone_hierarchy(self, armature: Object) -> List[str]:
        """Validate bone hierarchy against standard structure"""
        issues = []
        
        # Define expected hierarchy
        hierarchy = [
            ['hips', 'spine', 'chest', 'neck', 'head'],
            ['hips', 'left_leg', 'left_knee', 'left_ankle'],
            ['hips', 'right_leg', 'right_knee', 'right_ankle'],
            ['chest', 'left_shoulder', 'left_arm', 'left_elbow', 'left_wrist'],
            ['chest', 'right_shoulder', 'right_arm', 'right_elbow', 'right_wrist']
        ]

        for chain in hierarchy:
            previous = None
            for bone_name in chain:
                # Check if bone exists
                bone = None
                for alt_name in bone_names[bone_name]:
                    if alt_name in armature.data.bones:
                        bone = armature.data.bones[alt_name]
                        break
                        
                if not bone:
                    issues.append(t("Validation.missing_bone", bone=bone_name))
                    continue
                    
                # Check parent relationship
                if previous:
                    if not bone.parent:
                        issues.append(t("Validation.no_parent", bone=bone.name))
                    elif bone.parent.name != previous.name:
                        issues.append(t("Validation.wrong_parent", 
                                      bone=bone.name, 
                                      expected=previous.name, 
                                      actual=bone.parent.name))
                previous = bone
                
        return issues

    def validate_uv_maps(self, context: Context) -> Dict[str, int]:
        """Check UV maps for issues"""
        issues = {'nan_coords': 0, 'missing_uvs': 0}
        
        for mesh in get_all_meshes(context):
            if not mesh.data.uv_layers:
                issues['missing_uvs'] += 1
                continue
                
            for uv_layer in mesh.data.uv_layers:
                for uv in uv_layer.data:
                    if math.isnan(uv.uv.x):
                        uv.uv.x = 0
                        issues['nan_coords'] += 1
                    if math.isnan(uv.uv.y):
                        uv.uv.y = 0
                        issues['nan_coords'] += 1
                        
        return issues

    def generate_validation_report(self, context: Context, 
                                 hierarchy_issues: List[str], 
                                 uv_issues: Dict[str, int]) -> None:
        """Generate and display validation report"""
        report_lines = []
        
        # Add hierarchy issues
        if hierarchy_issues:
            report_lines.append(t("Validation.hierarchy_issues"))
            report_lines.extend(hierarchy_issues)
            
        # Add UV issues
        if uv_issues['nan_coords'] > 0:
            report_lines.append(t("Validation.uv_nan_coords", 
                                count=uv_issues['nan_coords']))
            
        if uv_issues['missing_uvs'] > 0:
            report_lines.append(t("Validation.missing_uvs", 
                                count=uv_issues['missing_uvs']))
            
        # Show report
        if report_lines:
            self.report({'WARNING'}, "\n".join(report_lines))
        else:
            self.report({'INFO'}, t("Validation.no_issues"))
