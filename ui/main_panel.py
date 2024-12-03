import bpy
from typing import Optional
from bpy.types import Panel, Context, UILayout
from ..core.translations import t

CATEGORY_NAME: str = "Avatar Toolkit"

def draw_title(self: Panel) -> None:
    """Draw the main panel title and description"""
    layout: UILayout = self.layout
    box: UILayout = layout.box()
    col: UILayout = box.column(align=True)
    
    # Add a nice header
    row: UILayout = col.row()
    row.scale_y = 1.2
    row.label(text=t("AvatarToolkit.label"), icon='ARMATURE_DATA')
    
    # Description as a flowing paragraph
    desc_col: UILayout = col.column()
    desc_col.scale_y = 0.6
    desc_col.label(text=t("AvatarToolkit.desc1"))
    desc_col.label(text=t("AvatarToolkit.desc2"))
    desc_col.label(text=t("AvatarToolkit.desc3"))
    col.separator()

class AvatarToolKit_PT_AvatarToolkitPanel(Panel):
    """Main panel for Avatar Toolkit containing general information and settings"""
    bl_label = t("AvatarToolkit.label")
    bl_idname = "OBJECT_PT_avatar_toolkit"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY_NAME
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context: Context) -> None:
        """Draw the main panel layout"""
        draw_title(self)
