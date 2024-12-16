# MIT License
# This code was taken from Cats Blender Plugin Unoffical, some of this code is by the original developers, however was improved by myself.
# Didn't think it was necessary to re-make something that works well.

import bpy
from typing import Dict, List, Optional, Tuple, Any, Set
from bpy.types import Operator, Context, Object, ShapeKey
from collections import OrderedDict
from ..core.logging_setup import logger
from ..core.translations import t
from ..core.common import (
    get_active_armature,
    validate_armature,
    get_all_meshes,
    validate_mesh_for_pose
)

class VisemeCache:
    """Caches generated viseme shape data"""
    _cache: Dict = {}
    
    @classmethod
    def get_cached_shape(cls, key: str, mix_data: List) -> Optional[List]:
        cache_key = (key, tuple(tuple(x) for x in mix_data))
        return cls._cache.get(cache_key)
    
    @classmethod 
    def cache_shape(cls, key: str, mix_data: List, shape_data: List) -> None:
        cache_key = (key, tuple(tuple(x) for x in mix_data))
        cls._cache[cache_key] = shape_data

class VisemePreview:
    """Handles viseme preview functionality"""
    _preview_data: Dict = {}
    _active: bool = False
    _preview_shapes: Optional[OrderedDict] = None
    
    @classmethod
    def start_preview(cls, context: Context, mesh: Object, shapes: List[str]) -> bool:
        if not mesh or not mesh.data or not mesh.data.shape_keys:
            return False
            
        cls._active = True
        cls._preview_data = {}
        
        # Store original values
        for shape_key in mesh.data.shape_keys.key_blocks:
            cls._preview_data[shape_key.name] = shape_key.value
            
        # Get properties from avatar_toolkit
        props = context.scene.avatar_toolkit
        shape_a = props.mouth_a
        shape_o = props.mouth_o
        shape_ch = props.mouth_ch

        
        cls._preview_shapes = OrderedDict()
        cls._preview_shapes['vrc.v_aa'] = {'mix': [[(shape_a), (0.9998)]]}
        cls._preview_shapes['vrc.v_ch'] = {'mix': [[(shape_ch), (0.9996)]]}
        cls._preview_shapes['vrc.v_dd'] = {'mix': [[(shape_a), (0.3)], [(shape_ch), (0.7)]]}
        cls._preview_shapes['vrc.v_ih'] = {'mix': [[(shape_ch), (0.7)], [(shape_o), (0.3)]]}
        cls._preview_shapes['vrc.v_ff'] = {'mix': [[(shape_a), (0.2)], [(shape_ch), (0.4)]]}
        cls._preview_shapes['vrc.v_e'] = {'mix': [[(shape_a), (0.5)], [(shape_ch), (0.2)]]}
        cls._preview_shapes['vrc.v_kk'] = {'mix': [[(shape_a), (0.7)], [(shape_ch), (0.4)]]}
        cls._preview_shapes['vrc.v_nn'] = {'mix': [[(shape_a), (0.2)], [(shape_ch), (0.7)]]}
        cls._preview_shapes['vrc.v_oh'] = {'mix': [[(shape_a), (0.2)], [(shape_o), (0.8)]]}
        cls._preview_shapes['vrc.v_ou'] = {'mix': [[(shape_o), (0.9994)]]}
        cls._preview_shapes['vrc.v_pp'] = {'mix': [[(shape_a), (0.0004)], [(shape_o), (0.0004)]]}
        cls._preview_shapes['vrc.v_rr'] = {'mix': [[(shape_ch), (0.5)], [(shape_o), (0.3)]]}
        cls._preview_shapes['vrc.v_sil'] = {'mix': [[(shape_a), (0.0002)], [(shape_ch), (0.0002)]]}
        cls._preview_shapes['vrc.v_ss'] = {'mix': [[(shape_ch), (0.8)]]}
        cls._preview_shapes['vrc.v_th'] = {'mix': [[(shape_a), (0.4)], [(shape_o), (0.15)]]}
        
        return True

    @classmethod
    def update_preview(cls, context: Context) -> None:
        if not cls._active or not cls._preview_shapes:
            return
            
        mesh = context.active_object
        props = context.scene.avatar_toolkit
        viseme_data = cls._preview_shapes.get(props.viseme_preview_selection)
        if viseme_data:
            cls.show_viseme(context, mesh, props.viseme_preview_selection, viseme_data['mix'])
    
    @classmethod
    def show_viseme(cls, context: Context, mesh: Object, viseme_name: str, mix_data: List) -> None:
        if not cls._active:
            return
            
        # Get shape intensity from properties
        intensity = context.scene.avatar_toolkit.shape_intensity
            
        for shape_key in mesh.data.shape_keys.key_blocks:
            shape_key.value = 0
            
        for shape_name, value in mix_data:
            if shape_name in mesh.data.shape_keys.key_blocks:
                # Apply intensity to the preview value
                mesh.data.shape_keys.key_blocks[shape_name].value = value * intensity
                
        context.view_layer.update()

    
    @classmethod
    def end_preview(cls, mesh: Object) -> None:
        if not cls._active:
            return
            
        for shape_name, value in cls._preview_data.items():
            if shape_name in mesh.data.shape_keys.key_blocks:
                mesh.data.shape_keys.key_blocks[shape_name].value = value
                
        cls._active = False
        cls._preview_data.clear()
        cls._preview_shapes = None

class ATOOLKIT_OT_preview_visemes(Operator):
    bl_idname = "avatar_toolkit.preview_visemes"
    bl_label = t("Visemes.preview_label")
    bl_description = t("Visemes.preview_desc")
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    
    @classmethod
    def poll(cls, context: Context) -> bool:
        armature = get_active_armature(context)
        if not armature:
            return False
        valid, _ = validate_armature(armature)
        return valid and context.active_object and context.active_object.type == 'MESH'
    
    def execute(self, context: Context) -> Set[str]:
        props = context.scene.avatar_toolkit
        mesh = context.active_object
        
        if props.viseme_preview_mode:
            VisemePreview.end_preview(mesh)
            props.viseme_preview_mode = False
        else:
            if not mesh.data.shape_keys:
                self.report({'ERROR'}, t("Visemes.error.no_shapekeys"))
                return {'CANCELLED'}
                
            if VisemePreview.start_preview(context, mesh, [props.mouth_a, props.mouth_o, props.mouth_ch]):
                props.viseme_preview_mode = True
                props.viseme_preview_selection = 'vrc.v_aa'
            
        return {'FINISHED'}

def validate_deformation(mesh, mix_data):
    """Validates if shape key deformations are within reasonable ranges"""
    base_coords = [v.co.copy() for v in mesh.data.shape_keys.key_blocks['Basis'].data]
    max_deform = 0
    
    for shape_data in mix_data:
        shape_name, value = shape_data
        if shape_name in mesh.data.shape_keys.key_blocks:
            shape_key = mesh.data.shape_keys.key_blocks[shape_name]
            for i, v in enumerate(shape_key.data):
                deform = (v.co - base_coords[i]).length * value
                max_deform = max(max_deform, deform)
    
    mesh_size = max(mesh.dimensions)
    return max_deform < (mesh_size * 0.4)

class ATOOLKIT_OT_create_visemes(Operator):
    bl_idname = "avatar_toolkit.create_visemes"
    bl_label = t("Visemes.create_label")
    bl_description = t("Visemes.create_desc")
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context: Context) -> bool:
        armature = get_active_armature(context)
        if not armature:
            return False
        valid, _ = validate_armature(armature)
        return valid and context.active_object and context.active_object.type == 'MESH'

    def execute(self, context: Context) -> Set[str]:
        props = context.scene.avatar_toolkit
        mesh = context.active_object
        
        if not mesh.data.shape_keys:
            self.report({'ERROR'}, t("Visemes.error.no_shapekeys"))
            return {'CANCELLED'}
            
        if props.mouth_a == "Basis" or props.mouth_o == "Basis" or props.mouth_ch == "Basis":
            self.report({'ERROR'}, t("Visemes.error.select_shapekeys"))
            return {'CANCELLED'}
            
        try:
            self.create_visemes(context, mesh)
            self.report({'INFO'}, t("Visemes.success"))
            return {'FINISHED'}
        except Exception as e:
            logger.error(f"Error creating visemes: {str(e)}")
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        
    def create_visemes(self, context: Context, mesh: Object) -> None:
        """Creates viseme shape keys by mixing existing shape keys"""
        props = context.scene.avatar_toolkit
        wm = context.window_manager
        
        # Store original shape key names
        shapes = [props.mouth_a, props.mouth_o, props.mouth_ch]
        renamed_shapes = shapes.copy()
        
        # Temporarily rename selected shapes to avoid conflicts
        for shapekey in mesh.data.shape_keys.key_blocks:
            if shapekey.name == props.mouth_a:
                shapekey.name = f"{shapekey.name}_old"
                props.mouth_a = shapekey.name
                renamed_shapes[0] = shapekey.name
            elif shapekey.name == props.mouth_o:
                if props.mouth_a != props.mouth_o:
                    shapekey.name = f"{shapekey.name}_old"
                props.mouth_o = shapekey.name
                renamed_shapes[1] = shapekey.name
            elif shapekey.name == props.mouth_ch:
                if props.mouth_a != props.mouth_ch and props.mouth_o != props.mouth_ch:
                    shapekey.name = f"{shapekey.name}_old"
                props.mouth_ch = shapekey.name
                renamed_shapes[2] = shapekey.name
        
        # Define viseme shape key data
        shapekey_data = OrderedDict()
        shapekey_data['vrc.v_aa'] = {'mix': [[(props.mouth_a), (0.9998)]]}
        shapekey_data['vrc.v_ch'] = {'mix': [[(props.mouth_ch), (0.9996)]]}
        shapekey_data['vrc.v_dd'] = {'mix': [[(props.mouth_a), (0.3)], [(props.mouth_ch), (0.7)]]}
        shapekey_data['vrc.v_ih'] = {'mix': [[(props.mouth_ch), (0.7)], [(props.mouth_o), (0.3)]]}
        shapekey_data['vrc.v_ff'] = {'mix': [[(props.mouth_a), (0.2)], [(props.mouth_ch), (0.4)]]}
        shapekey_data['vrc.v_e'] = {'mix': [[(props.mouth_a), (0.5)], [(props.mouth_ch), (0.2)]]}
        shapekey_data['vrc.v_kk'] = {'mix': [[(props.mouth_a), (0.7)], [(props.mouth_ch), (0.4)]]}
        shapekey_data['vrc.v_nn'] = {'mix': [[(props.mouth_a), (0.2)], [(props.mouth_ch), (0.7)]]}
        shapekey_data['vrc.v_oh'] = {'mix': [[(props.mouth_a), (0.2)], [(props.mouth_o), (0.8)]]}
        shapekey_data['vrc.v_ou'] = {'mix': [[(props.mouth_o), (0.9994)]]}
        shapekey_data['vrc.v_pp'] = {'mix': [[(props.mouth_a), (0.0004)], [(props.mouth_o), (0.0004)]]}
        shapekey_data['vrc.v_rr'] = {'mix': [[(props.mouth_ch), (0.5)], [(props.mouth_o), (0.3)]]}
        shapekey_data['vrc.v_sil'] = {'mix': [[(props.mouth_a), (0.0002)], [(props.mouth_ch), (0.0002)]]}
        shapekey_data['vrc.v_ss'] = {'mix': [[(props.mouth_ch), (0.8)]]}
        shapekey_data['vrc.v_th'] = {'mix': [[(props.mouth_a), (0.4)], [(props.mouth_o), (0.15)]]}
        
        # Create progress tracker
        total_steps = len(shapekey_data)
        wm.progress_begin(0, total_steps)
        
        # Create viseme shape keys
        for index, (key, data) in enumerate(shapekey_data.items()):
            wm.progress_update(index)
            
            # Check cache first
            cached_data = VisemeCache.get_cached_shape(key, data['mix'])
            if cached_data:
                continue
            
            # Create new shape key
            self.mix_shapekey(context, renamed_shapes, data['mix'], key)
            
            # Cache the new shape key data
            shape_data = [v.co.copy() for v in mesh.data.shape_keys.key_blocks[key].data]
            VisemeCache.cache_shape(key, data['mix'], shape_data)
        
        # Restore original shape key names
        self.restore_shape_names(context, mesh, shapes, renamed_shapes)
        
        # Cleanup and finalize
        mesh.active_shape_key_index = 0
        wm.progress_end()
        
    def mix_shapekey(self, context: Context, shapes: List[str], mix_data: List, new_name: str) -> None:
        """Creates a new shape key by mixing existing ones"""
        mesh = context.active_object
        
        # Remove existing shape key if it exists
        if new_name in mesh.data.shape_keys.key_blocks:
            mesh.active_shape_key_index = mesh.data.shape_keys.key_blocks.find(new_name)
            bpy.ops.object.shape_key_remove()
        
        # Reset all shape keys
        for shapekey in mesh.data.shape_keys.key_blocks:
            shapekey.value = 0
        
        # Set mix values
        for shape_name, value in mix_data:
            if shape_name in mesh.data.shape_keys.key_blocks:
                shapekey = mesh.data.shape_keys.key_blocks[shape_name]
                shapekey.value = value
        
        # Create mixed shape key
        mesh.shape_key_add(name=new_name, from_mix=True)
        
        # Reset values and restore shape key settings
        for shapekey in mesh.data.shape_keys.key_blocks:
            shapekey.value = 0
            if shapekey.name in shapes:
                shapekey.slider_max = 1
    
    def restore_shape_names(self, context: Context, mesh: Object, original_names: List[str], current_names: List[str]) -> None:
        """Restores original shape key names"""
        props = context.scene.avatar_toolkit
        
        # Restore mouth_a
        if original_names[0] not in mesh.data.shape_keys.key_blocks:
            shapekey = mesh.data.shape_keys.key_blocks.get(current_names[0])
            if shapekey:
                shapekey.name = original_names[0]
                if current_names[2] == current_names[0]:
                    current_names[2] = original_names[0]
                if current_names[1] == current_names[0]:
                    current_names[1] = original_names[0]
                current_names[0] = original_names[0]
        
        # Restore mouth_o
        if original_names[1] not in mesh.data.shape_keys.key_blocks:
            shapekey = mesh.data.shape_keys.key_blocks.get(current_names[1])
            if shapekey:
                shapekey.name = original_names[1]
                if current_names[2] == current_names[1]:
                    current_names[2] = original_names[1]
                current_names[1] = original_names[1]
        
        # Restore mouth_ch
        if original_names[2] not in mesh.data.shape_keys.key_blocks:
            shapekey = mesh.data.shape_keys.key_blocks.get(current_names[2])
            if shapekey:
                shapekey.name = original_names[2]
                current_names[2] = original_names[2]
        
        # Update properties
        props.mouth_a = current_names[0]
        props.mouth_o = current_names[1]
        props.mouth_ch = current_names[2]
