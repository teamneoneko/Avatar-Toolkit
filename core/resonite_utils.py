from types import FrameType
import bpy
import bpy_extras
from numpy import double
from typing import Set, Dict

from .common import get_active_armature, simplify_bonename, validate_armature, ProgressTracker
from bpy.types import Context, Operator
from ..core.translations import t
from ..core.dictionaries import bone_names, resonite_translations
from ..core.logging_setup import logger

import re
from .resonite_loader import resonite_animx, resonite_types
import os

class AvatarToolKit_OT_ExportResonite(Operator):
    bl_idname = 'avatar_toolkit.export_resonite'
    bl_label = t("Importer.export_resonite.label")
    bl_description = t("Importer.export_resonite.desc")
    bl_options = {'REGISTER', 'UNDO'}
    filepath: bpy.props.StringProperty()

    @classmethod
    def poll(cls, context: Context):
        if get_active_armature(context) is None:
            return False
        return True

    def execute(self, context: Context):
        bpy.ops.export_scene.gltf('INVOKE_AREA',
            export_image_format = 'WEBP',
            export_image_quality = 75,
            export_materials = 'EXPORT',
            export_animations = True,
            export_animation_mode = 'ACTIONS',
            export_nla_strips_merged_animation_name = 'Animation',
            export_nla_strips = True)
        return {'FINISHED'}

class AvatarToolkit_OT_ConvertResonite(Operator):
    """Convert armature bone names to Resonite format with progress tracking and validation"""
    bl_idname = "avatar_toolkit.convert_resonite"
    bl_label = t("Tools.convert_resonite")
    bl_description = t("Tools.convert_resonite_desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        armature = get_active_armature(context)
        if not armature:
            return False
        is_valid, _ = validate_armature(armature)
        return is_valid

    def execute(self, context: Context) -> Set[str]:
        armature = get_active_armature(context)
        if not armature:
            logger.warning("No armature selected for Resonite conversion")
            self.report({'WARNING'}, t("Armature.validation.no_armature"))
            return {'CANCELLED'}

        translate_bone_fails: int = 0
        untranslated_bones: Set[str] = set()
        simplified_names: Dict[str, str] = {}

        # Create reverse lookup dictionary
        reverse_bone_lookup = {}
        for preferred_name, name_list in bone_names.items():
            for name in name_list:
                reverse_bone_lookup[name] = preferred_name

        try:
            context.view_layer.objects.active = armature
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.object.mode_set(mode='OBJECT')

            # Cache simplified bone names
            for bone in armature.data.bones:
                simplified_names[bone.name] = simplify_bonename(bone.name)

            total_bones = len(armature.data.bones)
            with ProgressTracker(context, total_bones, t("Tools.convert_resonite.operation")) as progress:
                for bone in armature.data.bones:
                    # Remove any existing "<noik>" tags
                    bone.name = re.compile(re.escape("<noik>"), re.IGNORECASE).sub("", bone.name)
                    simplified_name = simplified_names[bone.name]

                    if simplified_name in reverse_bone_lookup and reverse_bone_lookup[simplified_name] in resonite_translations:
                        new_name = resonite_translations[reverse_bone_lookup[simplified_name]]
                        logger.debug(f"Translating bone: {bone.name} -> {new_name}")
                        bone.name = new_name
                    else:
                        untranslated_bones.add(bone.name)
                        bone.name = bone.name + "<noik>"
                        translate_bone_fails += 1
                        logger.debug(f"Failed to translate bone: {bone.name}")

                    progress.step(t("Tools.convert_resonite.processing", name=bone.name))

        except Exception as e:
            logger.error(f"Error during Resonite conversion: {str(e)}")
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

        finally:
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
            except Exception as e:
                logger.warning(f"Error returning to object mode: {str(e)}")

        if translate_bone_fails > 0:
            logger.info(f"Conversion completed with {translate_bone_fails} untranslated bones")
            logger.debug(f"Untranslated bones: {untranslated_bones}")
            self.report({'INFO'}, t("Tools.bones_translated_with_fails", translate_bone_fails=translate_bone_fails))
        else:
            logger.info("All bones translated successfully")
            self.report({'INFO'}, t("Tools.bones_translated_success"))

        return {'FINISHED'}


def makeorexistingfcurve(action: bpy.types.Action,data_path: str,action_group: str, index=0) -> bpy.types.FCurve:
    fcurve = action.fcurves.find(data_path=data_path,index=index)
    if fcurve == None:
        return action.fcurves.new(data_path,action_group=action_group,index=index)
    else:
        print("fcurve with data \""+data_path+"\" already exists")
        return fcurve

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



        
    

    



    

