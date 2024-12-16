from types import FrameType
import bpy
import bpy_extras
from numpy import double

from .common import get_armature, get_selected_armature, simplify_bonename, is_valid_armature
from bpy.types import Object, ShapeKey, Mesh, Context, Operator
from functools import lru_cache
from ..core.register import register_wrap
from ..functions.translations import t
from ..core.dictionaries import bone_names

import re
from .resonite_loader import resonite_animx, resonite_types
import os



@register_wrap
class AvatarToolKit_OT_ExportResonite(Operator):
    bl_idname = 'avatar_toolkit.export_resonite'
    bl_label = t("Importer.export_resonite.label")
    bl_description = t("Importer.export_resonite.desc")
    bl_options = {'REGISTER', 'UNDO'}
    filepath: bpy.props.StringProperty()


    @classmethod
    def poll(cls, context: Context):
        if get_armature(context) is None:
            return False
        return True

    def execute(self, context: Context):
        #settings stolen from cats.
        bpy.ops.export_scene.gltf('INVOKE_AREA',
            export_image_format = 'WEBP',
            export_image_quality = 75,
            export_materials = 'EXPORT',
            export_animations = True,
            export_animation_mode = 'ACTIONS',
            export_nla_strips_merged_animation_name = 'Animation',
            export_nla_strips = True)
        return {'FINISHED'}

@register_wrap
class AvatarToolKit_OT_ConvertToResonite(Operator):
    bl_idname = 'avatar_toolkit.convert_to_resonite'
    bl_label = t('Tools.convert_to_resonite.label')
    bl_description = t('Tools.convert_to_resonite.desc')
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        armature = get_selected_armature(context)
        return armature is not None and is_valid_armature(armature)
        
    def execute(self, context: Context) -> set:
        armature = get_selected_armature(context)
        if not armature:
            self.report({'WARNING'}, t("Tools.no_armature_selected"))
            return {'CANCELLED'}

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
        bone.name = re.compile(re.escape("<noik>"), re.IGNORECASE).sub("",bone.name) #remove "NOIK" from bones before translating again, in case an update was done that fixes a translation.
        for bone in armature.data.bones:
            if simplify_bonename(bone.name) in reverse_bone_lookup and reverse_bone_lookup[simplify_bonename(bone.name)] in resonite_translations:
                bone.name = resonite_translations[reverse_bone_lookup[simplify_bonename(bone.name)]]
            else:
                untranslated_bones.add(bone.name)
                
                bone.name = bone.name+"<noik>"
                translate_bone_fails += 1
            
        bpy.ops.object.mode_set(mode='OBJECT')

        if translate_bone_fails > 0:
            self.report({'INFO'}, t("Tools.bones_translated_with_fails").format(translate_bone_fails=translate_bone_fails))
        else:
            self.report({'INFO'}, t("Tools.bones_translated_success"))

        return {'FINISHED'}


def makeorexistingfcurve(action: bpy.types.Action,data_path: str,action_group: str, index=0) -> bpy.types.FCurve:
    fcurve = action.fcurves.find(data_path=data_path,index=index)
    if fcurve == None:
        return action.fcurves.new(data_path,action_group=action_group,index=index)
    else:
        print("fcurve with data \""+data_path+"\" already exists")
        return fcurve

@register_wrap
class AvatarToolKit_OT_AnimX_Importer(Operator,bpy_extras.io_utils.ImportHelper):
    bl_idname = 'avatar_toolkit.animx_importer'
    bl_label = t('Tools.animx_importer.label')
    bl_description = t('Tools.animx_importer.desc')
    bl_options = {'REGISTER', 'UNDO'}

    #fps = bpy.props.FloatProperty(default=25) #25 fps
    
    filter_glob: bpy.props.StringProperty(
        default="*.animx",
        options={'HIDDEN'}
    )
    files: bpy.props.CollectionProperty(type=bpy.types.OperatorFileListElement, options={'HIDDEN', 'SKIP_SAVE'})
    filepath: bpy.props.StringProperty()

    directory:bpy.props.StringProperty(subtype='DIR_PATH')

    @classmethod
    def poll(cls, context: Context) -> bool:
        return context.active_object != None
        
    def execute(self, context: Context) -> set:
        
        Froox_animations: list[resonite_animx.AnimX] = []

        #decoding using self contained library:
        files = [file.name for file in self.files]
        #files.append(self.filepath)
        for file in files:
            froox_animation: resonite_animx.AnimX = resonite_animx.AnimX()
            froox_animation.interval.x = 30 #should be default fps
            froox_animation.read(file = os.path.join(self.directory,file))
            Froox_animations.append(froox_animation)

        #TODO: Allow multiple targets and setting animations to each one somehow with an interface.
        target: bpy.types.Object = context.active_object
        if target.animation_data == None:
            target.animation_data_create()

        #Load data into Blender Animations.
        for froox_animation in Froox_animations:
            action: bpy.types.Action = bpy.data.actions.new(froox_animation.name.x)
            target.animation_data.action = action
            action.use_fake_user = True
            for track in froox_animation.tracks:
                data_path: str
                actualproperty: str = track.property.x

                match(actualproperty):
                    case("Position"):
                        actualproperty = "location"
                    case("Rotation"):
                        actualproperty = "rotation_quaternion"
                    case("Scale"):
                        actualproperty = "scale"
                data_path = actualproperty

                if target.type == "ARMATURE":
                    data_path = "pose.bones[\""+track.node.x+"\"]."+data_path

                    for posebone in target.pose.bones:
                        posebone.rotation_mode = "QUATERNION"

                print("reading frames for "+data_path)
                if(track.FrameType == "resonite_types.double" or track.FrameType == "resonite_types.double"):
                    self.readTrackData(track,makeorexistingfcurve(action=action,data_path=data_path,action_group=track.node.x,index=0),".x")
                elif (track.FrameType == "resonite_types.float3" or track.FrameType == "resonite_types.double3"):
                    self.readTrackData(track,makeorexistingfcurve(action=action,data_path=data_path,action_group=track.node.x,index=0),".x")
                    self.readTrackData(track,makeorexistingfcurve(action=action,data_path=data_path,action_group=track.node.x,index=2),".y")
                    self.readTrackData(track,makeorexistingfcurve(action=action,data_path=data_path,action_group=track.node.x,index=1),".z")
                elif (track.FrameType == "resonite_types.float4" or track.FrameType == "resonite_types.double4"):
                    self.readTrackData(track,makeorexistingfcurve(action=action,data_path=data_path,action_group=track.node.x,index=0),".x")
                    self.readTrackData(track,makeorexistingfcurve(action=action,data_path=data_path,action_group=track.node.x,index=1),".y")
                    self.readTrackData(track,makeorexistingfcurve(action=action,data_path=data_path,action_group=track.node.x,index=2),".z")
                    self.readTrackData(track,makeorexistingfcurve(action=action,data_path=data_path,action_group=track.node.x,index=3),".w")
                elif (track.FrameType == "resonite_types.doubleQ" or track.FrameType == "resonite_types.floatQ"):
                    self.readTrackData(track,makeorexistingfcurve(action=action,data_path=data_path,action_group=track.node.x,index=3),".w")
                    self.readTrackData(track,makeorexistingfcurve(action=action,data_path=data_path,action_group=track.node.x,index=0),".x")
                    self.readTrackData(track,makeorexistingfcurve(action=action,data_path=data_path,action_group=track.node.x,index=2),".y")
                    self.readTrackData(track,makeorexistingfcurve(action=action,data_path=data_path,action_group=track.node.x,index=1),".z")
                else:
                    continue
        return {'FINISHED'}

    def readTrackData(self,track: resonite_animx.ResoTrack, fcurve_reso: bpy.types.FCurve, valuetype: str = ""):
        tracktype = type(track)
        match(tracktype):
            case (resonite_animx.RawTrack):
                rawtrack: resonite_animx.RawTrack = track

                
                
                fcurve_reso.keyframe_points.add(count=len(rawtrack.keyframes))
                # populate points
                fcurve_reso.keyframe_points.foreach_set("co", [x for co in zip([frame.time.x*track.Owner.interval.x for frame in rawtrack.keyframes], [eval("frame.value"+valuetype) for frame in rawtrack.keyframes]) for x in co])
                fcurve_reso.update()

            case (resonite_animx.DiscreteTrack):
                discretetrack: resonite_animx.DiscreteTrack = track

                fcurve_reso.keyframe_points.add(count=len(discretetrack.keyframes))
                # populate points
                fcurve_reso.keyframe_points.foreach_set("co", [x for co in zip([frame.time.x*track.Owner.interval.x for frame in discretetrack.keyframes], [eval("frame.value"+valuetype) for frame in discretetrack.keyframes]) for x in co])
                fcurve_reso.update()

            case(resonite_animx.CurveTrack):
                curvetrack: resonite_animx.CurveTrack = track

                fcurve_reso.keyframe_points.add(count=len(curvetrack.keyframes))
                # populate points
                fcurve_reso.keyframe_points.foreach_set("co", [x for co in zip([frame.time.x*track.Owner.interval.x for frame in curvetrack.keyframes], [eval("frame.value"+valuetype) for frame in curvetrack.keyframes]) for x in co])
                interp: bool = curvetrack.tangents
                #print("has tangents? "+str(interp))

                for idx,frame in enumerate(curvetrack.keyframes):
                    
                    if interp:
                        fcurve_reso.keyframe_points[idx].handle_left = float(eval("frame.left_tan"+valuetype))
                        fcurve_reso.keyframe_points[idx].handle_right = float(eval("frame.right_tan"+valuetype))
                    fcurve_reso.keyframe_points[idx].interpolation = "BEZIER"
                    fcurve_reso.keyframe_points[idx].easing = "EASE_IN"
                fcurve_reso.update()

            case(resonite_animx.BezierTrack):
                beziertrack: resonite_animx.BezierTrack = track
                # Bezier is not supported rn, ignore.
            case _:
                print("invalid track type, ignoring")
                print(track)



        
    

    



    

