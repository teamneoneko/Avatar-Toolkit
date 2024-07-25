import bpy
from ..core.register import register_wrap
from .panel import AvatarToolkitPanel
from bpy.types import Context
from ..functions.digitigrade_legs import CreateDigitigradeLegs
from ..functions.translations import t
from ..core.common import get_selected_armature

@register_wrap
class AvatarToolkitToolsPanel(bpy.types.Panel):
    bl_label = t("Tools.label")
    bl_idname = "OBJECT_PT_avatar_toolkit_tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Avatar Toolkit"
    bl_parent_id = "OBJECT_PT_avatar_toolkit"
    bl_order = 3

    def draw(self, context: Context):
        layout = self.layout
        armature = get_selected_armature(context)
        
        if armature:
            layout.label(text=t("Tools.tools_title.label"))
            layout.separator(factor=0.5)

            row = layout.row(align=True)
            row.scale_y = 1.5  
            row.operator("avatar_toolkit.convert_to_resonite", text=t("Tools.convert_to_resonite.label"))
            row = layout.row(align=True)
            row.operator(CreateDigitigradeLegs.bl_idname, text=t("Tools.create_digitigrade_legs.label"))
        else:
            layout.label(text=t("Tools.select_armature"))
