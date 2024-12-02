import bpy
from .main_panel import AvatarToolKit_PT_AvatarToolkitPanel, CATEGORY_NAME
from ..core.translations import t

class AvatarToolkitSettingsPanel(bpy.types.Panel):
    bl_label = t("Settings.label")
    bl_idname = "OBJECT_PT_avatar_toolkit_settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY_NAME
    bl_parent_id = AvatarToolKit_PT_AvatarToolkitPanel.bl_idname
    bl_order = 8

    def draw(self, context):
        layout = self.layout
        
        layout.label(text=t("Settings.language.label"))
        layout.prop(context.scene.avatar_toolkit, "language", text="", icon='WORLD')

class AVATAR_TOOLKIT_OT_translation_restart_popup(bpy.types.Operator):
    bl_idname = "avatar_toolkit.translation_restart_popup"
    bl_label = t("Settings.translation_restart_popup.label")
    bl_description = t("Settings.translation_restart_popup.description")
    bl_options = {'INTERNAL'}

    def execute(self, context):
        if context.scene.avatar_toolkit.language_changed:
            bpy.ops.script.reload()
            context.scene.avatar_toolkit.language_changed = False
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):
        layout = self.layout
        layout.label(text=t("Settings.translation_restart_popup.message1"), icon='INFO')
        layout.label(text=t("Settings.translation_restart_popup.message2"), icon='FILE_REFRESH')
