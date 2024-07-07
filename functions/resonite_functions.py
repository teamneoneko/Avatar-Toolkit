import bpy
from ..core.register import register_wrap
from typing import List, Optional
import re
from bpy.types import Operator, Context, Object
from ..core.dictionaries import bone_names
from ..core.common import get_armature, simplify_bonename

@register_wrap
class ConvertToResonite(Operator):
    bl_idname = 'avatar_toolkit.convert_to_resonite'
    bl_label = "Convert to Resonite" #t('Tools.convert_to_resonite.label')
    bl_description = "Converts bone names on a model to names compatable with Resonite" #t('Tools.convert_to_resonite.desc')
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        if not get_armature(context):
            return False
        return True
        
    def execute(self, context: Context) -> set:
        armature = get_armature(context)

        translate_bone_fails = 0
        untranslated_bones = set()

        reverse_bone_lookup = dict()
        for (preferred_name, name_list) in bone_names.items():
            for name in name_list:
                reverse_bone_lookup[name] = preferred_name

        resonite_translations = {
            'hips': "Hips",
            'spine': "Spine",
            'chest': "Chest",
            'neck': "Neck",
            'head': "Head",
            'left_eye': "Eye.L",
            'right_eye': "Eye.R",
            'right_leg': "UpperLeg.R",
            'right_knee': "Calf.R",
            'right_ankle': "Foot.R",
            'right_toe': 'Toes.R',
            'right_shoulder': "Shoulder.R",
            'right_arm': "UpperArm.R",
            'right_elbow': "ForeArm.R",
            'right_wrist': "Hand.R",
            'left_leg': "UpperLeg.L",
            'left_knee': "Calf.L",
            'left_ankle': "Foot.L",
            'left_toe': "Toes.L",
            'left_shoulder': "Shoulder.L",
            'left_arm': "UpperArm.L",
            'left_elbow': "ForeArm.L",
            'left_wrist': "Hand.R",

            'pinkie_1_l': "pinkie1.L",
            'pinkie_2_l': "pinkie2.L",
            'pinkie_3_l': "pinkie3.L",
            'ring_1_l': "ring1.L",
            'ring_2_l': "ring2.L",
            'ring_3_l': "ring3.L",
            'middle_1_l': "middle1.L",
            'middle_2_l': "middle2.L",
            'middle_3_l': "middle3.L",
            'index_1_l': "index1.L",
            'index_2_l': "index2.L",
            'index_3_l': "index3.L",
            'thumb_1_l': "thumb1.L",
            'thumb_2_l': "thumb2.L",
            'thumb_3_l': "thumb3.L",

            'pinkie_1_r': "pinkie1.R",
            'pinkie_2_r': "pinkie2.R",
            'pinkie_3_r': "pinkie3.R",
            'ring_1_r': "ring1.R",
            'ring_2_r': "ring2.R",
            'ring_3_r': "ring3.R",
            'middle_1_r': "middle1.R",
            'middle_2_r': "middle2.R",
            'middle_3_r': "middle3.R",
            'index_1_r': "index1.R",
            'index_2_r': "index2.R",
            'index_3_r': "index3.R",
            'thumb_1_r': "thumb1.R",
            'thumb_2_r': "thumb2.R",
            'thumb_3_r': "thumb3.R"
        }

                

        context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode='EDIT')

        bpy.ops.object.mode_set(mode='OBJECT')
        for bone in armature.data.bones:
            if simplify_bonename(bone.name) in reverse_bone_lookup and reverse_bone_lookup[simplify_bonename(bone.name)] in resonite_translations:
                bone.name = resonite_translations[reverse_bone_lookup[simplify_bonename(bone.name)]]
            else:
                untranslated_bones.add(bone.name)
                
                bone.name =  re.compile(re.escape("<noik>"), re.IGNORECASE).sub("",bone.name)+"<noik>"
                translate_bone_fails += 1
            
        bpy.ops.object.mode_set(mode='OBJECT')

        if translate_bone_fails > 0:
            self.report({'INFO'}, "Failed to translate {translate_bone_fails} bones to humanoid names. Adding \"<noik>\" to their names.".format(translate_bone_fails=translate_bone_fails))
        else:
            self.report({'INFO'}, "Successfully translated all bones to humanoid names")


        return {'FINISHED'}