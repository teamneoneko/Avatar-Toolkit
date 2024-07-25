import bpy
from ..core.register import register_wrap
from .panel import AvatarToolkitPanel
from bpy.types import Context
from ..functions.translations import t

from ..core.import_pmx import import_pmx
from ..core.import_pmd import import_pmd
from ..functions.import_anything import ImportAnyModel
from ..core.common import get_selected_armature, set_selected_armature

@register_wrap
class AvatarToolkitQuickAccessPanel(bpy.types.Panel):
    bl_label = t("Quick_Access.label")
    bl_idname = "OBJECT_PT_avatar_toolkit_quick_access"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Avatar Toolkit"
    bl_parent_id = "OBJECT_PT_avatar_toolkit"
    bl_order = 1

    def draw(self, context: Context):
        layout = self.layout
        layout.label(text=t("Quick_Access.options"))

        layout.prop(context.scene, "selected_armature", text="Select Armature")

        row = layout.row()
        row.label(text=t("Quick_Access.import_export.label"), icon='IMPORT')
        
        layout.separator(factor=0.5)

        row = layout.row(align=True)
        row.scale_y = 1.5  
        row.operator(ImportAnyModel.bl_idname, text=t("Quick_Access.import"))
        row.operator("avatar_toolkit.export_menu", text=t("Quick_Access.export"))

@register_wrap
class AVATAR_TOOLKIT_OT_export_menu(bpy.types.Operator):
    bl_idname = "avatar_toolkit.export_menu"
    bl_label = t("Quick_Access.export_menu.label")
    bl_description = t("Quick_Access.import_pmx.desc")

    @classmethod
    def poll(cls, context):
        return any(obj.type == 'MESH' for obj in context.scene.objects)

    def execute(self, context: Context):
        return {'FINISHED'}

    def invoke(self, context: Context, event):
        wm = context.window_manager
        return wm.invoke_popup(self, width=200)

    def draw(self, context: Context):
        layout = self.layout
        layout.label(text=t("Quick_Access.select_export.label"))
        layout.operator("avatar_toolkit.export_resonite", text=t("Quick_Access.select_export_resonite.label"))
        layout.operator("avatar_toolkit.export_fbx", text=t("Quick_Access.export_fbx.label"))

@register_wrap
class AVATAR_TOOLKIT_OT_export_fbx(bpy.types.Operator):
    bl_idname = 'avatar_toolkit.export_fbx'
    bl_label = t("Quick_Access.export_fbx.label")
    bl_description = t("Quick_Access.export_fbx.desc")
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        bpy.ops.export_scene.fbx('INVOKE_DEFAULT')
        return {'FINISHED'}

