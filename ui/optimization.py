import bpy
from ..core.register import register_wrap
from .panel import AvatarToolkitPanel
from ..functions.translations import t
from ..core.common import get_selected_armature

@register_wrap
class AvatarToolkitOptimizationPanel(bpy.types.Panel):
    bl_label = t("Optimization.label")
    bl_idname = "OBJECT_PT_avatar_toolkit_optimization"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Avatar Toolkit"
    bl_parent_id = "OBJECT_PT_avatar_toolkit"

    def draw(self, context):
        layout = self.layout
        armature = get_selected_armature(context)
        
        if armature:
            layout.label(text=t("Optimization.options.label"))
            
            row = layout.row()
            row.scale_y = 1.2 
            row.operator("avatar_toolkit.combine_materials", text=t("Optimization.combine_materials.label"))
            
            layout.separator(factor=0.5)
            
            row = layout.row(align=True)
            row.scale_y = 1.2 
            row.operator("avatar_toolkit.join_all_meshes", text=t("Optimization.join_all_meshes.label"))
            row.operator("avatar_toolkit.join_selected_meshes", text=t("Optimization.join_selected_meshes.label"))
            row.operator("avatar_toolkit.remove_doubles_safely", text="Remove Doubles Safely")
        else:
            layout.label(text="Please select an armature in Quick Access")
