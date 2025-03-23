import bpy
from typing import Set, Dict, List, Optional, Tuple
from bpy.types import (
    Operator, 
    Panel, 
    Menu, 
    Context, 
    UILayout, 
    WindowManager,
    Object
)
from .main_panel import AvatarToolKit_PT_AvatarToolkitPanel, CATEGORY_NAME
from ..core.translations import t
from ..core.common import (
    get_active_armature, 
    clear_default_objects, 
    get_armature_list,
    get_armature_stats
)
from ..functions.pose_mode import (
    AvatarToolkit_OT_StartPoseMode,
    AvatarToolkit_OT_StopPoseMode,
    AvatarToolkit_OT_ApplyPoseAsShapekey,
    AvatarToolkit_OT_ApplyPoseAsRest
)
from ..core.armature_validation import validate_armature

class AvatarToolKit_OT_ExportFBX(Operator):
    """Export selected objects as FBX"""
    bl_idname: str = "avatar_toolkit.export_fbx"
    bl_label: str = t("QuickAccess.export_fbx")
    
    def execute(self, context: Context) -> Set[str]:
        bpy.ops.export_scene.fbx('INVOKE_DEFAULT')
        return {'FINISHED'}

class AvatarToolKit_MT_ExportMenu(Menu):
    """Export menu containing various export options"""
    bl_idname: str = "AVATAR_TOOLKIT_MT_export_menu"
    bl_label: str = t("QuickAccess.export")

    def draw(self, context: Context) -> None:
        layout: UILayout = self.layout
        layout.operator("avatar_toolkit.export_fbx", text=t("QuickAccess.export_fbx"))
        layout.operator("avatar_toolkit.export_resonite", text=t("QuickAccess.export_resonite"))

class AvatarToolKit_OT_ExportMenu(Operator):
    """Open the export menu"""
    bl_idname: str = "avatar_toolkit.export"
    bl_label: str = t("QuickAccess.export")

    @classmethod
    def poll(cls, context: Context) -> bool:
        return get_active_armature(context) is not None
    
    def execute(self, context: Context) -> Set[str]:
        bpy.context.window_manager.popup_menu(AvatarToolKit_MT_ExportMenu.draw)
        return {'FINISHED'}
    
class AvatarToolKit_PT_QuickAccessPanel(Panel):
    """Quick access panel for common Avatar Toolkit operations"""
    bl_label: str = t("QuickAccess.label")
    bl_idname: str = "OBJECT_PT_avatar_toolkit_quick_access"
    bl_space_type: str = 'VIEW_3D'
    bl_region_type: str = 'UI'
    bl_category: str = CATEGORY_NAME
    bl_parent_id: str = AvatarToolKit_PT_AvatarToolkitPanel.bl_idname
    bl_order: int = 0

    def draw(self, context: Context) -> None:
        """Draw the panel layout"""
        layout: UILayout = self.layout
        props = context.scene.avatar_toolkit
        
        # Armature Selection Box
        armature_box: UILayout = layout.box()
        col: UILayout = armature_box.column(align=True)
        col.label(text=t("QuickAccess.select_armature"), icon='ARMATURE_DATA')
        col.separator(factor=0.5)
        
        # Armature Selection
        col.prop(context.scene.avatar_toolkit, "active_armature", text="")
        
        # Armature Validation
        active_armature: Optional[Object] = get_active_armature(context)
        if active_armature:
            is_valid, messages, is_acceptable = validate_armature(active_armature)
            
            info_box = col.box()
            
            if not is_valid:
                # Display non-standard bones and hierarchy issues
                if len(messages) > 1:
                    # Found Bones section
                    validation_box = info_box.box()
                    row = validation_box.row()
                    row.prop(props, "show_found_bones", text=t("Validation.section.found_bones"), icon='TRIA_DOWN' if props.show_found_bones else 'TRIA_RIGHT', emboss=False)
                    if props.show_found_bones:
                        for line in messages[0].split('\n'):
                            validation_box.label(text=line)
                    
                    # Main validation status
                    validation_box = info_box.box()
                    row = validation_box.row()
                    row.alert = True
                    row.label(text=t("Validation.status.failed"))
                    
                    # Detailed validation message
                    validation_box = info_box.box()
                    row = validation_box.row()
                    row.alert = True
                    row.label(text=t("Validation.message.failed.line1"))
                    row = validation_box.row()
                    row.alert = True
                    row.label(text=t("Validation.message.failed.line2"))
                    row = validation_box.row()
                    row.alert = True
                    row.label(text=t("Validation.message.failed.line3"))
                    
                    # Non-Standard Bones section
                    validation_box = info_box.box()
                    row = validation_box.row()
                    row.alert = True
                    row.prop(props, "show_non_standard", text=t("Validation.section.non_standard"), icon='TRIA_DOWN' if props.show_non_standard else 'TRIA_RIGHT', emboss=False)
                    if props.show_non_standard:
                        for line in messages[1].split('\n'):
                            sub_row = validation_box.row()
                            sub_row.alert = True
                            sub_row.label(text=line)
                            
                    # Hierarchy Issues section
                    validation_box = info_box.box()
                    row = validation_box.row()
                    row.alert = True
                    row.prop(props, "show_hierarchy", text=t("Validation.section.hierarchy"), icon='TRIA_DOWN' if props.show_hierarchy else 'TRIA_RIGHT', emboss=False)
                    if props.show_hierarchy:
                        for message in messages[2:]:
                            sub_row = validation_box.row()
                            sub_row.alert = True
                            sub_row.label(text=message)
                else:
                    # If no specific issues, show acceptable message
                    info_box.label(text=messages[0], icon='INFO')
                    info_box.label(text=messages[1])
                    info_box.label(text=messages[2])
            elif is_valid and not is_acceptable:
                row = info_box.row()
                split = row.split(factor=0.6)
                split.label(text=t("QuickAccess.valid_armature"), icon='CHECKMARK')
                stats = get_armature_stats(active_armature)
                split.label(text=t("QuickAccess.bones_count", count=stats['bone_count']))
                
                if stats['has_pose']:
                    info_box.label(text=t("QuickAccess.pose_bones_available"), icon='POSE_HLT')
            elif is_valid and is_acceptable:
                # Show acceptable standard message
                info_box.label(text=messages[0], icon='INFO')
                info_box.label(text=messages[1])
                info_box.label(text=messages[2])
                
                # Add standardize button
                standardize_box = info_box.box()
                standardize_box.operator("avatar_toolkit.standardize_armature", 
                                    text=t("QuickAccess.standardize_armature"),
                                    icon='MODIFIER')

            # Validation Mode Warnings
            validation_mode = context.scene.avatar_toolkit.validation_mode
            if validation_mode == 'BASIC':
                warning_row = info_box.box()
                warning_row.alert = True
                warning_row.label(text=t("QuickAccess.validation_basic_warning"), icon='INFO')
                warning_row.label(text=t("QuickAccess.validation_basic_details"))
            elif validation_mode == 'NONE':
                warning_row = info_box.box()
                warning_row.alert = True
                warning_row.label(text=t("QuickAccess.validation_none_warning"), icon='ERROR')
                warning_row.label(text=t("QuickAccess.validation_none_details"))

            # Pose Mode Controls
            pose_box: UILayout = layout.box()
            col = pose_box.column(align=True)
            col.label(text=t("QuickAccess.pose_controls"), icon='ARMATURE_DATA')
            col.separator(factor=0.5)
            
            if context.mode == "POSE":
                col.operator(AvatarToolkit_OT_StopPoseMode.bl_idname, icon='POSE_HLT')
                col.separator(factor=0.5)
                col.operator(AvatarToolkit_OT_ApplyPoseAsRest.bl_idname, icon='MOD_ARMATURE')
                col.operator(AvatarToolkit_OT_ApplyPoseAsShapekey.bl_idname, icon='MOD_ARMATURE')
            else:
                col.operator(AvatarToolkit_OT_StartPoseMode.bl_idname, icon='POSE_HLT')

        # Import/Export Box
        import_box: UILayout = layout.box()
        col = import_box.column(align=True)
        col.label(text=t("QuickAccess.import_export"), icon='IMPORT')
        col.separator(factor=0.5)
        
        # Import/Export Buttons
        button_row: UILayout = col.row(align=True)
        button_row.scale_y = 1.5
        button_row.operator("avatar_toolkit.import", text=t("QuickAccess.import"), icon='IMPORT')
        button_row.operator("avatar_toolkit.export", text=t("QuickAccess.export"), icon='EXPORT')
