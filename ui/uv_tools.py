import bpy
from bpy.types import Panel, Context, UILayout
from ..core.translations import t

class AvatarToolKit_PT_UVTools(Panel):
    """UV Tools panel containing UV manipulation operators"""
    bl_label = t("Tools.label")
    bl_idname = "OBJECT_PT_avatar_toolkit_uv_tools"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Avatar Toolkit"
    bl_parent_id = "OBJECT_PT_avatar_toolkit_uv_main" 
    bl_order = 3
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context: Context) -> None:
        layout: UILayout = self.layout
        
        tools_box: UILayout = layout.box()
        col: UILayout = tools_box.column(align=True)
        col.label(text=t("Tools.uv_title"), icon='UV')
        col.separator(factor=0.5)
        
        row: UILayout = col.row(align=True)
        row.operator("avatar_toolkit.align_uv_edges_to_target", 
                    text=t("UVTools.align_edges"), 
                    icon='GP_MULTIFRAME_EDITING')
