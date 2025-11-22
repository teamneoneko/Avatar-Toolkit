"""
MMD Converter Panel - UI for MMD conversion tools
"""
import bpy
from bpy.types import Panel, Context, UILayout
from .main_panel import AvatarToolKit_PT_AvatarToolkitPanel, CATEGORY_NAME
from .panel_layout import get_panel_order, should_open_by_default
from ..core.translations import t
from ..core.common import get_active_armature
from ..core.mmd_converter import detect_mmd_armature
from ..functions.tools.mmd_conversion import AvatarToolkit_OT_ConvertMMDArmature


class AvatarToolKit_PT_MMDPanel(Panel):
    """Panel for MMD conversion tools"""
    bl_label = t("MMD.panel.label")
    bl_idname = "OBJECT_PT_avatar_toolkit_mmd"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY_NAME
    bl_parent_id = AvatarToolKit_PT_AvatarToolkitPanel.bl_idname
    bl_order = get_panel_order('mmd')
    bl_options = set() if not should_open_by_default('MMD') else {'DEFAULT_CLOSED'}

    def draw(self, context: Context) -> None:
        """Draw the MMD conversion panel interface"""
        layout: UILayout = self.layout
        
        # MMD Conversion Tools
        mmd_box: UILayout = layout.box()
        col: UILayout = mmd_box.column(align=True)
        col.label(text=t("MMD.converter.title"), icon='ARMATURE_DATA')
        col.separator(factor=0.5)
        
        # Check if we have an active armature
        armature = get_active_armature(context)
        
        if not armature:
            col.label(text=t("MMD.no_armature_selected"), icon='ERROR')
            col.label(text=t("MMD.select_armature_to_convert"))
            return
        
        # Check if the armature appears to be MMD
        is_mmd = detect_mmd_armature(armature)
        
        if is_mmd:
            col.label(text=t("MMD.armature_name", name=armature.name), icon='CHECKMARK')
            col.label(text=t("MMD.armature_detected"), icon='INFO')
            col.separator(factor=0.3)
            
            toolkit = context.scene.avatar_toolkit
            
            # Basic conversion settings
            col.prop(toolkit, 'mmd_make_parent', text=t("MMD.make_armature_parent"))
            col.prop(toolkit, 'mmd_rename_armature', text=t("MMD.rename_to_armature"))
            col.separator(factor=0.2)
            
            # Translation settings
            col.prop(toolkit, 'mmd_translate_names', text=t("MMD.translate_names"))
            
            # Translation sub-options (only show if translation is enabled)
            if toolkit.mmd_translate_names:
                trans_box = col.box()
                trans_col = trans_box.column(align=True)
                trans_col.label(text=t("MMD.translation_options"), icon='WORLD')
                trans_col.prop(toolkit, 'mmd_translate_bones', text=t("MMD.translate_bones"))
                trans_col.prop(toolkit, 'mmd_translate_materials', text=t("MMD.translate_materials"))
                trans_col.prop(toolkit, 'mmd_translate_shapekeys', text=t("MMD.translate_shapekeys"))
                trans_col.prop(toolkit, 'mmd_translate_objects', text=t("MMD.translate_objects"))
            
            col.separator(factor=0.2)
            
            col.operator(
                AvatarToolkit_OT_ConvertMMDArmature.bl_idname,
                text=t("MMD.convert_armature_button"),
                icon='EXPORT'
            )
            
            info_box = mmd_box.box()
            info_col = info_box.column(align=True)
            info_col.label(text=t("MMD.conversion_info.title"), icon='INFO')
            info_col.label(text=t("MMD.conversion_info.removes_parent"))
            info_col.label(text=t("MMD.conversion_info.renames_armature"))
            info_col.label(text=t("MMD.conversion_info.maintains_hierarchy"))
            if toolkit.mmd_translate_names:
                info_col.label(text=t("MMD.conversion_info.translates_names"))
            
        else:
            col.label(text=t("MMD.armature_name", name=armature.name), icon='ERROR')
            col.label(text=t("MMD.no_mmd_bones_detected"), icon='CANCEL')
            col.separator(factor=0.3)
            
            row = col.row()
            row.enabled = False
            row.operator(
                AvatarToolkit_OT_ConvertMMDArmature.bl_idname,
                text=t("MMD.convert_armature_button"),
                icon='CANCEL'
            )
            
            help_box = mmd_box.box()
            help_col = help_box.column(align=True)
            help_col.label(text=t("MMD.detection_failed.title"), icon='QUESTION')
            help_col.label(text=t("MMD.detection_failed.not_mmd_format"))
            help_col.label(text=t("MMD.detection_failed.need_mmd_bones"))
            help_col.label(text=t("MMD.detection_failed.check_bone_names"))
