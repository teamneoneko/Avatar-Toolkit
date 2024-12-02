import bpy
from ..core.translations import t
from .main_panel import draw_title

class UVTools_PT_MainPanel(bpy.types.Panel):
    bl_label = t("AvatarToolkit.label")
    bl_idname = "OBJECT_PT_avatar_toolkit_uv"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Avatar Toolkit"

    def draw(self: bpy.types.Panel, context: bpy.types.Context):
        layout = self.layout
        draw_title(self)
