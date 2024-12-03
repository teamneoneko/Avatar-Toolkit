import bpy
from typing import Set, Optional, List, Tuple
from bpy.types import Operator, Panel, Menu, Context, UILayout
from .main_panel import AvatarToolKit_PT_AvatarToolkitPanel, CATEGORY_NAME
from ..core.translations import t
from ..core.common import (
    get_active_armature, 
    clear_default_objects, 
    validate_armature,
    get_armature_list,
    get_armature_stats
)
from ..core.importers.importer import import_types, imports
from ..functions.pose_mode import (
    AvatarToolkit_OT_StartPoseMode,
    AvatarToolkit_OT_StopPoseMode,
    AvatarToolkit_OT_ApplyPoseAsShapekey,
    AvatarToolkit_OT_ApplyPoseAsRest
)

class AvatarToolKit_OT_Import(Operator):
    """Import FBX files into Blender with Avatar Toolkit settings"""
    bl_idname = "avatar_toolkit.import"
    bl_label = t("QuickAccess.import")
    
    def execute(self, context: Context) -> Set[str]:
        clear_default_objects()
        bpy.ops.import_scene.fbx('INVOKE_DEFAULT', filter_glob=imports)
        return {'FINISHED'}

class AvatarToolKit_OT_ExportFBX(Operator):
    """Export selected objects as FBX"""
    bl_idname = "avatar_toolkit.export_fbx"
    bl_label = t("QuickAccess.export_fbx")
    
    def execute(self, context: Context) -> Set[str]:
        bpy.ops.export_scene.fbx('INVOKE_DEFAULT')
        return {'FINISHED'}

class AvatarToolKit_MT_ExportMenu(Menu):
    """Export menu containing various export options"""
    bl_idname = "AVATAR_TOOLKIT_MT_export_menu"
    bl_label = t("QuickAccess.export")

    def draw(self, context: Context) -> None:
        layout: UILayout = self.layout
        layout.operator("avatar_toolkit.export_fbx", text=t("QuickAccess.export_fbx"))
        layout.operator("avatar_toolkit.export_resonite", text=t("QuickAccess.export_resonite"))

class AvatarToolKit_OT_ExportMenu(Operator):
    """Open the export menu"""
    bl_idname = "avatar_toolkit.export"
    bl_label = t("QuickAccess.export")
    
    def execute(self, context: Context) -> Set[str]:
        bpy.ops.wm.call_menu(name=AvatarToolKit_MT_ExportMenu.bl_idname)
        return {'FINISHED'}

class AvatarToolKit_PT_QuickAccessPanel(Panel):
    """Quick access panel for common Avatar Toolkit operations"""
    bl_label = t("QuickAccess.label")
    bl_idname = "OBJECT_PT_avatar_toolkit_quick_access"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY_NAME
    bl_parent_id = AvatarToolKit_PT_AvatarToolkitPanel.bl_idname
    bl_order = 0

    @classmethod
    def poll(cls, context: Context) -> bool:
        """Only show panel in Object or Pose mode"""
        return context.mode in {'OBJECT', 'POSE'}

    def draw(self, context: Context) -> None:
        """Draw the panel layout"""
        layout: UILayout = self.layout
        
        # Armature Selection Box
        armature_box: UILayout = layout.box()
        col: UILayout = armature_box.column(align=True)
        col.label(text=t("QuickAccess.select_armature"), icon='ARMATURE_DATA')
        col.separator(factor=0.5)
        
        # Armature Selection
        col.prop(context.scene.avatar_toolkit, "active_armature", text="")
        
        # Armature Validation
        active_armature = get_active_armature(context)
        if active_armature:
            is_valid: bool
            message: str
            is_valid, message = validate_armature(active_armature)
            
            if is_valid:
                info_box: UILayout = col.box()
                row: UILayout = info_box.row()
                split: UILayout = row.split(factor=0.6)
                split.label(text=t("QuickAccess.valid_armature"), icon='CHECKMARK')
                stats: dict = get_armature_stats(active_armature)
                split.label(text=t("QuickAccess.bones_count", count=stats['bone_count']))
                
                if stats['has_pose']:
                    info_box.label(text=t("QuickAccess.pose_bones_available"), icon='POSE_HLT')
            else:
                col.separator(factor=0.5)
                col.label(text=message, icon='ERROR')

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
