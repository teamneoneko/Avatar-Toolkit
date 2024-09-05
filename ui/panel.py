import bpy
from ..core.register import register_wrap
from ..functions.translations import t

CATEGORY_NAME = "Avatar Toolkit"

@register_wrap
class AvatarToolKit_PT_AvatarToolkitPanel(bpy.types.Panel):
    bl_label = t("AvatarToolkit.label")
    bl_idname = "OBJECT_PT_avatar_toolkit"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY_NAME

    def draw(self, context):
        layout = self.layout
        layout.label(text=t("AvatarToolkit.welcome"))
        layout.label(text=t("AvatarToolkit.description"))
        layout.label(text=t("AvatarToolkit.alpha_warning"))

        
