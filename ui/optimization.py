import bpy
from ..core.register import register_wrap
from .panel import AvatarToolkitPanel
from ..core.translation import t

@register_wrap
class AvatarToolkitOptimizationPanel(bpy.types.Panel):
    bl_label = t("avatar_toolkit.optimization.title")
    bl_idname = "OBJECT_PT_avatar_toolkit_optimization"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Avatar Toolkit"
    bl_parent_id = "OBJECT_PT_avatar_toolkit"

    def draw(self, context):
        layout = self.layout
        layout.label(text=t("avatar_toolkit.optimization.label"))
        
        row = layout.row()
        row.operator("avatar_toolkit.combine_materials", text=t("avatar_toolkit.combine_materials.label"))

        row = layout.row()
        row.operator("avatar_toolkit.join_all_meshes", text=t("avatar_toolkit.join_all_meshes.label"))

        row = layout.row()
        row.operator("avatar_toolkit.join_selected_meshes", text=t("avatar_toolkit.join_selected_meshes.label"))

        # Add optimization options here
