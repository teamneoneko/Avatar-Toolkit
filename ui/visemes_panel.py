import bpy
from bpy.types import Panel, Context, UILayout, Object, ShapeKey
from ..core.translations import t
from .main_panel import AvatarToolKit_PT_AvatarToolkitPanel, CATEGORY_NAME
from ..core.common import get_active_armature

class AvatarToolKit_PT_VisemesPanel(Panel):
    """Panel containing viseme creation and preview tools"""
    bl_label: str = t("Visemes.panel_label")
    bl_idname: str = "VIEW3D_PT_avatar_toolkit_visemes"
    bl_space_type: str = 'VIEW_3D'
    bl_region_type: str = 'UI'
    bl_category: str = CATEGORY_NAME
    bl_parent_id: str = AvatarToolKit_PT_AvatarToolkitPanel.bl_idname
    bl_order: int = 5
    bl_options: set[str] = {'DEFAULT_CLOSED'}

    def draw(self, context: Context) -> None:
        """Draw the visemes panel interface with shape key selection and preview controls"""
        layout: UILayout = self.layout
        props = context.scene.avatar_toolkit

        # Mesh Selection Box
        mesh_box: UILayout = layout.box()
        col: UILayout = mesh_box.column(align=True)
        col.label(text=t("Visemes.mesh_select"), icon='OUTLINER_OB_MESH')
        col.separator(factor=0.5)

        armature = get_active_armature(context)
        if armature:
            col.prop_search(props, "viseme_mesh", bpy.data, "objects", text="")
        else:
            col.label(text=t("Visemes.no_armature"), icon='ERROR')

        # Get selected mesh
        mesh_obj = bpy.data.objects.get(props.viseme_mesh)
        if not mesh_obj or not mesh_obj.data.shape_keys:
            layout.label(text=t("Visemes.no_shapekeys"))
            return

        # Shape Key Selection Box    
        shape_box: UILayout = layout.box()
        col: UILayout = shape_box.column(align=True)
        col.label(text=t("Visemes.shape_selection"), icon='SHAPEKEY_DATA')
        col.separator(factor=0.5)
        
        # Shape key selection with valid data
        shape_keys: ShapeKey = mesh_obj.data.shape_keys
        col.prop_search(props, "mouth_a", shape_keys, "key_blocks", text=t("Visemes.mouth_a"))
        col.prop_search(props, "mouth_o", shape_keys, "key_blocks", text=t("Visemes.mouth_o"))
        col.prop_search(props, "mouth_ch", shape_keys, "key_blocks", text=t("Visemes.mouth_ch"))
        
        # Shape intensity slider
        col.separator()
        col.prop(props, "shape_intensity", slider=True)
        
        # Preview Box
        preview_box: UILayout = layout.box()
        col: UILayout = preview_box.column(align=True)
        col.label(text=t("Visemes.preview_label"), icon='HIDE_OFF')
        col.separator(factor=0.5)

        if props.viseme_preview_mode:
            col.prop(props, "viseme_preview_selection", text="")
            col.separator()

        preview_text: str = t("Visemes.stop_preview") if props.viseme_preview_mode else t("Visemes.start_preview")
        col.operator("avatar_toolkit.preview_visemes", text=preview_text, icon='HIDE_OFF')

        # Create Box
        create_box: UILayout = layout.box()
        col: UILayout = create_box.column(align=True)
        col.label(text=t("Visemes.create_label"), icon='ADD')
        col.separator(factor=0.5)
        col.operator("avatar_toolkit.create_visemes", icon='ADD')
