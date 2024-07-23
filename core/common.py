import bpy
import numpy as np
from .dictionaries import bone_names

from typing import List, Optional, Tuple
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

def get_armatures(self, context: Context) -> List[Tuple[str, str, str]]:
    return [(obj.name, obj.name, "") for obj in bpy.data.objects if obj.type == 'ARMATURE']

def get_selected_armature(context: Context) -> Optional[Object]:
    if context.scene.selected_armature:
        armature = bpy.data.objects.get(context.scene.selected_armature)
        if is_valid_armature(armature):
            return armature
    return None

def set_selected_armature(context: Context, armature: Optional[Object]) -> None:
    context.scene.selected_armature = armature.name if armature else ""

def is_valid_armature(armature: Object) -> bool:
    if not armature or armature.type != 'ARMATURE':
        return False
    if not armature.data or not armature.data.bones:
        return False
    return True

def select_current_armature(context: Context) -> bool:
    armature = get_selected_armature(context)
    if armature:
        bpy.ops.object.select_all(action='DESELECT')
        armature.select_set(True)
        context.view_layer.objects.active = armature
        return True
    return False

def get_all_meshes(context: Context) -> List[Object]:
    armature = get_selected_armature(context)
    if armature and is_valid_armature(armature):
        return [obj for obj in bpy.data.objects if obj.type == 'MESH' and obj.parent == armature]
    return []
