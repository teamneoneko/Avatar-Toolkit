import bpy
from ..core import common
from ..core.register import register_wrap
from ..functions.translations import t
from typing import List, Tuple
from ..core.common import get_selected_armature, is_valid_armature, get_all_meshes, init_progress, update_progress, finish_progress

@register_wrap
class AvatarToolKit_OT_AutoVisemeButton(bpy.types.Operator):
    bl_idname = 'avatar_toolkit.create_visemes'
    bl_label = t('AutoVisemeButton.label')
    bl_description = t('AutoVisemeButton.desc')
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        armature = get_selected_armature(context)
        return armature is not None and is_valid_armature(armature) and get_all_meshes(context)

    def execute(self, context: bpy.types.Context) -> set:
        try:
            self.create_visemes(context)
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

    def create_visemes(self, context: bpy.types.Context) -> None:
        init_progress(context, 5)  # 5 main steps

        update_progress(self, context, t("VisemePanel.start_viseme_creation"))
        mesh = bpy.data.objects.get(context.scene.selected_mesh)
        if not mesh or not common.has_shapekeys(mesh):
            raise ValueError(t('AutoVisemeButton.error.noShapekeys'))

        update_progress(self, context, t("VisemePanel.removing_existing_visemes"))
        self.remove_existing_vrc_shapekeys(mesh)

        shape_a = context.scene.avatar_toolkit_mouth_a
        shape_o = context.scene.avatar_toolkit_mouth_o
        shape_ch = context.scene.avatar_toolkit_mouth_ch

        if shape_a == "Basis" or shape_o == "Basis" or shape_ch == "Basis":
            raise ValueError(t('AutoVisemeButton.error.selectShapekeys'))

        update_progress(self, context, t("VisemePanel.creating_visemes"))
        visemes: List[Tuple[str, List[Tuple[str, float]]]] = [
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
            self.create_viseme(mesh, viseme_name, shape_mix, context.scene.avatar_toolkit_shape_intensity)

        update_progress(self, context, t("VisemePanel.sorting_shapekeys"))
        common.sort_shape_keys(mesh)

        update_progress(self, context, t("VisemePanel.viseme_creation_completed"))
        finish_progress(context)

    def create_viseme(self, mesh: bpy.types.Object, viseme_name: str, shape_mix: List[Tuple[str, float]], intensity: float) -> None:
        shape_keys = mesh.data.shape_keys.key_blocks

        if viseme_name in shape_keys:
            mesh.shape_key_remove(shape_keys[viseme_name])

        new_key = mesh.shape_key_add(name=viseme_name, from_mix=False)
        new_key.value = 0.0

        for shape_name, value in shape_mix:
            if shape_name in shape_keys:
                source_shape = shape_keys[shape_name]
                for i, vert in enumerate(new_key.data):
                    vert.co += (source_shape.data[i].co - shape_keys['Basis'].data[i].co) * value * intensity

    def remove_existing_vrc_shapekeys(self, mesh: bpy.types.Object) -> None:
        vrc_prefixes = ['vrc.v_', 'vrc.blink_', 'vrc.lowerlid_']
        shape_keys = mesh.data.shape_keys.key_blocks
        for key in reversed(shape_keys):
            if any(key.name.startswith(prefix) for prefix in vrc_prefixes):
                mesh.shape_key_remove(key)
