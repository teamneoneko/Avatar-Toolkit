import bpy
from ..core.translations import t

CATEGORY_NAME = "Avatar Toolkit"

def draw_title(self: bpy.types.Panel):
    layout = self.layout
    layout.label(text=t("AvatarToolkit.desc1"))
    layout.label(text=t("AvatarToolkit.desc2"))
    layout.label(text=t("AvatarToolkit.desc3"))

class AvatarToolKit_PT_AvatarToolkitPanel(bpy.types.Panel):
    bl_label = t("AvatarToolkit.label")
    bl_idname = "OBJECT_PT_avatar_toolkit"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY_NAME

    def draw(self: bpy.types.Panel, context: bpy.types.Context):
        draw_title(self)

