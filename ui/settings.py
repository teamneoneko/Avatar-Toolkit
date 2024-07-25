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
    bl_order = 6

    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene, "avatar_toolkit_language", text=t("Settings.language.label"))

@register_wrap
class AVATAR_TOOLKIT_OT_translation_restart_popup(bpy.types.Operator):
    bl_idname = "avatar_toolkit.translation_restart_popup"
    bl_label = t("Settings.translation_restart_popup.label")
    bl_description = t("Settings.translation_restart_popup.description")
    bl_options = {'INTERNAL'}

    def execute(self, context):
        if context.scene.avatar_toolkit_language_changed:
            # Reload the addon after the popup is closed
            bpy.ops.script.reload()
            context.scene.avatar_toolkit_language_changed = False
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):
        layout = self.layout
        layout.label(text=t("Settings.translation_restart_popup.message1"))
        layout.label(text=t("Settings.translation_restart_popup.message2"))
