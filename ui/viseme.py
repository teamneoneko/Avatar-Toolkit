import bpy
from ..core.register import register_wrap
from ..functions.translations import t

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
        
        # Check if there's an active object and it's a mesh
        if context.active_object and context.active_object.type == 'MESH':
            mesh = context.active_object
            
            # Check if the mesh has shape keys
            if mesh.data.shape_keys:
                layout.prop_search(context.scene, "mouth_a", mesh.data.shape_keys, "key_blocks", text=t('VisemePanel.mouth_a.label'))
                layout.prop_search(context.scene, "mouth_o", mesh.data.shape_keys, "key_blocks", text=t('VisemePanel.mouth_o.label'))
                layout.prop_search(context.scene, "mouth_ch", mesh.data.shape_keys, "key_blocks", text=t('VisemePanel.mouth_ch.label'))

                layout.prop(context.scene, 'shape_intensity')

                layout.operator("avatar_toolkit.create_visemes", icon='TRIA_RIGHT')
            else:
                layout.label(text=t('VisemePanel.error.noShapekeys'), icon='ERROR')
        else:
            layout.label(text=t('VisemePanel.error.noMesh'), icon='ERROR')

        # Always show some information or options
        layout.separator()
        layout.label(text=t('VisemePanel.info.selectMesh'))
