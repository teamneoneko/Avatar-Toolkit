import bpy
from ..core.register import register_wrap
from .panel import AvatarToolkitPanel

from ..core.import_pmx import import_pmx
from ..core.import_pmd import import_pmd
from ..core.importer import import_fbx

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
    
        row = layout.row()
        row.label(text="Import/Export", icon='IMPORT')
        
        layout.separator(factor=0.5)

        row = layout.row(align=True)
        row.scale_y = 1.5  
        row.operator("avatar_toolkit.import_menu", text="Import")
        row.operator("avatar_toolkit.export_menu", text="Export")

@register_wrap
class AVATAR_TOOLKIT_OT_import_menu(bpy.types.Operator):
    bl_idname = "avatar_toolkit.import_menu"
    bl_label = "Import Menu"

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_popup(self, width=200)

    def draw(self, context):
        layout = self.layout
        layout.label(text="Select Import Method")
        layout.operator("avatar_toolkit.import_pmx", text="Import PMX")
        layout.operator("avatar_toolkit.import_pmd", text="Import PMD")
        layout.operator("avatar_toolkit.import_fbx", text="Import FBX") 


@register_wrap
class AVATAR_TOOLKIT_OT_export_menu(bpy.types.Operator):
    bl_idname = "avatar_toolkit.export_menu"
    bl_label = "Export Menu"

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_popup(self, width=200)

    def draw(self, context):
        layout = self.layout
        layout.label(text="Export options will go here")

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

@register_wrap
class AVATAR_TOOLKIT_OT_import_fbx(bpy.types.Operator):
    bl_idname = "avatar_toolkit.import_fbx"
    bl_label = "Import FBX"

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        import_fbx(self.filepath)
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
