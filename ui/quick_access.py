import bpy
from ..core.register import register_wrap
from ..core.pmx.import_pmx import import_pmx
from ..core.pmd.import_pmd import import_pmd

@register_wrap
class AvatarToolkitQuickAccessPanel(bpy.types.Panel):
    bl_label = "Quick Access"
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
        row.operator("avatar_toolkit.import_pmx", text="Import PMX")
        row.operator("avatar_toolkit.import_pmd", text="Import PMD")

@register_wrap
class AVATAR_TOOLKIT_OT_import_pmx(bpy.types.Operator):
    bl_idname = "avatar_toolkit.import_pmx"
    bl_label = "Import PMX"

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
    bl_label = "Import PMD"

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        import_pmd(self.filepath)
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
