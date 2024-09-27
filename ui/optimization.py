import bpy
from ..core.register import register_wrap
from .panel import AvatarToolKit_PT_AvatarToolkitPanel, CATEGORY_NAME
from ..functions.translations import t
from ..functions.remove_doubles_safely import AvatarToolKit_OT_RemoveDoublesSafely, AvatarToolKit_OT_RemoveDoublesSafelyAdvanced
from ..core.common import get_selected_armature
from ..functions.mesh_tools import AvatarToolKit_OT_JoinAllMeshes, AvatarToolKit_OT_JoinSelectedMeshes
from ..functions.combine_materials import AvatarToolKit_OT_CombineMaterials

@register_wrap
class AvatarToolkit_PT_OptimizationPanel(bpy.types.Panel):
    bl_label = t("Optimization.label")
    bl_idname = "OBJECT_PT_avatar_toolkit_optimization"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY_NAME
    bl_parent_id = AvatarToolKit_PT_AvatarToolkitPanel.bl_idname
    bl_order = 2

    def draw(self: bpy.types.Panel, context: bpy.types.Context):
        layout = self.layout
        armature = get_selected_armature(context)
        
        if armature:
            layout.label(text=t("Optimization.options.label"), icon='SETTINGS')
            
            layout.separator(factor=0.5)
            
            row = layout.row(align=True)
            row.scale_y = 1.2 
            row.operator(AvatarToolKit_OT_CombineMaterials.bl_idname, text=t("Optimization.combine_materials.label"), icon='MATERIAL')
            
            layout.separator(factor=0.5)
            
            row = layout.row(align=True)
            row.scale_y = 1.2 
            row.operator(AvatarToolKit_OT_RemoveDoublesSafely.bl_idname, text=t("Optimization.remove_doubles_safely.label"), icon='SNAP_VERTEX')
            row.operator(AvatarToolKit_OT_RemoveDoublesSafelyAdvanced.bl_idname, text=t("Optimization.remove_doubles_safely_advanced.label"), icon="ACTION")
            
            layout.separator(factor=1.0)
            
            layout.label(text=t("Optimization.joinmeshes.label"), icon='OBJECT_DATA')
            row = layout.row(align=True)
            row.scale_y = 1.2 
            row.operator(AvatarToolKit_OT_JoinAllMeshes.bl_idname, text=t("Optimization.join_all_meshes.label"), icon='OUTLINER_OB_MESH')
            row.operator(AvatarToolKit_OT_JoinSelectedMeshes.bl_idname, text=t("Optimization.join_selected_meshes.label"), icon='STICKY_UVS_LOC')
            
        else:
            layout.label(text=t("Optimization.select_armature"), icon='ERROR')


