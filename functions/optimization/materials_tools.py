import bpy
import re
from typing import Set, Dict, List, Optional, Tuple
from bpy.types import (
    Operator, 
    Context, 
    Object, 
    Material, 
    NodeTree,
    ShaderNodeTexImage
)
from ...core.logging_setup import logger
from ...core.translations import t
from ...core.common import (
    get_active_armature,
    get_all_meshes,
    validate_armature,
    clear_unused_data_blocks,
    ProgressTracker
)

def textures_match(tex1: ShaderNodeTexImage, tex2: ShaderNodeTexImage) -> bool:
    """Compare two texture nodes for matching properties and image data"""
    return tex1.image == tex2.image and tex1.extension == tex2.extension

def consolidate_nodes(node1: ShaderNodeTexImage, node2: ShaderNodeTexImage) -> None:
    """Transfer properties from one texture node to another to ensure consistency"""
    node2.color_space = node1.color_space
    node2.coordinates = node1.coordinates

def consolidate_textures(node_tree1: NodeTree, node_tree2: NodeTree) -> None:
    """Synchronize texture nodes between two material node trees"""
    for node1 in node_tree1.nodes:
        if node1.type == 'TEX_IMAGE':
            for node2 in node_tree2.nodes:
                if (node2.type == 'TEX_IMAGE' and node1.image == node2.image):
                    consolidate_nodes(node1, node2)
                    node2.image = node1.image
        elif node1.type == 'GROUP':
            if node1.node_tree and node2.node_tree:
                consolidate_textures(node1.node_tree, node2.node_tree)

def color_match(col1: Tuple[float, ...], col2: Tuple[float, ...], tolerance: float = 0.01) -> bool:
    """Compare two color values within a specified tolerance"""
    return all(abs(c1 - c2) < tolerance for c1, c2 in zip(col1, col2))

def materials_match(mat1: Material, mat2: Material, tolerance: float = 0.01) -> bool:
    """Compare two materials for matching properties within tolerance"""
    if not color_match(mat1.diffuse_color, mat2.diffuse_color, tolerance):
        return False
    
    if abs(mat1.roughness - mat2.roughness) > tolerance:
        return False
        
    if abs(mat1.metallic - mat2.metallic) > tolerance:
        return False
        
    if abs(mat1.alpha_threshold - mat2.alpha_threshold) > tolerance:
        return False
        
    if not color_match(mat1.emission_color, mat2.emission_color, tolerance):
        return False
    
    if mat1.node_tree and mat2.node_tree:
        consolidate_textures(mat1.node_tree, mat2.node_tree)
    
    return True

def get_base_name(name: str) -> str:
    """Extract the base material name by removing numeric suffixes"""
    mat_match = re.match(r"^(.*)\.\d{3}$", name)
    return mat_match.group(1) if mat_match else name

class AvatarToolkit_OT_CombineMaterials(Operator):
    """Operator for combining similar materials to reduce duplicate materials"""
    bl_idname: str = "avatar_toolkit.combine_materials"
    bl_label: str = t("Optimization.combine_materials")
    bl_description: str = t("Optimization.combine_materials_desc")
    bl_options: Set[str] = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        """Check if the operator can be executed"""
        armature = get_active_armature(context)
        if not armature:
            return False
        valid, _ = validate_armature(armature)
        return valid

    def execute(self, context: Context) -> Set[str]:
        """Execute the material combination operation"""
        try:
            armature = get_active_armature(context)
            meshes = get_all_meshes(context)
            
            if not meshes:
                self.report({'WARNING'}, t("Optimization.no_meshes"))
                return {'CANCELLED'}
                
            if not any(mesh.material_slots for mesh in meshes):
                self.report({'WARNING'}, t("Optimization.no_materials"))
                return {'CANCELLED'}

            with ProgressTracker(context, 4, "Combining Materials") as progress:         
                try:
                    num_combined = self.consolidate_materials(meshes)
                except Exception as e:
                    logger.error(f"Material consolidation failed: {str(e)}")
                    self.report({'ERROR'}, t("Optimization.error.consolidation"))
                    return {'CANCELLED'}
                progress.step("Consolidated materials")
                
                try:
                    num_cleaned = self.clean_material_slots(meshes)
                except Exception as e:
                    logger.error(f"Material slot cleanup failed: {str(e)}")
                    self.report({'ERROR'}, t("Optimization.error.slot_cleanup"))
                    return {'CANCELLED'}
                progress.step("Cleaned material slots")
                
                try:
                    num_removed = clear_unused_data_blocks(self)
                except Exception as e:
                    logger.error(f"Data block cleanup failed: {str(e)}")
                    self.report({'ERROR'}, t("Optimization.error.data_cleanup"))
                    return {'CANCELLED'}
                progress.step("Removed unused data blocks")
                
                self.report({'INFO'}, t("Optimization.materials_combined", 
                    combined=num_combined, 
                    cleaned=num_cleaned,
                    removed=num_removed))
                
                return {'FINISHED'}
                
        except Exception as e:
            logger.error(f"Failed to combine materials: {str(e)}")
            self.report({'ERROR'}, t("Optimization.error.combine_materials", error=str(e)))
            return {'CANCELLED'}

    def consolidate_materials(self, meshes: List[Object]) -> int:
        """Consolidate similar materials across all meshes"""
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
                            logger.warning(f"Material attribute mismatch: {mat.name}")
                            continue
                    else:
                        mat_mapping[base_name] = mat
        
        return num_combined

    def clean_material_slots(self, meshes: List[Object]) -> int:
        """Remove unused material slots from meshes"""
        cleaned_slots = 0
        for obj in meshes:
            initial_slots = len(obj.material_slots)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.material_slot_remove_unused()
            cleaned_slots += initial_slots - len(obj.material_slots)
        return cleaned_slots
