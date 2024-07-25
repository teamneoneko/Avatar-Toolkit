import bpy
from ..core.register import register_wrap
from ..functions.translations import t
from ..core.common import get_selected_armature

@register_wrap
class AvatarToolkitVisemePanel(bpy.types.Panel):
    bl_label = t("VisemePanel.label")
    bl_idname = "OBJECT_PT_avatar_toolkit_viseme"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Avatar Toolkit"
    bl_parent_id = "OBJECT_PT_avatar_toolkit"

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        
        armature = get_selected_armature(context)
        if armature:
            layout.prop(context.scene, "selected_mesh", text="Select Mesh")
            
            mesh = bpy.data.objects.get(context.scene.selected_mesh)
            if mesh and mesh.type == 'MESH':
                if mesh.data.shape_keys:
                    layout.prop_search(context.scene, "mouth_a", mesh.data.shape_keys, "key_blocks", text=t('VisemePanel.mouth_a.label'))
                    layout.prop_search(context.scene, "mouth_o", mesh.data.shape_keys, "key_blocks", text=t('VisemePanel.mouth_o.label'))
                    layout.prop_search(context.scene, "mouth_ch", mesh.data.shape_keys, "key_blocks", text=t('VisemePanel.mouth_ch.label'))

                    layout.prop(context.scene, 'shape_intensity')

                    layout.operator("avatar_toolkit.create_visemes", icon='TRIA_RIGHT')
                else:
                    layout.label(text=t('VisemePanel.error.noShapekeys'), icon='ERROR')
            else:
                layout.label(text=t('VisemePanel.error.selectMesh'), icon='INFO')
        else:
            layout.label(text=t('VisemePanel.error.noArmature'), icon='ERROR')

        layout.separator()
        layout.label(text=t('VisemePanel.info.selectMesh'))


