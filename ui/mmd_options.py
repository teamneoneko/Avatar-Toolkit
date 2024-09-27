import bpy
from ..core.register import register_wrap
from .panel import AvatarToolKit_PT_AvatarToolkitPanel, CATEGORY_NAME
from ..functions.translations import t
from ..functions.mmd_functions import *
from ..functions.mesh_tools import AvatarToolKit_OT_JoinAllMeshes
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
    bl_order = 4

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        
        layout.label(text=t("MMDOptions.title"), icon='OUTLINER_OB_ARMATURE')
        
        layout.separator(factor=0.5)
        
        col = layout.column(align=True)
        col.scale_y = 1.2
        col.operator(AvatarToolKit_OT_CleanupMesh.bl_idname, icon='BRUSH_DATA')
        col.operator(AvatarToolKit_OT_JoinAllMeshes.bl_idname, icon='OBJECT_DATAMODE')
        
        layout.separator(factor=0.5)
        
        col = layout.column(align=True)
        col.scale_y = 1.2
        col.operator(AvatarToolKit_OT_OptimizeWeights.bl_idname, icon='MOD_VERTEX_WEIGHT')
        col.operator(AvatarToolKit_OT_OptimizeArmature.bl_idname, icon='ARMATURE_DATA')
        
        layout.separator(factor=0.5)
        
        row = layout.row(align=True)
        row.scale_y = 1.2
        row.operator(AvatarToolKit_OT_ApplyTransforms.bl_idname, icon='OBJECT_ORIGIN')
        row.operator(AvatarToolKit_OT_CombineMaterials.bl_idname, icon='MATERIAL')
        
        layout.separator(factor=0.5)
        
        row = layout.row()
        row.scale_y = 1.2
        row.operator(AvatarToolKit_OT_ConvertMaterials.bl_idname, icon='SHADING_TEXTURE')

