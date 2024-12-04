import bpy
from typing import Set, Dict, List, Optional
from bpy.types import (
    Operator, 
    Panel, 
    Context, 
    UILayout, 
    WindowManager,
    Event
)
from .main_panel import AvatarToolKit_PT_AvatarToolkitPanel, CATEGORY_NAME
from ..core.translations import t, get_languages_list

class AvatarToolkit_OT_TranslationRestartPopup(Operator):
    """Popup dialog shown after language change to inform about restart requirement"""
    bl_idname: str = "avatar_toolkit.translation_restart_popup"
    bl_label: str = t("Language.changed.title")
    
    def execute(self, context: Context) -> Set[str]:
        return {'FINISHED'}
    
    def invoke(self, context: Context, event: Event) -> Set[str]:
        wm: WindowManager = context.window_manager
        return wm.invoke_props_dialog(self)
    
    def draw(self, context: Context) -> None:
        layout: UILayout = self.layout
        layout.label(text=t("Language.changed.success"))
        layout.label(text=t("Language.changed.restart"))

class AvatarToolKit_PT_SettingsPanel(Panel):
    """Settings panel for Avatar Toolkit containing language preferences"""
    bl_label: str = t("Settings.label")
    bl_idname: str = "OBJECT_PT_avatar_toolkit_settings"
    bl_space_type: str = 'VIEW_3D'
    bl_region_type: str = 'UI'
    bl_category: str = CATEGORY_NAME
    bl_parent_id: str = AvatarToolKit_PT_AvatarToolkitPanel.bl_idname
    bl_order: int = 2

    def draw(self, context: Context) -> None:
        """Draw the settings panel layout with language selection"""
        layout: UILayout = self.layout
        
        # Language Settings
        lang_box: UILayout = layout.box()
        col: UILayout = lang_box.column(align=True)
        row: UILayout = col.row()
        row.scale_y = 1.2
        row.label(text=t("Settings.language"), icon='WORLD')
        col.separator()
        col.prop(context.scene.avatar_toolkit, "language", text="")
        
        # Validation Settings
        val_box: UILayout = layout.box()
        col = val_box.column(align=True)
        row = col.row()
        row.scale_y = 1.2
        row.label(text=t("Settings.validation_mode"), icon='CHECKMARK')
        col.separator()
        col.prop(context.scene.avatar_toolkit, "validation_mode", text="")

        # Debug Settings
        debug_box = layout.box()
        col = debug_box.column()
        row = col.row(align=True)
        row.prop(context.scene.avatar_toolkit, "debug_expand", 
                icon="TRIA_DOWN" if context.scene.avatar_toolkit.debug_expand 
                else "TRIA_RIGHT", 
                icon_only=True, emboss=False)
        row.label(text=t("Settings.debug"), icon='CONSOLE')
        
        if context.scene.avatar_toolkit.debug_expand:
            col = debug_box.column(align=True)
            col.prop(context.scene.avatar_toolkit, "enable_logging")
