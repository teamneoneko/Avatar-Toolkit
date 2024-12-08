import bpy
from typing import Set
from bpy.types import Panel, Context, UILayout, Operator
from .main_panel import AvatarToolKit_PT_AvatarToolkitPanel, CATEGORY_NAME
from ..core.translations import t

class AvatarToolKit_PT_MMDPanel(Panel):
    """Panel containing MMD conversion and optimization tools"""
    bl_label = t("MMD.label")
    bl_idname = "OBJECT_PT_avatar_toolkit_mmd"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY_NAME
    bl_parent_id = AvatarToolKit_PT_AvatarToolkitPanel.bl_idname
    bl_order = 2

    def draw(self, context: Context) -> None:
        layout: UILayout = self.layout
        
        # Bone Standardization Box
        bone_box: UILayout = layout.box()
        col: UILayout = bone_box.column(align=True)
        col.label(text=t("MMD.bone_standardization"), icon='ARMATURE_DATA')
        col.separator(factor=0.5)
        col.operator("avatar_toolkit.mmd_standardize_bones", icon='BONE_DATA')
        
        # Weight Processing Box
        weight_box: UILayout = layout.box()
        col = weight_box.column(align=True)
        col.label(text=t("MMD.weight_processing"), icon='GROUP_VERTEX')
        col.separator(factor=0.5)
        col.operator("avatar_toolkit.mmd_process_weights", icon='WPAINT_HLT')
        
        # Hierarchy Box
        hierarchy_box: UILayout = layout.box()
        col = hierarchy_box.column(align=True)
        col.label(text=t("MMD.hierarchy"), icon='OUTLINER')
        col.separator(factor=0.5)
        col.operator("avatar_toolkit.mmd_fix_hierarchy", icon='CONSTRAINT_BONE')
        
        # Cleanup Box
        cleanup_box: UILayout = layout.box()
        col = cleanup_box.column(align=True)
        col.label(text=t("MMD.cleanup"), icon='BRUSH_DATA')
        col.separator(factor=0.5)
        col.operator("avatar_toolkit.mmd_cleanup_armature", icon='MODIFIER')
