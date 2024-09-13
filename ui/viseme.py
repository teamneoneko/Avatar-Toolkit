import bpy
from ..core.register import register_wrap
from .panel import AvatarToolKit_PT_AvatarToolkitPanel, CATEGORY_NAME
from ..functions.viseme import AvatarToolKit_OT_AutoVisemeButton
from ..functions.translations import t
from ..core.common import get_selected_armature

@register_wrap
class AvatarToolkitVisemePanel(bpy.types.Panel):
    bl_label = t("VisemePanel.label")
    bl_idname = "OBJECT_PT_avatar_toolkit_viseme"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY_NAME
    bl_parent_id = AvatarToolKit_PT_AvatarToolkitPanel.bl_idname
    bl_order = 6

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        
        armature = get_selected_armature(context)
        if armature:
            layout.prop(context.scene, "selected_mesh", text=t("VisemePanel.select_mesh"), icon='OUTLINER_OB_MESH')
            
            row = layout.row()
            mesh = bpy.data.objects.get(context.scene.selected_mesh)
            if mesh and mesh.type == 'MESH':
                if mesh.data.shape_keys:
                    layout.prop_search(context.scene, "avatar_toolkit_mouth_a", mesh.data.shape_keys, "key_blocks", text=t('VisemePanel.mouth_a.label'), icon='SHAPEKEY_DATA')
                    layout.prop_search(context.scene, "avatar_toolkit_mouth_o", mesh.data.shape_keys, "key_blocks", text=t('VisemePanel.mouth_o.label'), icon='SHAPEKEY_DATA')
                    layout.prop_search(context.scene, "avatar_toolkit_mouth_ch", mesh.data.shape_keys, "key_blocks", text=t('VisemePanel.mouth_ch.label'), icon='SHAPEKEY_DATA')

                    layout.prop(context.scene, 'avatar_toolkit_shape_intensity', text=t('VisemePanel.shape_intensity'), icon='FORCE_LENNARDJONES')

                    row = layout.row()
                    row.scale_y = 1.2
                    row.operator(AvatarToolKit_OT_AutoVisemeButton.bl_idname, text=t('VisemePanel.create_visemes'), icon='TRIA_RIGHT')
                else:
                    layout.label(text=t('VisemePanel.error.noShapekeys'), icon='ERROR')
            else:
                layout.label(text=t('VisemePanel.error.selectMesh'), icon='INFO')
        else:
            layout.label(text=t('VisemePanel.error.noArmature'), icon='ERROR')

        layout.separator()
        layout.label(text=t('VisemePanel.info.selectMesh'), icon='HELP')
