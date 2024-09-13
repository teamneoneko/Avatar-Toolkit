
import bpy
from ..core.register import register_wrap
from .panel import AvatarToolKit_PT_AvatarToolkitPanel, CATEGORY_NAME
from bpy.types import Panel, Context
from ..core.common import get_selected_armature
from ..functions.translations import t
from ..functions.armature_modifying import AvatarToolkit_OT_MergeArmatures

@register_wrap
class AvatarToolkit_PT_MergeArmaturesPanel(Panel):
    bl_label = t("MergeArmatures.label")
    bl_idname = "OBJECT_PT_avatar_toolkit_merge_armatures"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY_NAME
    bl_parent_id = AvatarToolKit_PT_AvatarToolkitPanel.bl_idname
    bl_order = 4

    def draw(self, context: Context):
        layout = self.layout
        armature = get_selected_armature(context)
        
        if armature:
            layout.label(text=t("MergeArmatures.title.label"), icon='ARMATURE_DATA')
            
            layout.separator(factor=0.5)
            row = layout.row(align=True)
            row.prop(context.scene, property="selected_armature",text=t("MergeArmatures.target_armature.label"),icon="STYLUS_PRESSURE")
            row = layout.row(align=True)
            row.prop(context.scene, property="merge_armature_source",icon="SORT_DESC")
            row = layout.row(align=True)
            row.prop(context.scene, property="merge_armature_align_bones")
            row = layout.row(align=True)
            row.prop(context.scene, property="merge_armature_apply_transforms")
            row = layout.row(align=True)
            row.operator(operator=AvatarToolkit_OT_MergeArmatures.bl_idname,icon="ARMATURE_DATA")
            
        else:
            layout.label(text=t("MergeArmatures.select_armature"), icon='ERROR')