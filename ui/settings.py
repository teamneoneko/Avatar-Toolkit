import bpy
from ..core.register import register_wrap
from .panel import AvatarToolkitPanel
from ..functions.translations import t

@register_wrap
class AvatarToolkitSettingsPanel(bpy.types.Panel):
    bl_label = t("Settings.label")
    bl_idname = "OBJECT_PT_avatar_toolkit_settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Avatar Toolkit"
    bl_parent_id = "OBJECT_PT_avatar_toolkit"

    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene, "avatar_toolkit_language", text=t("Settings.language.label"))
