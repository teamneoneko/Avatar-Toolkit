import bpy
from ..core.register import register_wrap
from .panel import AvatarToolkitPanel
from bpy.types import Context
from ..functions.translations import t

from ..core.import_pmx import import_pmx
from ..core.import_pmd import import_pmd

@register_wrap
class AvatarToolkitQuickAccessPanel(bpy.types.Panel):
    bl_label = t("Quick_Access.label")
    bl_idname = "OBJECT_PT_avatar_toolkit_quick_access"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Avatar Toolkit"
    bl_parent_id = "OBJECT_PT_avatar_toolkit"

    def draw(self, context: Context):
        layout = self.layout
        layout.label(text=t("Quick_Access.options"))

        row = layout.row()
        row.label(text=t("Quick_Access.import_export.label"), icon='IMPORT')
        
        layout.separator(factor=0.5)

        row = layout.row(align=True)
        row.scale_y = 1.5  
        row.operator("avatar_toolkit.import_menu", text=t("Quick_Access.import"))
        row.operator("avatar_toolkit.export_menu", text=t("Quick_Access.export"))

@register_wrap
class AVATAR_TOOLKIT_OT_import_menu(bpy.types.Operator):
    bl_idname = "avatar_toolkit.import_menu"
    bl_label = t("Quick_Access.import_menu.label")

    def execute(self, context: Context):
        return {'FINISHED'}

    def invoke(self, context: Context, event):
        wm = context.window_manager
        return wm.invoke_popup(self, width=200)

    def draw(self, context: Context):
        layout = self.layout
        layout.label(text="Select Import Method")
        layout.operator("avatar_toolkit.import_pmx", text=t("Quick_Access.import_pmx"))
        layout.operator("avatar_toolkit.import_pmd", text=t("Quick_Access.import_pmd"))

@register_wrap
class AVATAR_TOOLKIT_OT_export_menu(bpy.types.Operator):
    bl_idname = "avatar_toolkit.export_menu"
    bl_label = t("Quick_Access.export_menu.label")

    def execute(self, context: Context):
        return {'FINISHED'}

    def invoke(self, context: Context, event):
        wm = context.window_manager
        return wm.invoke_popup(self, width=200)

    def draw(self, context: Context):
        layout = self.layout
        layout.label(text=t("Quick_Access.select_export.label"))
        layout.operator("avatar_toolkit.export_resonite", text=t("Quick_Access.select_export_resonite.label"))

@register_wrap
class AVATAR_TOOLKIT_OT_import_pmx(bpy.types.Operator):
    bl_idname = "avatar_toolkit.import_pmx"
    bl_label = t("Quick_Access.import_pmx")

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context: Context):
        import_pmx(self.filepath)
        return {'FINISHED'}

    def invoke(self, context: Context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

@register_wrap
class AVATAR_TOOLKIT_OT_import_pmd(bpy.types.Operator):
    bl_idname = "avatar_toolkit.import_pmd"
    bl_label = t("Quick_Access.import_pmd")

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context: Context):
        import_pmd(self.filepath)
        return {'FINISHED'}

    def invoke(self, context: Context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
