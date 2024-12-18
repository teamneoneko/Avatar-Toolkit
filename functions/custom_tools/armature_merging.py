import bpy
import numpy as np
from typing import List, Optional, Dict, Set, Tuple, Any
from bpy.types import Context, Object, Operator, ArmatureModifier, EditBone, VertexGroup, Mesh, ShapeKey

from ...core.logging_setup import logger
from ...core.translations import t
from ...core.common import (
    get_all_meshes,
    fix_zero_length_bones,
    clear_unused_data_blocks,
    join_mesh_objects,
    remove_unused_shapekeys
)

class AvatarToolkit_OT_MergeArmature(bpy.types.Operator):
    """Operator for merging two armatures together with their associated meshes"""
    bl_idname: str = 'avatar_toolkit.merge_armatures'
    bl_label: str = t('MergeArmature.label')
    bl_description: str = t('MergeArmature.desc')
    bl_options: Set[str] = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return len(get_all_meshes(context)) > 1

    def execute(self, context: Context) -> Set[str]:
        try:
            wm = context.window_manager
            wm.progress_begin(0, 100)

            # Get both armatures
            base_armature_name: str = context.scene.merge_armature_into
            merge_armature_name: str = context.scene.merge_armature
            base_armature: Optional[Object] = bpy.data.objects.get(base_armature_name)
            merge_armature: Optional[Object] = bpy.data.objects.get(merge_armature_name)
            
            if not base_armature or not merge_armature:
                logger.error(f"Armature not found: {merge_armature_name}")
                self.report({'ERROR'}, t('MergeArmature.error.not_found', name=merge_armature_name))
                return {'CANCELLED'}

            # Remove Rigid Bodies and Joints
            delete_rigidbodies_and_joints(base_armature)
            delete_rigidbodies_and_joints(merge_armature)
            wm.progress_update(40)

            # Check parents and transformations
            if not validate_parents_and_transforms(merge_armature, base_armature, context):
                wm.progress_end()
                return {'CANCELLED'}
            wm.progress_update(80)

            # Get settings from scene properties
            merge_all_bones: bool = context.scene.avatar_toolkit.merge_all_bones
            join_meshes: bool = context.scene.avatar_toolkit.join_meshes

            # Merge armatures
            merge_armatures(
                base_armature_name,
                merge_armature_name,
                mesh_only=False,
                merge_all_bones=merge_all_bones,
                join_meshes=join_meshes,
                operator=self
            )
            wm.progress_update(90)

            wm.progress_update(100)
            wm.progress_end()

            self.report({'INFO'}, t('MergeArmature.success'))
            return {'FINISHED'}

        except Exception as e:
            logger.error(f"Error merging armatures: {str(e)}")
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

def delete_rigidbodies_and_joints(armature: Object) -> None:
    """Delete rigid bodies and joints associated with an armature"""
    to_delete: List[Object] = []
    parent: Object = armature
    while parent.parent:
        parent = parent.parent
        
    for child in parent.children:
        if 'rigidbodies' in child.name.lower() or 'joints' in child.name.lower():
            to_delete.append(child)
        for grandchild in child.children:
            if 'rigidbodies' in grandchild.name.lower() or 'joints' in grandchild.name.lower():
                to_delete.append(grandchild)
    
    for obj in to_delete:
        bpy.data.objects.remove(obj, do_unlink=True)

def validate_parents_and_transforms(merge_armature: Object, base_armature: Object, context: Context) -> bool:
    """Validate parent relationships and transformations of armatures"""
    merge_parent: Optional[Object] = merge_armature.parent
    base_parent: Optional[Object] = base_armature.parent
    
    if merge_parent or base_parent:
        if context.scene.merge_all_bones:
            for armature, parent in [(merge_armature, merge_parent), (base_armature, base_parent)]:
                if parent:
                    if not is_transform_clean(parent):
                        logger.error("Parent transforms are not clean")
                        return False
                    bpy.data.objects.remove(parent, do_unlink=True)
        else:
            logger.error("Parent relationships need fixing")
            return False
    return True

def is_transform_clean(obj: Object) -> bool:
    """Check if object transforms are at default values"""
    for i in range(3):
        if obj.scale[i] != 1 or obj.location[i] != 0 or obj.rotation_euler[i] != 0:
            return False
    return True

def prepare_mesh_vertex_groups(mesh: Object) -> None:
    """Initialize mesh vertex groups for merging process"""
    if mesh.vertex_groups:
        for vg in mesh.vertex_groups:
            mesh.vertex_groups.remove(vg)

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    vg: VertexGroup = mesh.vertex_groups.new(name=mesh.name)
    bpy.ops.object.vertex_group_assign()
    bpy.ops.object.mode_set(mode='OBJECT')

def merge_armatures(
    base_armature_name: str,
    merge_armature_name: str,
    mesh_only: bool,
    merge_all_bones: bool = False,
    join_meshes: bool = False,
    operator: Optional[Operator] = None
) -> None:
    """Main function to merge two armatures with their associated meshes and data"""
    logger.info(f"Merging armatures: {merge_armature_name} into {base_armature_name}")
    tolerance: float = 0.00008726647  # around 0.005 degrees

    base_armature: Optional[Object] = bpy.data.objects.get(base_armature_name)
    merge_armature: Optional[Object] = bpy.data.objects.get(merge_armature_name)

    if not base_armature or not merge_armature:
        logger.error(f"Armature not found: {merge_armature_name}")
        if operator:
            operator.report({'ERROR'}, t('MergeArmature.error.notFound', name=merge_armature_name))
        return

    # Check transforms early
    if not validate_merge_armature_transforms(base_armature, merge_armature, None, tolerance):
        if not bpy.context.scene.avatar_toolkit.apply_transforms:
            logger.error("Transforms not aligned - user notification sent")
            if operator:
                operator.report({'ERROR'}, t('MergeArmature.error.transforms_not_aligned'))
            return

    # Apply transforms if enabled
    if bpy.context.scene.avatar_toolkit.apply_transforms:
        for obj in [base_armature, merge_armature]:
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            obj.select_set(False)

    # Validate and fix armatures
    fix_zero_length_bones(base_armature)
    fix_zero_length_bones(merge_armature)

    # Store original parent relationships
    original_parents: Dict[str, Optional[str]] = {}
    for bone in merge_armature.data.bones:
        original_parents[bone.name] = bone.parent.name if bone.parent else None

    # Get base bone names
    base_bone_names: Set[str] = {bone.name for bone in base_armature.data.bones}

    # Switch to edit mode on merge armature and rename bones
    bpy.context.view_layer.objects.active = merge_armature
    bpy.ops.object.mode_set(mode='EDIT')
    
    # Handle bone renaming based on merge_all_bones setting
    for bone in merge_armature.data.edit_bones:
        if not merge_all_bones:
            # Only rename bones that don't exist in base armature
            if bone.name not in base_bone_names:
                bone.name += '.merge'
        else:
            # Rename all bones from merge armature
            bone.name += '.merge'

    # Return to object mode
    bpy.ops.object.mode_set(mode='OBJECT')

    # Select and join armatures
    bpy.ops.object.select_all(action='DESELECT')
    base_armature.select_set(True)
    merge_armature.select_set(True)
    bpy.context.view_layer.objects.active = base_armature
    bpy.ops.object.join()

    # Restore parent relationships
    bpy.ops.object.mode_set(mode='EDIT')
    for bone in base_armature.data.edit_bones:
        base_name: str = bone.name.replace('.merge', '')
        if base_name in original_parents:
            parent_name: Optional[str] = original_parents[base_name]
            if parent_name:
                parent_bone: Optional[EditBone] = base_armature.data.edit_bones.get(parent_name)
                if parent_bone:
                    bone.parent = parent_bone

    bpy.ops.object.mode_set(mode='OBJECT')

    # Update mesh parenting
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.parent == merge_armature:
            obj.parent = base_armature

    # Process vertex groups if not mesh_only
    if not mesh_only:
        meshes: List[Object] = [obj for obj in bpy.data.objects if obj.type == 'MESH' and obj.parent == base_armature]
        process_vertex_groups(meshes)

        # Remove zero weight vertex groups if enabled
        if bpy.context.scene.avatar_toolkit.remove_zero_weights:
            bpy.context.view_layer.objects.active = base_armature
            for mesh in meshes:
                bpy.context.view_layer.objects.active = mesh
                bpy.ops.avatar_toolkit.clean_weights()

    # Join meshes if requested
    if join_meshes:
        meshes_to_join: List[Object] = [obj for obj in bpy.data.objects if obj.type == 'MESH' and obj.parent == base_armature]
        if meshes_to_join:
            joined_mesh: Optional[Object] = join_mesh_objects(bpy.context, meshes_to_join)
            if joined_mesh:
                logger.info(f"Joined meshes into {joined_mesh.name}")

    # Clean up shape keys if enabled
    if bpy.context.scene.avatar_toolkit.cleanup_shape_keys:
        for obj in bpy.data.objects:
            if obj.type == 'MESH' and obj.parent == base_armature:
                remove_unused_shapekeys(obj)

    # Remove any remaining .merge bones
    bpy.context.view_layer.objects.active = base_armature
    bpy.ops.object.mode_set(mode='EDIT')
    edit_bones: List[EditBone] = base_armature.data.edit_bones
    bones_to_remove: List[EditBone] = [bone for bone in edit_bones if bone.name.endswith('.merge')]
    for bone in bones_to_remove:
        edit_bones.remove(bone)
    bpy.ops.object.mode_set(mode='OBJECT')

    # Final cleanup
    clear_unused_data_blocks()

def validate_merge_armature_transforms(
    base_armature: Object,
    merge_armature: Object, 
    mesh_merge: Optional[Object],
    tolerance: float
) -> bool:
    """Validate transforms of both armatures and mesh"""
    for i in [0, 1, 2]:
        if abs(base_armature.scale[i] - merge_armature.scale[i]) > tolerance:
            return False
            
        if abs(merge_armature.rotation_euler[i]) > tolerance or \
           (mesh_merge and abs(mesh_merge.rotation_euler[i]) > tolerance):
            return False
            
    return True

def adjust_merge_armature_transforms(
    merge_armature: Object,
    mesh_merge: Object
) -> None:
    """Adjust transforms of the merge armature"""
    old_loc: List[float] = list(merge_armature.location)
    old_scale: List[float] = list(merge_armature.scale)

    for i in [0, 1, 2]:
        merge_armature.location[i] = (mesh_merge.location[i] * old_scale[i]) + old_loc[i]
        merge_armature.rotation_euler[i] = mesh_merge.rotation_euler[i]
        merge_armature.scale[i] = mesh_merge.scale[i] * old_scale[i]

    for i in [0, 1, 2]:
        mesh_merge.location[i] = 0
        mesh_merge.rotation_euler[i] = 0
        mesh_merge.scale[i] = 1

def detect_bones_to_merge(
    base_edit_bones: bpy.types.ArmatureEditBones,
    merge_edit_bones: bpy.types.ArmatureEditBones,
    tolerance: float,
    merge_all_bones: bool
) -> List[str]:
    """Detect corresponding bones between base and merge armatures using smart detection and position tolerance"""
    bones_to_merge: List[str] = []

    # Cache base bone positions
    base_bones_positions: Dict[str, np.ndarray] = {
        bone.name: np.array(bone.head) for bone in base_edit_bones
    }

    # Smart bone detection
    for merge_bone in merge_edit_bones:
        merge_bone_position: np.ndarray = np.array(merge_bone.head)
        found_match: bool = False

        if merge_all_bones and merge_bone.name in base_bones_positions:
            # If merging same bones by name
            bones_to_merge.append(merge_bone.name)
            found_match = True
        else:
            # Find bones with close positions
            for base_bone_name, base_bone_position in base_bones_positions.items():
                if np.linalg.norm(merge_bone_position - base_bone_position) <= tolerance:
                    bones_to_merge.append(base_bone_name)
                    found_match = True
                    break

        if not found_match:
            # Handle unmatched bones if needed
            pass

    return bones_to_merge

def process_vertex_groups(meshes: List[Object]) -> None:
    """Process vertex groups in meshes"""
    for mesh in meshes:
        vg_names: Set[str] = {vg.name for vg in mesh.vertex_groups}
        merge_vg_names: List[str] = [vg_name for vg_name in vg_names if vg_name.endswith('.merge')]

        for vg_merge_name in merge_vg_names:
            base_name: str = vg_merge_name[:-6]
            vg_merge: Optional[VertexGroup] = mesh.vertex_groups.get(vg_merge_name)
            vg_base: Optional[VertexGroup] = mesh.vertex_groups.get(base_name)

            if vg_merge is None:
                continue

            if vg_base:
                mix_vertex_groups(mesh, vg_merge_name, base_name)
            else:
                vg_merge.name = base_name

def mix_vertex_groups(mesh: Object, vg_from_name: str, vg_to_name: str) -> None:
    """Mix vertex group weights"""
    vg_from: Optional[VertexGroup] = mesh.vertex_groups.get(vg_from_name)
    vg_to: Optional[VertexGroup] = mesh.vertex_groups.get(vg_to_name)
        
    if not vg_from or not vg_to:
        return

    num_vertices: int = len(mesh.data.vertices)
    weights_from: np.ndarray = np.zeros(num_vertices)
    weights_to: np.ndarray = np.zeros(num_vertices)

    idx_from: int = vg_from.index
    idx_to: int = vg_to.index

    for v in mesh.data.vertices:
        for g in v.groups:
            if g.group == idx_from:
                weights_from[v.index] = g.weight
            elif g.group == idx_to:
                weights_to[v.index] = g.weight

    weights_combined: np.ndarray = np.clip(weights_from + weights_to, 0.0, 1.0)
    vg_to.add(range(num_vertices), weights_combined.tolist(), 'REPLACE')
    mesh.vertex_groups.remove(vg_from)

def remove_unused_vertex_groups(mesh: Object) -> None:
    """Remove vertex groups with no weights"""
    for vg in mesh.vertex_groups:
        has_weights: bool = False
        for vert in mesh.data.vertices:
            for group in vert.groups:
                if group.group == vg.index and group.weight > 0.001:
                    has_weights = True
                    break
            if has_weights:
                break
        if not has_weights:
            mesh.vertex_groups.remove(vg)

def apply_armature_to_mesh(armature: Object, mesh: Object) -> None:
    """Apply armature deformation to mesh"""
    armature_mod: ArmatureModifier = mesh.modifiers.new('PoseToRest', 'ARMATURE')
    armature_mod.object = armature
    
    if bpy.app.version >= (3, 5):
        mesh.modifiers.move(mesh.modifiers.find(armature_mod.name), 0)
    else:
        for _ in range(len(mesh.modifiers) - 1):
            bpy.ops.object.modifier_move_up(modifier=armature_mod.name)
            
    with bpy.context.temp_override(object=mesh):
        bpy.ops.object.modifier_apply(modifier=armature_mod.name)

def apply_armature_to_mesh_with_shapekeys(armature: Object, mesh: Object, context: Context) -> None:
    """Apply armature deformation to mesh with shape keys"""
    old_active_index: int = mesh.active_shape_key_index
    old_show_only: bool = mesh.show_only_shape_key
    mesh.show_only_shape_key = True
    
    shape_keys: List[ShapeKey] = mesh.data.shape_keys.key_blocks
    vertex_groups: List[str] = []
    mutes: List[bool] = []
    
    for sk in shape_keys:
        vertex_groups.append(sk.vertex_group)
        sk.vertex_group = ''
        mutes.append(sk.mute)
        sk.mute = False

    disabled_mods: List[Any] = []
    for mod in mesh.modifiers:
        if mod.show_viewport:
            mod.show_viewport = False
            disabled_mods.append(mod)

    arm_mod: ArmatureModifier = mesh.modifiers.new('PoseToRest', 'ARMATURE')
    arm_mod.object = armature
    
    co_length: int = len(mesh.data.vertices) * 3
    eval_cos: np.ndarray = np.empty(co_length, dtype=np.single)
    
    for i, shape_key in enumerate(shape_keys):
        mesh.active_shape_key_index = i
        
        depsgraph = context.evaluated_depsgraph_get()
        eval_mesh: Mesh = mesh.evaluated_get(depsgraph)
        eval_mesh.data.vertices.foreach_get('co', eval_cos)
        
        shape_key.data.foreach_set('co', eval_cos)
        if i == 0:
            mesh.data.vertices.foreach_set('co', eval_cos)

    for mod in disabled_mods:
        mod.show_viewport = True
        
    mesh.modifiers.remove(arm_mod)
    
    for sk, vg, mute in zip(shape_keys, vertex_groups, mutes):
        sk.vertex_group = vg
        sk.mute = mute
        
    mesh.active_shape_key_index = old_active_index
    mesh.show_only_shape_key = old_show_only
