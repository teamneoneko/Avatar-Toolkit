import bpy
from .main_panel import AvatarToolKit_PT_AvatarToolkitPanel, CATEGORY_NAME
from ..core.translations import t
from ..core.common import open_web_after_delay_multi_threaded

class AvatarToolkit_PT_CreditsSupport(bpy.types.Panel):
    bl_label = t("CreditsSupport.label")
    bl_idname = "OBJECT_PT_avatar_toolkit_credits_support"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY_NAME
    bl_parent_id = AvatarToolKit_PT_AvatarToolkitPanel.bl_idname
    bl_order = 10

    def draw(self, context):
        layout = self.layout

        layout.label(text=t("CreditsSupport.credits_title"))
        box = layout.box()
        column = box.column(align=True)
        column.scale_y = 0.7
        column.label(text=t("CreditsSupport.credits_text1"))
        column.label(text=t("CreditsSupport.credits_text2"))
        column.label(text=t("CreditsSupport.credits_text3"))
        column.label(text=t("CreditsSupport.credits_text4"))

        layout.separator()

        layout.label(text=t("CreditsSupport.support_title"))
        box = layout.box()
        column = box.column(align=True)
        column.scale_y = 0.7
        column.label(text=t("CreditsSupport.support_text1"))
        column.label(text=t("CreditsSupport.support_text2"))
        row = column.row()
        row.scale_y = 1.5
        row.operator("wm.url_open", text=t("CreditsSupport.support_button")).url = "https://neoneko.xyz/supportus.html"

        layout.separator()

        layout.label(text=t("CreditsSupport.help_title"))
        box = layout.box()
        column = box.column(align=True)
        column.scale_y = 0.7
        column.label(text=t("CreditsSupport.help_text1"))
        column.label(text=t("CreditsSupport.help_text2"))
        row = column.row()
        row.scale_y = 1.5
        row.operator("wm.url_open", text=t("CreditsSupport.wiki_button")).url = "https://github.com/teamneoneko/Avatar-Toolkit"
        row = column.row()
        row.scale_y = 1.5
        row.operator("wm.url_open", text=t("CreditsSupport.discord_button")).url = "https://discord.catsblenderplugin.xyz"

