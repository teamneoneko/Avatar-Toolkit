import bpy
from ..core.register import register_wrap
from ..functions.translations import t

@register_wrap
class AvatarToolkitVisemePanel(bpy.types.Panel):
    bl_label = t("Viseme.label")
    bl_idname = "OBJECT_PT_avatar_toolkit_viseme"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Avatar Toolkit"
    bl_parent_id = "OBJECT_PT_avatar_toolkit"

    def draw(self, context):
        layout = self.layout
        mesh = context.active_object

        if not mesh or mesh.type != 'MESH':
            layout.label(text=t('VisemePanel.error.noMesh'), icon='ERROR')
            return

        if not mesh.data.shape_keys:
            layout.label(text=t('VisemePanel.error.noShapekeys'), icon='ERROR')
            return

        layout.prop_search(context.scene, "mouth_a", mesh.data.shape_keys, "key_blocks", text=t('Scene.mouth_a.label'))
        layout.prop_search(context.scene, "mouth_o", mesh.data.shape_keys, "key_blocks", text=t('Scene.mouth_o.label'))
        layout.prop_search(context.scene, "mouth_ch", mesh.data.shape_keys, "key_blocks", text=t('Scene.mouth_ch.label'))

        layout.prop(context.scene, 'shape_intensity')

        layout.operator("avatar_toolkit.create_visemes", icon='TRIA_RIGHT')
