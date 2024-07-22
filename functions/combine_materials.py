import bpy
import re
from typing import List, Tuple, Optional
from bpy.types import Material, Operator, Context, Object
from ..core.common import clean_material_names, get_selected_armature
from ..core.register import register_wrap
from ..functions.translations import t

def textures_match(tex1: bpy.types.ImageTexture, tex2: bpy.types.ImageTexture) -> bool:
    return tex1.image == tex2.image and tex1.extension == tex2.extension

def consolidate_nodes(node1: bpy.types.ShaderNodeTexImage, node2: bpy.types.ShaderNodeTexImage) -> None:
    node2.color_space = node1.color_space
    node2.coordinates = node1.coordinates

def copy_tex_nodes(mat1: Material, mat2: Material) -> None:
    for node1 in mat1.node_tree.nodes:
        if node1.type == 'TEX_IMAGE':
            node2 = mat2.node_tree.nodes.get(node1.name)
            if node2:
                node2.mapping = node1.mapping
                node2.projection = node1.projection

def consolidate_textures(mat1: Material, mat2: Material) -> None:
    if mat1.node_tree and mat2.node_tree:
        for node1 in mat1.node_tree.nodes:
            if node1.type == 'TEX_IMAGE':
                if node1.node_tree:
                    consolidate_textures(node1.node_tree, mat2.node_tree)
                
                for node2 in mat2.node_tree.nodes:
                    if (node2.type == 'TEX_IMAGE' and
                        node1.image == node2.image):
                        consolidate_nodes(node1, node2)
                        node2.image = node1.image
                        copy_tex_nodes(mat1, mat2)

def color_match(col1: Tuple[float, float, float, float], col2: Tuple[float, float, float, float], tolerance: float = 0.01) -> bool:
    return abs(col1[0] - col2[0]) < tolerance

def materials_match(mat1: Material, mat2: Material, tolerance: float = 0.01) -> bool:
    if not color_match(mat1.diffuse_color, mat2.diffuse_color, tolerance):
        return False
    
    if mat1.roughness != mat2.roughness:
        return False
    
    consolidate_textures(mat1, mat2)
    
    return True

def get_base_name(name: str) -> str:
    mat_match = re.match(r"^(.*)\.\d{3}$", name)
    return mat_match.group(1) if mat_match else name

def report_consolidated(self: Operator, num_combined: int) -> None:
    self.report({'INFO'}, f"Combined {num_combined} materials")

@register_wrap
class CombineMaterials(Operator):
    bl_idname = "avatar_toolkit.combine_materials"
    bl_label = t("Optimization.combine_materials.label")
    bl_description = t("Optimization.combine_materials.desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return context.active_object is not None and get_selected_armature(context) is not None
    
    def execute(self, context: Context) -> set:
        bpy.ops.object.mode_set(mode='OBJECT')
        
        armature = get_selected_armature(context)
        if not armature:
            self.report({'WARNING'}, "No armature selected")
            return {'CANCELLED'}
        
        meshes: List[Object] = [obj for obj in bpy.data.objects if obj.type == 'MESH' and 'Armature' in obj.modifiers and obj.modifiers['Armature'].object == armature]
        if not meshes:
            self.report({'WARNING'}, "No meshes found for the selected armature")
            return {'CANCELLED'}
        
        bpy.ops.object.mode_set(mode='OBJECT')
        self.consolidate_materials(meshes)
        self.remove_unused_materials()
        self.cleanmatslots()
        self.clean_material_names()
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.context.view_layer.objects.active = armature
        
        return {'FINISHED'}

    def consolidate_materials(self, objects: List[Object]) -> None:
        mat_mapping: dict = {}
        num_combined: int = 0
        for ob in objects:
            for slot in ob.material_slots:
                mat: Optional[Material] = slot.material
                if mat:
                    base_name: str = get_base_name(mat.name)
                    
                    if base_name in mat_mapping:
                        base_mat: Material = mat_mapping[base_name]
                        if materials_match(base_mat, mat):
                            consolidate_textures(base_mat, mat)
                            num_combined += 1
                            slot.material = base_mat
                    else:
                        mat_mapping[base_name] = mat
        
        report_consolidated(self, num_combined)
    
    def remove_unused_materials(self) -> None:
        for mat in bpy.data.materials:
            if not any(obj for obj in bpy.data.objects if obj.material_slots and mat.name in obj.material_slots):
                bpy.data.materials.remove(mat, do_unlink=True)
    
    def cleanmatslots(self) -> None:
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.material_slot_remove_unused()
                obj.select_set(False)
    
    def clean_material_names(self) -> None:
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                clean_material_names(obj)
