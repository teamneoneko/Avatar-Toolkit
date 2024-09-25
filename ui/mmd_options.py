import bpy
from ..core.register import register_wrap
from .panel import AvatarToolKit_PT_AvatarToolkitPanel, CATEGORY_NAME
from ..functions.translations import t
from ..functions.mmd_functions import *
from ..functions.join_meshes import AvatarToolKit_OT_JoinAllMeshes
from ..functions.combine_materials import AvatarToolKit_OT_CombineMaterials
from ..functions.additional_tools import AvatarToolKit_OT_ApplyTransforms

@register_wrap
class AvatarToolkit_PT_MMDOptionsPanel(bpy.types.Panel):
    bl_label = t("MMDOptions.label")
    bl_idname = "OBJECT_PT_avatar_toolkit_mmd_options"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY_NAME
    bl_parent_id = AvatarToolKit_PT_AvatarToolkitPanel.bl_idname
    bl_order = 7

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        
        layout.operator(AvatarToolKit_OT_CleanupMesh.bl_idname)
        layout.operator(AvatarToolKit_OT_JoinAllMeshes.bl_idname)
        layout.operator(AvatarToolKit_OT_OptimizeWeights.bl_idname)
        layout.operator(AvatarToolKit_OT_OptimizeArmature.bl_idname)
        layout.operator(AvatarToolKit_OT_ApplyTransforms.bl_idname)
        layout.operator(AvatarToolKit_OT_CombineMaterials.bl_idname)
        layout.operator(AvatarToolKit_OT_ConvertMaterials.bl_idname)
