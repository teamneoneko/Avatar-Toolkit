import bpy
from typing import Set
from bpy.types import Panel, Context, UILayout
from .main_panel import AvatarToolKit_PT_AvatarToolkitPanel, CATEGORY_NAME
from ..core.translations import t

class AvatarToolKit_PT_MMDPanel(Panel):
    """Panel containing MMD bone standardization tools"""
    bl_label = t("MMD.label")
    bl_idname = "OBJECT_PT_avatar_toolkit_mmd"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY_NAME
    bl_parent_id = AvatarToolKit_PT_AvatarToolkitPanel.bl_idname
    bl_order = 3

    def draw(self, context: Context) -> None:
        layout: UILayout = self.layout
        toolkit = context.scene.avatar_toolkit
        
        # Add merge twist bones option
        layout.prop(toolkit, "keep_twist_bones")
        layout.operator("avatar_toolkit.standardize_mmd", icon='BONE_DATA')
