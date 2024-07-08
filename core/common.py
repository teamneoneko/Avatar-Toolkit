import bpy
import numpy as np
from .dictionaries import bone_names

from typing import List, Optional
from bpy.types import Object, ShapeKey, Mesh, Context
from functools import lru_cache

### Clean up material names in the given mesh by removing the '.001' suffix.
def clean_material_names(mesh: Mesh) -> None:
    for j, mat in enumerate(mesh.material_slots):
        if mat.name.endswith(('.0+', ' 0+')):
            mesh.active_material_index = j
            mesh.active_material.name = mat.name[:-len(mat.name.rstrip('0')) - 1]


# This will fix faulty uv coordinates, cats did this a other way which can have unintended consequences, 
# this is the best way i could of think of doing this for the time being, however may need improvements.

def fix_uv_coordinates(context: Context) -> None:
    obj = context.object

    # Check if the object is in Edit Mode
    if obj.mode != 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')

    # Check if the object has any mesh data
    if obj.type == 'MESH' and obj.data:
        bpy.context.view_layer.objects.active = obj
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.average_islands_scale()

        # Switch back to Object Mode
        bpy.ops.object.mode_set(mode='OBJECT')
    else:
        print("Object is not a valid mesh with UV data")

def has_shapekeys(mesh_obj: Object) -> bool:
    return mesh_obj.data.shape_keys is not None

@lru_cache(maxsize=None)
def _get_shape_key_co(shape_key: ShapeKey) -> np.ndarray:
    return np.array([v.co for v in shape_key.data])
    
def simplify_bonename(n: str) -> str:
    return n.lower().translate(dict.fromkeys(map(ord, u" _.")))
    
def get_armature(context: Context, armature_name: Optional[str] = None) -> Optional[Object]:
    if armature_name:
        obj = bpy.data.objects[armature_name]
        if obj.type == "ARMATURE":
            return obj
        else:
            return None
    if context.view_layer.objects.active:
        obj = context.view_layer.objects.active
        if obj.type == "ARMATURE":
            return obj
    return next((obj for obj in context.view_layer.objects if obj.type == 'ARMATURE'), None)

def has_shapekeys(mesh_obj: Object) -> bool:
    return mesh_obj.data.shape_keys is not None

def has_shapekeys(mesh_obj: Object) -> bool:
    return mesh_obj.data.shape_keys is not None

def sort_shape_keys(mesh: Object) -> None:
    print("Starting shape key sorting...")
    if not has_shapekeys(mesh):
        print("No shape keys found. Exiting sort function.")
        return

    order = [
        'Basis',
        'vrc.blink_left',
        'vrc.blink_right',
        'vrc.lowerlid_left',
        'vrc.lowerlid_right',
        'vrc.v_aa',
        'vrc.v_ch',
        'vrc.v_dd',
        'vrc.v_e',
        'vrc.v_ff',
        'vrc.v_ih',
        'vrc.v_kk',
        'vrc.v_nn',
        'vrc.v_oh',
        'vrc.v_ou',
        'vrc.v_pp',
        'vrc.v_rr',
        'vrc.v_sil',
        'vrc.v_ss',
        'vrc.v_th',
    ]

    shape_keys = mesh.data.shape_keys.key_blocks
    print(f"Total shape keys: {len(shape_keys)}")

    # Create a list of shape key names in their current order
    current_order = [key.name for key in shape_keys]

    # Create a new order list
    new_order = []

    # First, add all the keys that are in the predefined order
    for name in order:
        if name in current_order:
            new_order.append(name)
            current_order.remove(name)

    # Then add any remaining keys that weren't in the predefined order
    new_order.extend(current_order)

    print("New order:", new_order)

    # Now, rearrange the shape keys based on the new order
    for i, name in enumerate(new_order):
        index = shape_keys.find(name)
        if index != i:
            print(f"Moving {name} from index {index} to {i}")
            bpy.context.object.active_shape_key_index = index
            while bpy.context.object.active_shape_key_index > i:
                bpy.ops.object.shape_key_move(type='UP')

    print("Shape key sorting completed.")


def get_shapekeys(mesh: Object, prefix: str = '') -> List[tuple]:
    if not has_shapekeys(mesh):
        return []
    return [(key.name, key.name, key.name) for key in mesh.data.shape_keys.key_blocks if key.name != 'Basis' and key.name.startswith(prefix)]
