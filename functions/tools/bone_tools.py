import bpy
import re
from bpy.types import Operator, Context, EditBone, Object, Armature, Mesh
from typing import Optional, Dict, Any, List, Tuple
from ...core.translations import t
from ...core.common import (
    get_active_armature, 
    validate_armature, 
    get_all_meshes,
    ProgressTracker,
    validate_bone_hierarchy,
    restore_bone_transforms
)

def duplicate_bone(bone: EditBone) -> EditBone:
    """Create a duplicate of the given bone"""
    arm = bone.id_data
    new_bone = arm.edit_bones.new(bone.name + "_copy")
    new_bone.head = bone.head
    new_bone.tail = bone.tail
    new_bone.roll = bone.roll
    new_bone.parent = bone.parent
    return new_bone

class AvatarToolKit_OT_CreateDigitigradeLegs(Operator):
    """Operator to convert standard legs to digitigrade setup"""
    bl_idname = "avatar_toolkit.create_digitigrade"
    bl_label = t("Tools.create_digitigrade")
    bl_description = t("Tools.create_digitigrade_desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        """Check if operator can be executed"""
        armature = get_active_armature(context)
        if not armature:
            return False
        is_valid, _ = validate_armature(armature)
        return (is_valid and 
                context.mode == 'EDIT_ARMATURE' and
                context.selected_editable_bones is not None and
                len(context.selected_editable_bones) == 2)

    def store_bone_chain_data(self, digi0: EditBone) -> Dict[str, Any]:
        """Store initial bone chain data"""
        chain_data = {}
        current = digi0
        while current:
            chain_data[current.name] = {
                'head': current.head.copy(),
                'tail': current.tail.copy(),
                'roll': current.roll,
                'matrix': current.matrix.copy(),
                'parent': current.parent.name if current.parent else None
            }
            if current.children:
                current = current.children[0]
            else:
                break
        return chain_data

    def process_leg_chain(self, digi0: EditBone) -> bool:
        """Process a single leg bone chain"""
        try:
            # Get bone chain
            digi1: EditBone = digi0.children[0]
            digi2: EditBone = digi1.children[0]
            digi3: EditBone = digi2.children[0]
            digi4: Optional[EditBone] = digi3.children[0] if digi3.children else None

            # Clear roll for all bones
            for bone in [digi0, digi1, digi2, digi3] + ([digi4] if digi4 else []):
                bone.select = True
            bpy.ops.armature.roll_clear()
            bpy.ops.armature.select_all(action='DESELECT')

            # Create thigh bone
            thigh = duplicate_bone(digi0)
            base_name = digi0.name.split('.')[0]
            thigh.name = base_name
            
            # Create and position calf bone
            calf = duplicate_bone(digi1)
            calf.name = digi1.name.split('.')[0]
            calf.parent = thigh
            
            # Calculate new positions
            midpoint = (digi1.tail + digi2.tail) * 0.5
            calf.head = thigh.tail
            calf.tail = midpoint
            
            # Reparent foot to new calf
            digi3.parent = calf
            
            # Mark original bones as non-IK
            for bone in [digi0, digi1, digi2]:
                if "<noik>" not in bone.name:
                    bone.name = bone.name.split('.')[0] + "<noik>"

            return True

        except Exception as e:
            self.report({'ERROR'}, t("Tools.digitigrade_error", error=str(e)))
            return False

    def execute(self, context: Context) -> set[str]:
        """Execute the digitigrade conversion"""
        bpy.ops.object.mode_set(mode='EDIT')
        
        with ProgressTracker(context, len(context.selected_editable_bones), t("Tools.digitigrade")) as progress:
            for digi0 in context.selected_editable_bones:
                progress.step(t("Tools.processing_leg", bone=digi0.name))
                if not self.process_leg_chain(digi0):
                    return {'CANCELLED'}

        self.report({'INFO'}, t("Tools.digitigrade_success"))
        return {'FINISHED'}

class AvatarToolKit_OT_DeleteBoneConstraints(Operator):
    """Operator to remove all bone constraints from armature"""
    bl_idname = "avatar_toolkit.clean_constraints"
    bl_label = t("Tools.clean_constraints")
    bl_description = t("Tools.clean_constraints_desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        """Check if operator can be executed"""
        armature = get_active_armature(context)
        if not armature:
            return False
        is_valid, _ = validate_armature(armature)
        return is_valid

    def execute(self, context: Context) -> set[str]:
        """Execute the constraint removal operation"""

        # Make sure we are in Object mode first or it will error
        bpy.ops.object.mode_set(mode='OBJECT')

        armature = get_active_armature(context)
        
        # Select armature and make it active before changing mode
        bpy.ops.object.select_all(action='DESELECT')
        armature.select_set(True)
        context.view_layer.objects.active = armature
        
        bpy.ops.object.mode_set(mode='POSE')
        
        constraints_removed = 0
        for bone in armature.pose.bones:
            while bone.constraints:
                bone.constraints.remove(bone.constraints[0])
                constraints_removed += 1

        bpy.ops.object.mode_set(mode='OBJECT')
        self.report({'INFO'}, t("Tools.clean_constraints_success", count=constraints_removed))
        return {'FINISHED'}


class AvatarToolKit_OT_RemoveZeroWeightBones(Operator):
    """Operator to remove bones with no vertex weights"""
    bl_idname = "avatar_toolkit.clean_weights"
    bl_label = t("Tools.clean_weights")
    bl_description = t("Tools.clean_weights_desc")
    bl_options = {'REGISTER', 'UNDO'}

    def should_preserve_bone(self, bone_name: str, context: Context) -> bool:
        """Check if bone should be preserved based on settings"""
        if context.scene.avatar_toolkit.merge_twist_bones:
            return "twist" in bone_name.lower()
        return False

    def execute(self, context: Context) -> set[str]:
        """Execute the zero weight bone removal operation"""
        armature = get_active_armature(context)
        if not armature:
            return {'CANCELLED'}

        # Store initial transforms
        bpy.ops.object.mode_set(mode='EDIT')
        initial_transforms: Dict[str, Dict[str, Any]] = {}
        for bone in armature.data.edit_bones:
            initial_transforms[bone.name] = {
                'head': bone.head.copy(),
                'tail': bone.tail.copy(),
                'roll': bone.roll,
                'matrix': bone.matrix.copy(),
                'parent': bone.parent.name if bone.parent else None
            }

        # Get weighted bones
        weighted_bones: List[str] = []
        meshes = get_all_meshes(context)
        
        for mesh in meshes:
            mesh_data: Mesh = mesh.data
            for vertex in mesh_data.vertices:
                for group in vertex.groups:
                    if group.weight > context.scene.avatar_toolkit.merge_weights_threshold:
                        weighted_bones.append(mesh.vertex_groups[group.group].name)

        # Process bone removal
        bpy.ops.object.mode_set(mode='EDIT')
        armature_data: Armature = armature.data
        removed_count = 0

        for bone in armature_data.edit_bones[:]:  # Create a copy of the list
            if (bone.name not in weighted_bones and 
                not self.should_preserve_bone(bone.name, context)):
                
                # Store children data
                children = bone.children
                children_data = {child.name: initial_transforms[child.name] for child in children}

                # Reparent children
                for child in children:
                    child.use_connect = False
                    if bone.parent:
                        child.parent = bone.parent

                # Remove bone
                armature_data.edit_bones.remove(bone)
                removed_count += 1

                # Restore children positions
                for child_name, data in children_data.items():
                    if child_name in armature_data.edit_bones:
                        child = armature_data.edit_bones[child_name]
                        child.head = data['head']
                        child.tail = data['tail']
                        child.roll = data['roll']
                        child.matrix = data['matrix']

        bpy.ops.object.mode_set(mode='OBJECT')
        self.report({'INFO'}, t("Tools.clean_weights_success", count=removed_count))
        return {'FINISHED'}