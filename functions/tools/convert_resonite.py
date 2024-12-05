import bpy
import re
from typing import Set, Dict, Optional
from bpy.types import Operator, Context
from ...core.translations import t
from ...core.logging_setup import logger
from ...core.common import get_active_armature, simplify_bonename, validate_armature, ProgressTracker
from ...core.dictionaries import bone_names, resonite_translations

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