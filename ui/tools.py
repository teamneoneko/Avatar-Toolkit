import bpy
from ..core.register import register_wrap
from .panel import AvatarToolkitPanel
from bpy.types import Context
from ..functions.digitigrade_legs import CreateDigitigradeLegs
from ..functions.translations import t
from ..core.common import get_selected_armature
from ..functions.seperate_by import SeparateByMaterials, SeparateByLooseParts
from ..functions.additional_tools import ApplyTransforms
from ..functions.mesh_tools import AvatarToolkit_OT_RemoveUnusedShapekeys

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
            layout.label(text=t("Tools.tools_title.label"), icon='TOOL_SETTINGS')
            layout.separator(factor=0.5)

            row = layout.row(align=True)
            row.scale_y = 1.5  
            row.operator("avatar_toolkit.convert_to_resonite", text=t("Tools.convert_to_resonite.label"), icon='SCENE_DATA')
            row = layout.row(align=True)
            row.operator(CreateDigitigradeLegs.bl_idname, text=t("Tools.create_digitigrade_legs.label"), icon='BONE_DATA')
            layout.separator()
            row = layout.row(align=True)
            layout.label(text=t("Tools.separate_by.label"), icon='MESH_DATA')
            row.operator(SeparateByMaterials.bl_idname, text=t("Tools.separate_by_materials.label"), icon='MATERIAL')
            row.operator(SeparateByLooseParts.bl_idname, text=t("Tools.separate_by_loose_parts.label"), icon='OUTLINER_OB_MESH')
            row = layout.row(align=True)
            row.operator(ApplyTransforms.bl_idname, text=t("Tools.apply_transforms.label"), icon='OBJECT_ORIGIN')
            row.operator(AvatarToolkit_OT_RemoveUnusedShapekeys.bl_idname, text=t("Tools.remove_unused_shapekeys.label"), icon='SHAPEKEY_DATA')
        else:
            layout.label(text=t("Tools.select_armature"), icon='ERROR')
