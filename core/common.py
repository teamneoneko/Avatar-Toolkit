import bpy

import numpy as np
import threading
import time
import webbrowser
import typing
import struct
from io import BytesIO

from .dictionaries import bone_names
from ..core.register import register_wrap
from typing import List, Optional, Tuple
from bpy.types import Object, ShapeKey, Mesh, Context, Material, PropertyGroup
from functools import lru_cache
from bpy.props import PointerProperty, IntProperty, StringProperty
from bpy.utils import register_class




class SceneMatClass(PropertyGroup):
    mat: PointerProperty(type=Material)

register_class(SceneMatClass)

class MaterialListBool:
    #For the love that is holy do not ever touch these. If this was java I would make these private
    #They should only be accessed via context.scene.texture_atlas_Has_Mat_List_Shown
    #This is so we know if the materials are up to date. messing with these variables directly will make the thing blow up.
    
    #The only exception to this is the ExpandSection_Materials operator which populates this with new data once the materials have changed and need reloading.
    old_list: dict[str,list[Material]] = {}
    bool_material_list_expand: dict[str,bool] = {}

    def set_bool(self, value: bool) -> None:
        MaterialListBool.bool_material_list_expand[bpy.context.scene.name] = value
        if value == False:
            MaterialListBool.old_list[bpy.context.scene.name] = []

    def get_bool(self) -> bool:
            newlist: list[Material] = []
            for obj in bpy.context.scene.objects:
                if len(obj.material_slots)>0:
                    for mat_slot in obj.material_slots:
                        if mat_slot.material:
                            if mat_slot.material not in newlist:
                                newlist.append(mat_slot.material)
            
            still_the_same: bool = True
            if bpy.context.scene.name in MaterialListBool.old_list:
                for item in newlist:
                    if item not in MaterialListBool.old_list[bpy.context.scene.name]:
                        still_the_same = False
                        break
                for item in MaterialListBool.old_list[bpy.context.scene.name]:
                    if item not in newlist:
                        still_the_same = False
                        break
            else:
                still_the_same = False
            MaterialListBool.bool_material_list_expand[bpy.context.scene.name] = still_the_same
            
            return MaterialListBool.bool_material_list_expand[bpy.context.scene.name]


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

    # Store current mode and selection
    current_mode = context.mode
    current_active = context.view_layer.objects.active
    current_selected = context.selected_objects.copy()

    # Ensure we're in object mode and select the object
    bpy.ops.object.mode_set(mode='OBJECT')
    obj.select_set(True)
    context.view_layer.objects.active = obj

    # Check if the object has any mesh data
    if obj.type == 'MESH' and obj.data:

        # Switch to Edit Mode
        bpy.ops.object.mode_set(mode='EDIT')

        # Select all UVs
        bpy.ops.mesh.select_all(action='SELECT')

        # Try to find UV Editor area, fall back to 3D View if not found
        area = next((area for area in context.screen.areas if area.type == 'UV_EDITOR'), None)
        if not area:
            area = next((area for area in context.screen.areas if area.type == 'VIEW_3D'), None)

        # Get the region and space data
        region = next((region for region in area.regions if region.type == 'WINDOW'), None)
        space_data = area.spaces.active

        # Create a context override
        override = {
            'area': area,
            'region': region,
            'space_data': space_data,
            'edit_object': obj,
            'active_object': obj,
            'selected_objects': [obj],
            'mode': 'EDIT_MESH',
        }

        try:
            # Ensure UVs are selected
            bpy.ops.uv.select_all(override, action='SELECT')
            # Average UV island scales
            bpy.ops.uv.average_islands_scale(override)
        except Exception as e:
            print(f"UV Fix - Error during UV scaling: {str(e)}")

        # Switch back to Object Mode
        bpy.ops.object.mode_set(mode='OBJECT')
        print("UV Fix - Switched back to Object Mode")

        # Restore previous selection and active object
        for sel_obj in current_selected:
            sel_obj.select_set(True)
        context.view_layer.objects.active = current_active
    else:
        print("UV Fix - Object is not a valid mesh with UV data")

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
    armatures = [(obj.name, obj.name, "") for obj in bpy.data.objects if obj.type == 'ARMATURE']
    if not armatures:
        return [('NONE', 'No Armature', '')]
    return armatures

def get_armatures_that_are_not_selected(self, context: Context) -> List[Tuple[str, str, str]]:
    armatures = [(obj.name, obj.name, "") for obj in bpy.data.objects if ((obj.type == 'ARMATURE') and (obj.name != context.scene.selected_armature))]
    if not armatures:
        return [('NONE', 'No Other Armature', '')]
    return armatures

def get_selected_armature(context: Context) -> Optional[Object]:
    try:
        if hasattr(context.scene, 'selected_armature'):
            armature_name = context.scene.selected_armature
            if isinstance(armature_name, bytes):
                try:
                    armature_name = armature_name.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        armature_name = armature_name.decode('gbk')  # For Chinese characters
                    except UnicodeDecodeError:
                        try:
                            armature_name = armature_name.decode('shift-jis')
                        except UnicodeDecodeError:
                            armature_name = armature_name.decode('latin1')
            
            if armature_name:
                armature = bpy.data.objects.get(str(armature_name))
                if is_valid_armature(armature):
                    return armature
    except Exception:
        pass
    return None

def get_merge_armature_source(context: Context) -> Optional[Object]:
    try:
        if hasattr(context.scene, 'merge_armature_source'):
            source_name = context.scene.merge_armature_source
            if isinstance(source_name, bytes):
                try:
                    source_name = source_name.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        source_name = source_name.decode('shift-jis')
                    except UnicodeDecodeError:
                        source_name = source_name.decode('latin1', errors='ignore')
            
            if source_name:
                return bpy.data.objects.get(str(source_name))
    except Exception:
        pass
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

def apply_shapekey_to_basis(context: bpy.types.Context, obj: bpy.types.Object, shape_key_name: str, delete_old: bool = False) -> bool:
    if shape_key_name not in obj.data.shape_keys.key_blocks:
       return False
    shapekeynum = obj.data.shape_keys.key_blocks.find(shape_key_name)

    bpy.ops.object.mode_set(mode="EDIT")

    bpy.ops.mesh.select_all(action='SELECT')


    obj.active_shape_key_index = 0
    bpy.ops.mesh.blend_from_shape(shape = shape_key_name, add=True, blend=1)
    obj.active_shape_key_index = shapekeynum
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.blend_from_shape(shape = shape_key_name, add=True, blend=-2)


    bpy.ops.mesh.select_all(action='DESELECT')

    bpy.ops.object.mode_set(mode="OBJECT")
    print("blended!")

    if delete_old:
        obj.active_shape_key_index = shapekeynum
        bpy.ops.object.shape_key_remove(all=False)
    else:
        mesh: bpy.types.Mesh = obj.data
        mesh.shape_keys.key_blocks[shape_key_name].name = shape_key_name + "_reversed"
    return True

def apply_pose_as_rest(context: Context, armature_obj: Object, meshes: list[Object]) -> bool:
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
    
def get_all_meshes(context: Context) -> List[Object]:
    armature = get_selected_armature(context)
    if armature and is_valid_armature(armature):
        return [obj for obj in bpy.data.objects if obj.type == 'MESH' and obj.parent == armature]
    return []

def get_mesh_items(self, context):
    return [(obj.name, obj.name, "") for obj in get_all_meshes(context)]

def open_web_after_delay_multi_threaded(delay: typing.Optional[float] = 1.0, url: typing.Union[str, typing.Any] = ""):
    thread = threading.Thread(target=open_web_after_delay,args=[delay,url],name="open_browser_thread")
    thread.start()

def open_web_after_delay(delay, url):
    print("opening browser in "+str(delay)+" seconds.")
    time.sleep(delay)
    
    webbrowser.open_new_tab(url)

def duplicatebone(b: bpy.types.EditBone) -> bpy.types.EditBone:
    arm = bpy.context.object.data
    cb = arm.edit_bones.new(b.name)

    cb.head = b.head
    cb.tail = b.tail
    cb.matrix = b.matrix
    cb.parent = b.parent
    return cb

def has_shapekeys(mesh_obj: Object) -> bool:
    return mesh_obj.data.shape_keys is not None

def sort_shape_keys(mesh: Object) -> None:
    print("Starting shape key sorting...")
    if not has_shapekeys(mesh):
        print("No shape keys found. Exiting sort function.")
        return

    # Set the mesh as the active object
    bpy.context.view_layer.objects.active = mesh
    bpy.ops.object.mode_set(mode='OBJECT')

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
            mesh.active_shape_key_index = index
            while mesh.active_shape_key_index > i:
                bpy.ops.object.shape_key_move(type='UP')

    print("Shape key sorting completed.")

def get_shapekeys(mesh: Object, prefix: str = '') -> List[tuple]:
    if not has_shapekeys(mesh):
        return []
    return [(key.name, key.name, key.name) for key in mesh.data.shape_keys.key_blocks if key.name != 'Basis' and key.name.startswith(prefix)]

def remove_default_objects():
    for obj in bpy.data.objects:
        if obj.name in ["Camera", "Light", "Cube"]:
            bpy.data.objects.remove(obj, do_unlink=True)

def init_progress(context, steps):
    context.window_manager.progress_begin(0, 100)
    context.scene.avatar_toolkit_progress_steps = steps
    context.scene.avatar_toolkit_progress_current = 0

def update_progress(self, context, message):
    context.scene.avatar_toolkit_progress_current += 1
    progress = (context.scene.avatar_toolkit_progress_current / context.scene.avatar_toolkit_progress_steps) * 100
    context.window_manager.progress_update(progress)
    context.area.header_text_set(message)
    self.report({'INFO'}, message)

def finish_progress(context):
    context.window_manager.progress_end()
    context.area.header_text_set(None)

def transfer_vertex_weights(context: Context, obj: bpy.types.Object, source_group: str, target_group: str, delete_source_group: bool = True) -> bool:
    # Create and configure the Vertex Weight Mix modifier
    modifier = obj.modifiers.new(name="merge_weights", type="VERTEX_WEIGHT_MIX")
    modifier.show_viewport = True
    modifier.show_render = True
    modifier.mix_set = 'B'  # Replace weights in A with weights from B
    modifier.vertex_group_a = target_group
    modifier.vertex_group_b = source_group
    modifier.mask_constant = 1.0

    # Ensure we're in Object Mode
    bpy.ops.object.mode_set(mode='OBJECT')

    # Deselect all objects and select only our target object
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    context.view_layer.objects.active = obj

    # Move modifier to the top of the stack if necessary
    if len(obj.modifiers) > 1:
        obj.modifiers.move(obj.modifiers.find(modifier.name), 0)

    # Apply modifier
    bpy.ops.object.modifier_apply(modifier=modifier.name)

    # Clean up
    if delete_source_group and source_group in obj.vertex_groups:
        obj.vertex_groups.remove(obj.vertex_groups[source_group])

    return True

#Binary tools

import ctypes
def ReadCSharp_str(data: BytesIO) -> str:
    return data.read(read7bitEncoded_int(data)).decode('utf-16-le')

def WriteCSharp_str(data: BytesIO, string: str) -> str:
    write7bitEncoded_int(len(string)*2)
    return data.write(string.encode("utf-16-le"))

def read7bitEncoded_ulong(data: BytesIO) -> np.int64:
        num: ctypes.c_uint = ctypes.c_uint(0)
        num2: int = 0
        flag: bool = True
        
        while (flag):
            b: ctypes.c_ubyte = ctypes.c_ubyte(struct.unpack('<B', data.read(1))[0])
            flag = ((b & 128) > 0)
            num |= ((b & 127) << num2)
            num2 += 7
            if not flag:
                break

        return num

def read7bitEncoded_int(data: BytesIO) -> ctypes.c_int:
        num: ctypes.c_int = ctypes.c_int(0)
        num2:ctypes.c_int = ctypes.c_int(0)
        while (num2 != 35):
            b: ctypes.c_ubyte = ctypes.c_ubyte(struct.unpack('<B', data.read(1))[0])
            num |= int(b & 127) << num2
            num2 += 7
            if ((b & 128) == 0):
                return num
        return -1

def write7bitEncoded_ulong(data: BytesIO, integer: ctypes.c_ulong) -> None:
    while integer > ctypes.c_ulong(0):
        b: ctypes.c_ubyte = ctypes.c_ubyte(integer & ctypes.c_ulong(127))
        integer >>= 7
        if integer > ctypes.c_ulong(0):
            b |= 128
        data.write(b)
        if integer <= ctypes.c_ulong(0):
            return

def write7bitEncoded_int(data: BytesIO, value: ctypes.c_int) -> None:
    num: ctypes.c_uint = ctypes.c_uint(value)
    while(num >= ctypes.c_ubyte(128)):
        data.write(ctypes.c_ubyte(num | ctypes.c_ubyte(128)))
        num >>= 7
    data.Write(ctypes.c_ubyte(num))


#encoding FrooxEngine/C# types in binary:





