import bpy
from typing import Set
from bpy.types import Panel, Context, UILayout, Operator
from .main_panel import AvatarToolKit_PT_AvatarToolkitPanel, CATEGORY_NAME
from ..core.translations import t

class AvatarToolKit_PT_ToolsPanel(Panel):
    """Panel containing various tools for avatar customization and optimization"""
    bl_label: str = t("Tools.label")
    bl_idname: str = "OBJECT_PT_avatar_toolkit_tools"
    bl_space_type: str = 'VIEW_3D'
    bl_region_type: str = 'UI'
    bl_category: str = CATEGORY_NAME
    bl_parent_id: str = AvatarToolKit_PT_AvatarToolkitPanel.bl_idname
    bl_order: int = 2

    def draw(self, context: Context) -> None:
        """Draw the tools panel interface"""
        layout: UILayout = self.layout
        
        # General Tools
        tools_box: UILayout = layout.box()
        col: UILayout = tools_box.column(align=True)
        col.label(text=t("Tools.general_title"), icon='TOOL_SETTINGS')
        col.separator(factor=0.5)
        col.operator("avatar_toolkit.convert_resonite", text=t("Tools.convert_resonite"), icon='EXPORT')
        
        # Separation Tools
        sep_box: UILayout = layout.box()
        col = sep_box.column(align=True)
        col.label(text=t("Tools.separate_title"), icon='MOD_EXPLODE')
        col.separator(factor=0.5)
        row: UILayout = col.row(align=True)
        row.operator("avatar_toolkit.separate_materials", text=t("Tools.separate_materials"), icon='MATERIAL')
        row.operator("avatar_toolkit.separate_loose", text=t("Tools.separate_loose"), icon='MESH_DATA')
        
        # Bone Tools
        bone_box: UILayout = layout.box()
        col = bone_box.column(align=True)
        col.label(text=t("Tools.bone_title"), icon='BONE_DATA')
        col.separator(factor=0.5)
        col.operator("avatar_toolkit.create_digitigrade", text=t("Tools.create_digitigrade"), icon='BONE_DATA')
        
        # Weight Tools
        weight_box: UILayout = bone_box.box()
        col = weight_box.column(align=True)
        col.prop(context.scene.avatar_toolkit, "merge_twist_bones", text=t("Tools.merge_twist_bones"))
        row = col.row(align=True)
        row.operator("avatar_toolkit.clean_weights", text=t("Tools.clean_weights"), icon='GROUP_BONE')
        row.operator("avatar_toolkit.clean_constraints", text=t("Tools.clean_constraints"), icon='CONSTRAINT_BONE')
        
        # Merge Tools
        merge_box: UILayout = layout.box()
        col = merge_box.column(align=True)
        col.label(text=t("Tools.merge_title"), icon='AUTOMERGE_ON')
        col.separator(factor=0.5)
        row = col.row(align=True)
        row.operator("avatar_toolkit.merge_to_active", text=t("Tools.merge_to_active"), icon='BONE_DATA')
        row.operator("avatar_toolkit.merge_to_parent", text=t("Tools.merge_to_parent"), icon='BONE_DATA')
        col.operator("avatar_toolkit.connect_bones", text=t("Tools.connect_bones"), icon='BONE_DATA')
        
        # Additional Tools
        extra_box: UILayout = layout.box()
        col = extra_box.column(align=True)
        col.label(text=t("Tools.additional_title"), icon='TOOL_SETTINGS')
        col.separator(factor=0.5)
        col.operator("avatar_toolkit.apply_transforms", text=t("Tools.apply_transforms"), icon='OBJECT_DATA')
        col.operator("avatar_toolkit.clean_shapekeys", text=t("Tools.clean_shapekeys"), icon='SHAPEKEY_DATA')
