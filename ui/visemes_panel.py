from bpy.types import Panel, Context, UILayout
from ..core.translations import t
from .main_panel import AvatarToolKit_PT_AvatarToolkitPanel, CATEGORY_NAME

class AvatarToolKit_PT_VisemesPanel(Panel):
    """Panel containing viseme creation and preview tools"""
    bl_label: str = t("Visemes.panel_label")
    bl_idname: str = "VIEW3D_PT_avatar_toolkit_visemes"
    bl_space_type: str = 'VIEW_3D'
    bl_region_type: str = 'UI'
    bl_category: str = CATEGORY_NAME
    bl_parent_id: str = AvatarToolKit_PT_AvatarToolkitPanel.bl_idname
    bl_order: int = 4
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context: Context) -> None:
        """Draw the visemes panel interface"""
        layout: UILayout = self.layout
        props = context.scene.avatar_toolkit
        
        # Check for valid mesh with shape keys
        if not context.active_object or context.active_object.type != 'MESH' or not context.active_object.data.shape_keys:
            layout.label(text=t("Visemes.no_shapekeys"))
            return
            
        # Shape Key Selection Box
        shape_box: UILayout = layout.box()
        col: UILayout = shape_box.column(align=True)
        col.label(text=t("Visemes.shape_selection"), icon='SHAPEKEY_DATA')
        col.separator(factor=0.5)
        
        # Shape key selection with valid data
        shape_keys = context.active_object.data.shape_keys
        col.prop_search(props, "mouth_a", shape_keys, "key_blocks", text=t("Visemes.mouth_a"))
        col.prop_search(props, "mouth_o", shape_keys, "key_blocks", text=t("Visemes.mouth_o"))
        col.prop_search(props, "mouth_ch", shape_keys, "key_blocks", text=t("Visemes.mouth_ch"))
        
        # Shape intensity slider
        col.separator()
        col.prop(props, "shape_intensity", slider=True)
        
        # Preview Box
        preview_box: UILayout = layout.box()
        col = preview_box.column(align=True)
        col.label(text=t("Visemes.preview_label"), icon='HIDE_OFF')
        col.separator(factor=0.5)

        if props.viseme_preview_mode:
            col.prop(props, "viseme_preview_selection", text="")
            col.separator()

        preview_text = t("Visemes.stop_preview") if props.viseme_preview_mode else t("Visemes.start_preview")
        col.operator("avatar_toolkit.preview_visemes", text=preview_text, icon='HIDE_OFF')

        # Create Box
        create_box: UILayout = layout.box()
        col = create_box.column(align=True)
        col.label(text=t("Visemes.create_label"), icon='ADD')
        col.separator(factor=0.5)
        col.operator("avatar_toolkit.create_visemes", icon='ADD')
