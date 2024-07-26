import bpy
from ..core.register import register_wrap
from ..functions.translations import t

@register_wrap
class AvatarToolkitPanel(bpy.types.Panel):
    bl_label = t("AvatarToolkit.label")
    bl_idname = "OBJECT_PT_avatar_toolkit"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Avatar Toolkit"

    def draw(self, context):
        layout = self.layout
        layout.label(text=t("AvatarToolkit.welcome"))
        layout.label(text=t("AvatarToolkit.description"))
        layout.label(text=t("AvatarToolkit.alpha_warning"))

        
