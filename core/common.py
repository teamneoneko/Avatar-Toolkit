import bpy
import numpy as np
from bpy.types import Context, Object
from typing import Optional, Tuple, List, Set
from ..core.translations import t
from ..core.dictionaries import bone_names

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

def validate_armature(armature: bpy.types.Object) -> Tuple[bool, str]:
    """
    Validate if the selected object is a proper armature and has required bones
    Returns tuple of (is_valid, message)
    """
    if not armature:
        return False, t("Armature.validation.no_armature")
    if armature.type != 'ARMATURE':
        return False, t("Armature.validation.not_armature")
    if not armature.data.bones:
        return False, t("Armature.validation.no_bones")
        
    essential_bones: Set[str] = {'hips', 'spine', 'chest', 'neck', 'head'}
    found_bones: Set[str] = {bone.name.lower() for bone in armature.data.bones}
    
    for bone in essential_bones:
        if not any(alt_name in found_bones for alt_name in bone_names[bone]):
            return False, t("Armature.validation.missing_bone", bone=bone)
            
    return True, t("QuickAccess.valid_armature")

def auto_select_single_armature(context: bpy.types.Context) -> None:
    """Automatically select armature if only one exists in scene"""
    armatures = get_armature_list(context)
    if len(armatures) == 1:
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
    armature = get_active_armature(context)
    if armature:
        return [obj for obj in bpy.data.objects if obj.type == 'MESH' and obj.parent == armature]
    return []

def apply_pose_as_rest(context: Context, armature_obj: Object, meshes: List[Object]) -> bool:
    for mesh_obj in meshes:
        if not mesh_obj.data:
            continue
        if mesh_obj.data.shape_keys and mesh_obj.data.shape_keys.key_blocks:
            if len(mesh_obj.data.shape_keys.key_blocks) == 1:
                basis = mesh_obj.data.shape_keys.key_blocks[0]
                basis_name = basis.name
                mesh_obj.shape_key_remove(basis)
                apply_armature_to_mesh(armature_obj, mesh_obj)
                mesh_obj.shape_key_add(name=basis_name)
            else:
                apply_armature_to_mesh_with_shapekeys(armature_obj, mesh_obj, context)
        else:
            apply_armature_to_mesh(armature_obj, mesh_obj)
            
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.armature_apply(selected=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    return True

def apply_armature_to_mesh(armature_obj: Object, mesh_obj: Object) -> None:
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
