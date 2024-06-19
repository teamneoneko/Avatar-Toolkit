import bpy
from ..core.register import register_wrap
from .panel import AvatarToolkitPanel

from ..core.import_pmx import import_pmx
from ..core.import_pmd import import_pmd
from ..core.translation import t

@register_wrap
class AvatarToolkitQuickAccessPanel(bpy.types.Panel):
    bl_label = t("avatar_toolkit.quick_access.title")
    bl_idname = "OBJECT_PT_avatar_toolkit_quick_access"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Avatar Toolkit"
    bl_parent_id = "OBJECT_PT_avatar_toolkit"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Quick Access Options")
        
        # Add import buttons
        row = layout.row()
        row.operator("avatar_toolkit.import_pmx", text=t("avatar_toolkit.import_pmx.label"))
        row.operator("avatar_toolkit.import_pmd", text=t("avatar_toolkit.import_pmd.label"))

@register_wrap
class AVATAR_TOOLKIT_OT_import_pmx(bpy.types.Operator):
    bl_idname = "avatar_toolkit.import_pmx"
    bl_label = t("avatar_toolkit.import_pmx.label")

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        import_pmx(self.filepath)
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

@register_wrap
class AVATAR_TOOLKIT_OT_import_pmd(bpy.types.Operator):
    bl_idname = "avatar_toolkit.import_pmd"
    bl_label = t("avatar_toolkit.import_pmd.label")

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        import_pmd(self.filepath)
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
