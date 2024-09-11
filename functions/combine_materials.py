import bpy
import re
from typing import List, Tuple, Optional, Set, Dict
from bpy.types import Material, Operator, Context, Object, NodeTree
from ..core.common import clean_material_names, get_selected_armature, is_valid_armature, get_all_meshes, init_progress, update_progress, finish_progress
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

def consolidate_textures(node_tree1: NodeTree, node_tree2: NodeTree) -> None:
    for node1 in node_tree1.nodes:
        if node1.type == 'TEX_IMAGE':
            for node2 in node_tree2.nodes:
                if (node2.type == 'TEX_IMAGE' and
                    node1.image == node2.image):
                    consolidate_nodes(node1, node2)
                    node2.image = node1.image
        elif node1.type == 'GROUP':
            if node1.node_tree and node2.node_tree:
                consolidate_textures(node1.node_tree, node2.node_tree)

def color_match(col1: Tuple[float, float, float, float], col2: Tuple[float, float, float, float], tolerance: float = 0.01) -> bool:
    return all(abs(c1 - c2) < tolerance for c1, c2 in zip(col1, col2))

def materials_match(mat1: Material, mat2: Material, tolerance: float = 0.01) -> bool:
    if not color_match(mat1.diffuse_color, mat2.diffuse_color, tolerance):
        return False
    
    if abs(mat1.roughness - mat2.roughness) > tolerance:
        return False
    
    if mat1.node_tree and mat2.node_tree:
        consolidate_textures(mat1.node_tree, mat2.node_tree)
    
    return True

def get_base_name(name: str) -> str:
    mat_match = re.match(r"^(.*)\.\d{3}$", name)
    return mat_match.group(1) if mat_match else name

@register_wrap
class AvatarToolKit_OT_CombineMaterials(Operator):
    bl_idname = "avatar_toolkit.combine_materials"
    bl_label = t("Optimization.combine_materials.label")
    bl_description = t("Optimization.combine_materials.desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        armature = get_selected_armature(context)
        return armature is not None and is_valid_armature(armature)
    
    def execute(self, context: Context) -> Set[str]:
        armature = get_selected_armature(context)
        if not armature:
            self.report({'WARNING'}, t("Optimization.no_armature_selected"))
            return {'CANCELLED'}
        
        context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode='OBJECT')
        
        meshes = get_all_meshes(context)
        if not meshes:
            self.report({'WARNING'}, t("Optimization.no_meshes_found"))
            return {'CANCELLED'}
        
        init_progress(context, 5)  # 5 steps in total
        
        update_progress(self, context, t("Optimization.consolidating_materials"))
        self.consolidate_materials(meshes)
        
        update_progress(self, context, t("Optimization.cleaning_material_slots"))
        self.clean_material_slots(meshes)
        
        update_progress(self, context, t("Optimization.cleaning_material_names"))
        self.clean_material_names()
        
        update_progress(self, context, t("Optimization.clearing_unused_data"))
        self.clear_unused_data_blocks()
        
        update_progress(self, context, t("Optimization.finalizing"))
        finish_progress(context)
        
        return {'FINISHED'}

    def consolidate_materials(self, meshes: List[Object]) -> None:
        mat_mapping: Dict[str, Material] = {}
        num_combined: int = 0
        for mesh in meshes:
            for slot in mesh.material_slots:
                mat: Optional[Material] = slot.material
                if mat:
                    base_name: str = get_base_name(mat.name)
                    
                    if base_name in mat_mapping:
                        base_mat: Material = mat_mapping[base_name]
                        try:
                            if materials_match(base_mat, mat):
                                consolidate_textures(base_mat.node_tree, mat.node_tree)
                                num_combined += 1
                                slot.material = base_mat
                        except AttributeError:
                            self.report({'WARNING'}, t("Optimization.material_attribute_mismatch").format(material_name=mat.name))
                            continue
                    else:
                        mat_mapping[base_name] = mat
        
        self.report({'INFO'}, t("Optimization.materials_combined").format(num_combined=num_combined))

    def clean_material_slots(self, meshes: List[Object]) -> None:
        for obj in meshes:
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.material_slot_remove_unused()
            obj.select_set(False)

    def clean_material_names(self) -> None:
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                clean_material_names(obj)

    def clear_unused_data_blocks(self) -> None:
        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

