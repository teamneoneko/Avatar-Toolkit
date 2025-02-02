import bpy
from bpy.types import Panel, Context, UILayout
from ..core.translations import t

class AvatarToolKit_PT_UVPanel(Panel):
    """Main UV Tools panel for Avatar Toolkit"""
    bl_label = t("AvatarToolkit.label")
    bl_idname = "OBJECT_PT_avatar_toolkit_uv_main"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Avatar Toolkit"

    def draw(self, context: Context) -> None:
        layout: UILayout = self.layout
        
        # Add title section
        box: UILayout = layout.box()
        col: UILayout = box.column(align=True)
        row: UILayout = col.row()
        row.scale_y = 1.2
        row.label(text=t("AvatarToolkit.label"), icon='UV')
