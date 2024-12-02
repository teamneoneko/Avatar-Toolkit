import bpy
from .main_panel import AvatarToolKit_PT_AvatarToolkitPanel, CATEGORY_NAME
from bpy.types import Panel, Context
from ..core.common import get_selected_armature
from ..core.translations import t
from ..functions.armature_modifying import AvatarToolkit_OT_MergeArmatures

class AvatarToolkit_PT_MergeArmaturesPanel(Panel):
    bl_label = t("MergeArmatures.label")
    bl_idname = "OBJECT_PT_avatar_toolkit_merge_armatures"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY_NAME
    bl_parent_id = AvatarToolKit_PT_AvatarToolkitPanel.bl_idname
    bl_order = 5

    def draw(self, context: Context):
        layout = self.layout
        armature = get_selected_armature(context)
        
        if armature:
            layout.label(text=t("MergeArmatures.title.label"), icon='ARMATURE_DATA')
            
            layout.separator(factor=0.5)
            
            box = layout.box()
            col = box.column(align=True)
            
            col.prop(context.scene.avatar_toolkit, "selected_armature", text=t("MergeArmatures.target_armature.label"), icon="ARMATURE_DATA")
            col.prop(context.scene.avatar_toolkit, "merge_armature_source", icon="OUTLINER_OB_ARMATURE")
            
            layout.separator(factor=0.5)
            
            col = layout.column(align=True)
            col.prop(context.scene.avatar_toolkit, "merge_armature_align_bones", icon="BONE_DATA")
            col.prop(context.scene.avatar_toolkit, "merge_armature_apply_transforms", icon="OBJECT_ORIGIN")
            
            layout.separator(factor=1.0)
            
            row = layout.row()
            row.scale_y = 1.5
            row.operator(operator=AvatarToolkit_OT_MergeArmatures.bl_idname, icon="ARMATURE_DATA")
            
        else:
            layout.label(text=t("MergeArmatures.select_armature"), icon='ERROR')
