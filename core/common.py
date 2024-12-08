import bpy
import numpy as np
from bpy.types import Context, Object, Modifier, EditBone, Operator
from typing import Optional, Tuple, List, Set, Dict, Any, Generator, Callable
from ..core.logging_setup import logger
from ..core.translations import t
from ..core.dictionaries import bone_names

class ProgressTracker:
    """Universal progress tracking for Avatar Toolkit operations"""
    
    def __init__(self, context: Context, total_steps: int, operation_name: str = "Operation"):
        self.context = context
        self.total = total_steps
        self.current = 0
        self.operation_name = operation_name
        self.wm = context.window_manager
        
    def step(self, message: str = "") -> None:
        """Update progress by one step"""
        self.current += 1
        progress = self.current / self.total
        self.wm.progress_begin(0, 100)
        self.wm.progress_update(progress * 100)
        logger.debug(f"{self.operation_name} - {progress:.1%}: {message}")
        
    def __enter__(self):
        logger.info(f"Starting {self.operation_name}")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.wm.progress_end()
        logger.info(f"Completed {self.operation_name}")

def get_active_armature(context: bpy.types.Context) -> Optional[bpy.types.Object]:
    """Get the currently selected armature from Avatar Toolkit properties"""
    armature_name = context.scene.avatar_toolkit.active_armature
    if armature_name and armature_name != 'NONE':
        return bpy.data.objects.get(armature_name)
    return None

def set_active_armature(context: bpy.types.Context, armature: bpy.types.Object) -> None:
    """Set the active armature for Avatar Toolkit operations"""
    context.scene.avatar_toolkit.active_armature = armature

def get_armature_list(self=None, context: bpy.types.Context = None) -> List[Tuple[str, str, str]]:
    """Get list of all armature objects in the scene"""
    if context is None:
        context = bpy.context
    armatures = [(obj.name, obj.name, "") for obj in context.scene.objects if obj.type == 'ARMATURE']
    if not armatures:
        return [('NONE', t("Armature.validation.no_armature"), '')]
    return armatures

def validate_armature(armature: bpy.types.Object) -> Tuple[bool, List[str]]:
    """Enhanced armature validation with multiple validation modes"""
    validation_mode = bpy.context.scene.avatar_toolkit.validation_mode
    
    # Skip validation if mode is NONE
    if validation_mode == 'NONE':
        return True, []
        
    messages = []
    
    # Basic checks always run if not NONE
    if not armature or armature.type != 'ARMATURE' or not armature.data.bones:
        return False, [t("Armature.validation.basic_check_failed")]
        
    found_bones = {bone.name.lower(): bone for bone in armature.data.bones}
    
    # Essential bones check (BASIC and STRICT)
    essential_bones = {'hips', 'spine', 'chest', 'neck', 'head'}
    missing_bones = []
    for bone in essential_bones:
        if not any(alt_name in found_bones for alt_name in bone_names[bone]):
            missing_bones.append(bone)
    
    if missing_bones:
        messages.append(t("Armature.validation.missing_bones", bones=", ".join(missing_bones)))
    
    # Additional checks for STRICT mode only
    if validation_mode == 'STRICT':
        # Hierarchy validation
        hierarchy = [('hips', 'spine'), ('spine', 'chest'), ('chest', 'neck'), ('neck', 'head')]
        for parent, child in hierarchy:
            if not validate_bone_hierarchy(found_bones, parent, child):
                messages.append(t("Armature.validation.invalid_hierarchy", parent=parent, child=child))
        
        # Symmetry validation
        symmetry_pairs = [('arm', 'l', 'r'), ('leg', 'l', 'r')]
        for base, left, right in symmetry_pairs:
            if not validate_symmetry(found_bones, base, left, right):
                messages.append(t("Armature.validation.asymmetric_bones", bone=base))
                
        # Special handling for hand/wrist symmetry
        if (not validate_symmetry(found_bones, 'hand', 'l', 'r') and 
            not validate_symmetry(found_bones, 'wrist', 'l', 'r')):
            messages.append(t("Armature.validation.asymmetric_hand_wrist"))
    
    is_valid = len(messages) == 0
    return is_valid, messages

def validate_bone_hierarchy(bones: Dict[str, bpy.types.Bone], parent_name: str, child_name: str) -> bool:
    """Validate if there is a valid parent-child relationship between bones"""
    # Find matching parent and child bones using bone_names dictionary
    parent_bone = None
    child_bone = None
    
    # Check for parent bone matches
    for alt_name in bone_names[parent_name]:
        if alt_name in bones:
            parent_bone = bones[alt_name]
            break
            
    # Check for child bone matches
    for alt_name in bone_names[child_name]:
        if alt_name in bones:
            child_bone = bones[alt_name]
            break
    
    if not parent_bone or not child_bone:
        return False
        
    # Check if child's parent matches parent bone
    return child_bone.parent == parent_bone

def validate_symmetry(bones: Dict[str, bpy.types.Bone], base: str, left: str, right: str) -> bool:
    """
    Validate if matching left and right bones exist for a given base bone name
    """
    # Define common naming patterns
    left_patterns = [
        f"{base}.{left}",
        f"{base}_{left}",
        f"{left}_{base}"
    ]
    
    right_patterns = [
        f"{base}.{right}",
        f"{base}_{right}", 
        f"{right}_{base}"
    ]
    
    # Check if any of the patterns exist in the bones dictionary
    left_exists = any(pattern in bones for pattern in left_patterns)
    right_exists = any(pattern in bones for pattern in right_patterns)
    
    return left_exists and right_exists
  
def auto_select_single_armature(context: bpy.types.Context) -> None:
    """Automatically select armature if only one exists in scene"""
    armatures = get_armature_list(context)
    if len(armatures) == 1 and armatures[0][0] != 'NONE':
        toolkit = context.scene.avatar_toolkit
        set_active_armature(context, armatures[0])

def clear_default_objects() -> None:
    """Removes default Blender objects (cube, light, camera)"""
    default_names: Set[str] = {'Cube', 'Light', 'Camera'}
    for obj in bpy.data.objects:
        if obj.name.split('.')[0] in default_names:
            bpy.data.objects.remove(obj, do_unlink=True)

def get_armature_stats(armature: bpy.types.Object) -> dict:
    """Get statistics about the armature"""
    return {
        'bone_count': len(armature.data.bones),
        'has_pose': bool(armature.pose),
        'visible': not armature.hide_viewport,
        'name': armature.name
    }

def get_all_meshes(context: Context) -> List[Object]:
    """Get all mesh objects parented to the active armature"""
    armature = get_active_armature(context)
    if armature:
        return [obj for obj in bpy.data.objects if obj.type == 'MESH' and obj.parent == armature]
    return []

def validate_mesh_for_pose(mesh_obj: Object) -> Tuple[bool, str]:
    """Validate mesh object for pose operations"""
    if not mesh_obj.data:
        return False, t("Mesh.validation.no_data")
        
    if not mesh_obj.vertex_groups:
        return False, t("Mesh.validation.no_vertex_groups")
        
    armature_mods = [mod for mod in mesh_obj.modifiers if mod.type == 'ARMATURE']
    if not armature_mods:
        return False, t("Mesh.validation.no_armature_modifier")
    
    return True, t("Mesh.validation.valid")

def cache_vertex_positions(mesh_obj: Object) -> np.ndarray:
    """Cache vertex positions for a mesh object"""
    vertices = mesh_obj.data.vertices
    positions = np.empty(len(vertices) * 3, dtype=np.float32)
    vertices.foreach_get('co', positions)
    return positions.reshape(-1, 3)

def apply_vertex_positions(vertices: Object, positions: np.ndarray) -> None:
    """Apply cached vertex positions to mesh in batch"""
    vertices.foreach_set('co', positions.flatten())

def process_armature_modifiers(mesh_obj: Object) -> List[Dict[str, Any]]:
    """Process and store armature modifier states"""
    modifier_states = []
    for mod in mesh_obj.modifiers:
        if mod.type == 'ARMATURE':
            modifier_states.append({
                'name': mod.name,
                'object': mod.object,
                'vertex_group': mod.vertex_group,
                'show_viewport': mod.show_viewport
            })
    return modifier_states

def apply_pose_as_rest(context: Context, armature_obj: Object, meshes: List[Object]) -> Tuple[bool, str]:
    """Apply current pose as rest pose for armature and update meshes"""
    try:
        logger.info(f"Starting pose application for {len(meshes)} meshes")
        
        with ProgressTracker(context, len(meshes), "Applying Pose") as progress:
            for mesh_obj in meshes:
                if not mesh_obj.data:
                    continue
                    
                if mesh_obj.data.shape_keys and mesh_obj.data.shape_keys.key_blocks:
                    apply_armature_to_mesh_with_shapekeys(armature_obj, mesh_obj, context)
                else:
                    apply_armature_to_mesh(armature_obj, mesh_obj)
                
                progress.step(f"Processed {mesh_obj.name}")
            
            bpy.ops.object.mode_set(mode='POSE')
            bpy.ops.pose.armature_apply(selected=False)
            bpy.ops.object.mode_set(mode='OBJECT')
            
            return True, t("Operation.pose_applied")
            
    except Exception as e:
        logger.error(f"Error applying pose as rest: {str(e)}")
        return False, str(e)

def apply_armature_to_mesh(armature_obj: Object, mesh_obj: Object) -> None:
    """Apply armature deformation to mesh"""
    armature_mod = mesh_obj.modifiers.new('PoseToRest', 'ARMATURE')
    armature_mod.object = armature_obj
    
    if bpy.app.version >= (3, 5):
        mesh_obj.modifiers.move(mesh_obj.modifiers.find(armature_mod.name), 0)
    else:
        for _ in range(len(mesh_obj.modifiers) - 1):
            bpy.ops.object.modifier_move_up(modifier=armature_mod.name)
            
    with bpy.context.temp_override(object=mesh_obj):
        bpy.ops.object.modifier_apply(modifier=armature_mod.name)

def apply_armature_to_mesh_with_shapekeys(armature_obj: Object, mesh_obj: Object, context: Context) -> None:
    """Apply armature deformation to mesh with shape keys"""
    old_active_index = mesh_obj.active_shape_key_index
    old_show_only = mesh_obj.show_only_shape_key
    mesh_obj.show_only_shape_key = True
    
    shape_keys = mesh_obj.data.shape_keys.key_blocks
    vertex_groups = []
    mutes = []
    
    for sk in shape_keys:
        vertex_groups.append(sk.vertex_group)
        sk.vertex_group = ''
        mutes.append(sk.mute)
        sk.mute = False

    disabled_mods = []
    for mod in mesh_obj.modifiers:
        if mod.show_viewport:
            mod.show_viewport = False
            disabled_mods.append(mod)

    arm_mod = mesh_obj.modifiers.new('PoseToRest', 'ARMATURE')
    arm_mod.object = armature_obj
    
    co_length = len(mesh_obj.data.vertices) * 3
    eval_cos = np.empty(co_length, dtype=np.single)
    
    for i, shape_key in enumerate(shape_keys):
        mesh_obj.active_shape_key_index = i
        
        depsgraph = context.evaluated_depsgraph_get()
        eval_mesh = mesh_obj.evaluated_get(depsgraph)
        eval_mesh.data.vertices.foreach_get('co', eval_cos)
        
        shape_key.data.foreach_set('co', eval_cos)
        if i == 0:
            mesh_obj.data.vertices.foreach_set('co', eval_cos)

    for mod in disabled_mods:
        mod.show_viewport = True
        
    mesh_obj.modifiers.remove(arm_mod)
    
    for sk, vg, mute in zip(shape_keys, vertex_groups, mutes):
        sk.vertex_group = vg
        sk.mute = mute
        
    mesh_obj.active_shape_key_index = old_active_index
    mesh_obj.show_only_shape_key = old_show_only

def validate_meshes(meshes: List[Object]) -> Tuple[bool, str]:
    """Validates a list of mesh objects to ensure they are suitable for joining operations"""
    if not meshes:
        return False, t("Optimization.no_meshes")
    if not all(mesh.data for mesh in meshes):
        return False, t("Optimization.invalid_mesh_data")
    if not all(mesh.type == 'MESH' for mesh in meshes):
        return False, t("Optimization.non_mesh_objects")
    return True, ""

def join_mesh_objects(context: Context, meshes: List[Object], progress: Optional[ProgressTracker] = None) -> Tuple[bool, str]:
    """Combines multiple mesh objects into a single mesh with proper cleanup and UV fixing"""
    try:
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        
        for mesh in meshes:
            mesh.select_set(True)
        
        if context.selected_objects:
            context.view_layer.objects.active = context.selected_objects[0]
            
            if progress:
                progress.step(t("Optimization.joining_meshes"))
            bpy.ops.object.join()
            
            if progress:
                progress.step(t("Optimization.applying_transforms"))
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            
            if progress:
                progress.step(t("Optimization.fixing_uvs"))
            fix_uv_coordinates(context)
            
            return True, t("Optimization.meshes_joined")
            
        return False, t("Optimization.no_mesh_selected")
        
    except Exception as e:
        logger.error(f"Failed to join meshes: {str(e)}")
        return False, str(e)

def fix_uv_coordinates(context: Context) -> None:
    """Normalizes and fixes UV coordinates for the active mesh object"""
    obj: Object = context.object
    current_mode: str = context.mode
    current_active: Object = context.view_layer.objects.active
    current_selected: List[Object] = context.selected_objects.copy()

    try:
        bpy.ops.object.mode_set(mode='OBJECT')
        obj.select_set(True)
        context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        
        bpy.ops.mesh.select_all(action='SELECT')

        with context.temp_override(active_object=obj):
            bpy.ops.uv.select_all(action='SELECT')
            bpy.ops.uv.average_islands_scale()
            
        logger.debug(f"UV Fix - Successfully processed {obj.name}")

    except Exception as e:
        logger.warning(f"UV Fix - Skipped processing for {obj.name}: {str(e)}")

    finally:
        bpy.ops.object.mode_set(mode='OBJECT')
        for sel_obj in current_selected:
            sel_obj.select_set(True)
        context.view_layer.objects.active = current_active

def clear_unused_data_blocks(self) -> int:
    """Removes all unused data blocks from the current Blender file"""
    initial_count: int = sum(len(getattr(bpy.data, attr)) for attr in dir(bpy.data) if isinstance(getattr(bpy.data, attr), bpy.types.bpy_prop_collection))
    bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    final_count: int = sum(len(getattr(bpy.data, attr)) for attr in dir(bpy.data) if isinstance(getattr(bpy.data, attr), bpy.types.bpy_prop_collection))
    return initial_count - final_count

def simplify_bonename(name: str) -> str:
    """Simplify bone name by removing spaces, underscores, dots and converting to lowercase"""
    return name.lower().translate(dict.fromkeys(map(ord, u" _.")))

def duplicate_bone_chain(bones: List[EditBone]) -> List[EditBone]:
    """Duplicate a chain of bones while preserving hierarchy"""
    new_bones = []
    parent_map = {}
    
    for bone in bones:
        new_bone = duplicate_bone(bone)
        if bone.parent and bone.parent in parent_map:
            new_bone.parent = parent_map[bone.parent]
        parent_map[bone] = new_bone
        new_bones.append(new_bone)
        
    return new_bones

def restore_bone_transforms(bone: EditBone, transforms: Dict[str, Any]) -> None:
    """Restore bone transforms from stored data"""
    bone.head = transforms['head']
    bone.tail = transforms['tail'] 
    bone.roll = transforms['roll']
    bone.matrix = transforms['matrix']

def get_vertex_weights(mesh_obj: Object, group_name: str) -> Dict[int, float]:
    """Get vertex weights for a specific vertex group"""
    weights = {}
    group_index = mesh_obj.vertex_groups[group_name].index
    for vertex in mesh_obj.data.vertices:
        for group in vertex.groups:
            if group.group == group_index:
                weights[vertex.index] = group.weight
    return weights

def transfer_vertex_weights(mesh_obj: Object, 
                          source_name: str, 
                          target_name: str, 
                          threshold: float = 0.01) -> None:
    """Transfer vertex weights from source to target group"""
    if source_name not in mesh_obj.vertex_groups:
        return
        
    source_group = mesh_obj.vertex_groups[source_name]
    target_group = mesh_obj.vertex_groups.get(target_name)
    
    if not target_group:
        target_group = mesh_obj.vertex_groups.new(name=target_name)
    
    # Get source weights
    weights = get_vertex_weights(mesh_obj, source_name)
    
    # Transfer weights above threshold
    for vertex_index, weight in weights.items():
        if weight > threshold:
            target_group.add([vertex_index], weight, 'ADD')
            
    # Remove source group
    mesh_obj.vertex_groups.remove(source_group)

def remove_unused_shapekeys(mesh_obj: Object, tolerance: float = 0.001) -> int:
    """Remove unused shape keys from a mesh object"""
    if not mesh_obj.data.shape_keys:
        return 0
        
    key_blocks = mesh_obj.data.shape_keys.key_blocks
    vertex_count = len(mesh_obj.data.vertices)
    removed_count = 0
    
    # Cache for relative key locations
    cache = {}
    locations = np.empty(3 * vertex_count, dtype=np.float32)
    to_delete = []
    
    for key in key_blocks:
        if key == key.relative_key:
            continue
            
        # Get current key locations
        key.data.foreach_get("co", locations)
        
        # Get or calculate relative key locations
        if key.relative_key.name not in cache:
            rel_locations = np.empty(3 * vertex_count, dtype=np.float32)
            key.relative_key.data.foreach_get("co", rel_locations)
            cache[key.relative_key.name] = rel_locations
            
        # Compare locations
        locations -= cache[key.relative_key.name]
        if (np.abs(locations) < tolerance).all():
            if not any(c in key.name for c in "-=~"):  # Skip category markers
                to_delete.append(key.name)
                
    # Remove marked shape keys
    for key_name in to_delete:
        mesh_obj.shape_key_remove(key_blocks[key_name])
        removed_count += 1
        
    return removed_count

def save_armature_state(armature: Object) -> Dict[str, Any]:
    """Save current armature state for recovery"""
    state = {
        'bones': {},
        'pose': {},
        'settings': {}
    }
    
    # Save bone data
    for bone in armature.data.bones:
        state['bones'][bone.name] = {
            'head': bone.head_local.copy(),
            'tail': bone.tail_local.copy(),
            'roll': bone.roll,
            'parent': bone.parent.name if bone.parent else None
        }
        
    # Save pose data if exists
    if armature.pose:
        for bone in armature.pose.bones:
            state['pose'][bone.name] = {
                'location': bone.location.copy(),
                'rotation': bone.rotation_quaternion.copy(),
                'scale': bone.scale.copy()
            }
            
    return state

def restore_armature_state(armature: Object, state: Dict[str, Any]) -> None:
    """Restore armature from saved state"""
    bpy.ops.object.mode_set(mode='EDIT')
    
    # Restore bones
    for name, data in state['bones'].items():
        if name in armature.data.edit_bones:
            bone = armature.data.edit_bones[name]
            bone.head = data['head']
            bone.tail = data['tail']
            bone.roll = data['roll']
            
    # Restore parenting
    for name, data in state['bones'].items():
        if data['parent'] and name in armature.data.edit_bones:
            bone = armature.data.edit_bones[name]
            if data['parent'] in armature.data.edit_bones:
                bone.parent = armature.data.edit_bones[data['parent']]
                
    bpy.ops.object.mode_set(mode='POSE')
    
    # Restore pose if exists
    if 'pose' in state:
        for name, data in state['pose'].items():
            if name in armature.pose.bones:
                bone = armature.pose.bones[name]
                bone.location = data['location']
                bone.rotation_quaternion = data['rotation']
                bone.scale = data['scale']
