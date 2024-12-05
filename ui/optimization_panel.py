import bpy
from typing import Set
from bpy.types import Panel, Context, UILayout, Operator
from .main_panel import AvatarToolKit_PT_AvatarToolkitPanel, CATEGORY_NAME
from ..core.translations import t

class AvatarToolKit_PT_OptimizationPanel(Panel):
    """Panel containing mesh and material optimization tools for avatar optimization"""
    bl_label: str = t("Optimization.label")
    bl_idname: str = "OBJECT_PT_avatar_toolkit_optimization"
    bl_space_type: str = 'VIEW_3D'
    bl_region_type: str = 'UI'
    bl_category: str = CATEGORY_NAME
    bl_parent_id: str = AvatarToolKit_PT_AvatarToolkitPanel.bl_idname
    bl_order: int = 1

    def draw(self, context: Context) -> None:
        """Draws the optimization panel interface with material, mesh cleanup and join mesh tools"""
        layout: UILayout = self.layout
        
        # Materials Box
        materials_box: UILayout = layout.box()
        col: UILayout = materials_box.column(align=True)
        col.label(text=t("Optimization.materials_title"), icon='MATERIAL')
        col.separator(factor=0.5)
                
        # Material Operations
        col.operator("avatar_toolkit.combine_materials", icon='MATERIAL')
        
        # Mesh Cleanup Box
        cleanup_box: UILayout = layout.box()
        col: UILayout = cleanup_box.column(align=True)
        col.label(text=t("Optimization.cleanup_title"), icon='MESH_DATA')
        col.separator(factor=0.5)
        
        # Remove Doubles Row
        row: UILayout = col.row(align=True)
        row.operator("avatar_toolkit.remove_doubles", icon='MESH_DATA')
        row.operator("avatar_toolkit.remove_doubles_advanced", icon='PREFERENCES')
        
        # Join Meshes Box
        join_box: UILayout = layout.box()
        col: UILayout = join_box.column(align=True)
        col.label(text=t("Optimization.join_meshes_title"), icon='OBJECT_DATA')
        col.separator(factor=0.5)
        
        # Join Meshes Row
        row: UILayout = col.row(align=True)
        row.operator("avatar_toolkit.join_all_meshes", icon='OBJECT_DATA')
        row.operator("avatar_toolkit.join_selected_meshes", icon='RESTRICT_SELECT_OFF')
