import bpy
from typing import Set
from bpy.types import Panel, Context, UILayout, Operator
from .main_panel import AvatarToolKit_PT_AvatarToolkitPanel, CATEGORY_NAME
from ..core.translations import t

class AvatarToolKit_PT_MMDPanel(Panel):
    """Panel containing MMD-specific tools and operations"""
    bl_label = t("MMDTools.label")
    bl_idname = "OBJECT_PT_avatar_toolkit_mmd"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY_NAME
    bl_parent_id = AvatarToolKit_PT_AvatarToolkitPanel.bl_idname
    bl_order = 3

    def draw(self, context: Context) -> None:
        """Draw the MMD tools panel interface"""
        layout = self.layout
        
        # Basic MMD Tools Box
        basic_box = layout.box()
        col = basic_box.column(align=True)
        col.label(text=t("MMDTools.basic_tools"), icon='ARMATURE_DATA')
        col.separator(factor=0.5)
        col.operator("avatar_toolkit.fix_bone_names", icon='SORTALPHA')
        col.operator("avatar_toolkit.fix_bone_hierarchy", icon='BONE_DATA')
        col.operator("avatar_toolkit.fix_bone_weights", icon='GROUP_BONE')
        
        # Advanced MMD Tools Box
        advanced_box = layout.box()
        col = advanced_box.column(align=True)
        col.label(text=t("MMDTools.advanced_tools"), icon='MODIFIER')
        col.separator(factor=0.5)
        col.operator("avatar_toolkit.fix_mmd_features", icon='SHAPEKEY_DATA')
        col.operator("avatar_toolkit.advanced_bone_ops", icon='CONSTRAINT_BONE')
        
        # Settings Box
        settings_box = layout.box()
        col = settings_box.column(align=True)
        col.label(text=t("MMDTools.settings"), icon='PREFERENCES')
        col.separator(factor=0.5)
        col.prop(context.scene.avatar_toolkit, "mmd_keep_upper_chest")
        col.prop(context.scene.avatar_toolkit, "mmd_remove_unused_bones")
        col.prop(context.scene.avatar_toolkit, "mmd_cleanup_shapekeys")
        
        # Cleanup Box
        cleanup_box = layout.box()
        col = cleanup_box.column(align=True)
        col.label(text=t("MMDTools.cleanup"), icon='TRASH')
        col.separator(factor=0.5)
        col.operator("avatar_toolkit.cleanup_operations", icon='BRUSH_DATA')
