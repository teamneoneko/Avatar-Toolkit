import bpy
from ..core import common
from ..core.register import register_wrap
from ..functions.translations import t

@register_wrap
class AutoVisemeButton(bpy.types.Operator):
    bl_idname = 'avatar_toolkit.create_visemes'
    bl_label = t('AutoVisemeButton.label')
    bl_description = t('AutoVisemeButton.desc')
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH'

    def execute(self, context):
        mesh = context.active_object
        if not mesh or not common.has_shapekeys(mesh):
            self.report({'ERROR'}, t('AutoVisemeButton.error.noShapekeys'))
            return {'CANCELLED'}

        shape_a = context.scene.mouth_a
        shape_o = context.scene.mouth_o
        shape_ch = context.scene.mouth_ch

        if shape_a == "Basis" or shape_o == "Basis" or shape_ch == "Basis":
            self.report({'ERROR'}, t('AutoVisemeButton.error.selectShapekeys'))
            return {'CANCELLED'}

        # Create visemes
        visemes = [
            ('vrc.v_aa', [(shape_a, 0.9998)]),
            ('vrc.v_ch', [(shape_ch, 0.9996)]),
            ('vrc.v_dd', [(shape_a, 0.3), (shape_ch, 0.7)]),
            ('vrc.v_e', [(shape_a, 0.5), (shape_ch, 0.2)]),
            ('vrc.v_ff', [(shape_a, 0.2), (shape_ch, 0.4)]),
            ('vrc.v_ih', [(shape_ch, 0.7), (shape_o, 0.3)]),
            ('vrc.v_kk', [(shape_a, 0.7), (shape_ch, 0.4)]),
            ('vrc.v_nn', [(shape_a, 0.2), (shape_ch, 0.7)]),
            ('vrc.v_oh', [(shape_a, 0.2), (shape_o, 0.8)]),
            ('vrc.v_ou', [(shape_o, 0.9994)]),
            ('vrc.v_pp', [(shape_a, 0.0004), (shape_o, 0.0004)]),
            ('vrc.v_rr', [(shape_ch, 0.5), (shape_o, 0.3)]),
            ('vrc.v_sil', [(shape_a, 0.0002), (shape_ch, 0.0002)]),
            ('vrc.v_ss', [(shape_ch, 0.8)]),
            ('vrc.v_th', [(shape_a, 0.4), (shape_o, 0.15)])
        ]

        for viseme_name, shape_mix in visemes:
            self.create_viseme(mesh, viseme_name, shape_mix, context.scene.shape_intensity)

        # Sort shape keys
        common.sort_shape_keys(mesh)

        self.report({'INFO'}, t('AutoVisemeButton.success'))
        return {'FINISHED'}

    def create_viseme(self, mesh, viseme_name, shape_mix, intensity):
        # Remove existing viseme if it exists
        if viseme_name in mesh.data.shape_keys.key_blocks:
            mesh.shape_key_remove(mesh.data.shape_keys.key_blocks[viseme_name])

        # Create new viseme
        new_key = mesh.shape_key_add(name=viseme_name, from_mix=False)
        new_key.value = 1.0

        # Mix shapes
        for shape_name, value in shape_mix:
            if shape_name in mesh.data.shape_keys.key_blocks:
                shape = mesh.data.shape_keys.key_blocks[shape_name]
                shape.value = value * intensity

        # Apply mix
        mesh.shape_key_add(name=viseme_name, from_mix=True)

        # Reset shape key values
        for shape in mesh.data.shape_keys.key_blocks:
            shape.value = 0.0

        new_key.value = 1.0