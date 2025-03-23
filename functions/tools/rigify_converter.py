import bpy
from typing import Dict, List, Set, Optional, Tuple, Any
from bpy.types import Operator, Context, Object, PoseBone, EditBone, Bone, Constraint
from ...core.common import get_active_armature
from ...core.logging_setup import logger
from ...core.translations import t
from ...core.dictionaries import rigify_unity_names, rigify_basic_unity_names, rigify_unnecessary_bones
from ...core.armature_validation import validate_armature

class AvatarToolkit_OT_ConvertRigifyToUnity(Operator):
    """Convert Rigify armature to Unity-compatible format"""
    bl_idname = "avatar_toolkit.convert_rigify_to_unity"
    bl_label = t("Tools.convert_rigify_to_unity")
    bl_description = t("Tools.convert_rigify_to_unity_desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        armature = get_active_armature(context)
        if not armature:
            return False
        return ("DEF-spine" in armature.data.bones or 
                "spine" in armature.data.bones and "metarig" in armature.name.lower())

    def execute(self, context: Context) -> Set[str]:
        try:
            logger.info("Starting Rigify to Unity conversion")
            armature = get_active_armature(context)
            if not armature:
                logger.error("No armature found")
                self.report({'ERROR'}, t("Tools.no_armature"))
                return {'CANCELLED'}

            logger.debug(f"Converting armature: {armature.name}")
            armature.name = "Armature"
            armature.data.name = "Armature"
            logger.debug("Renamed armature to 'Armature'")
            
            if "DEF-spine" in armature.data.bones:
                logger.info("Processing DEF bones")
                self.move_def_bones(armature)
                self.rename_bones_for_unity(armature)
            else:
                logger.info("Processing basic bones")
                self.cleanup_extra_bones(armature)
                self.rename_basic_bones_for_unity(armature)
            
            logger.debug("Cleaning up bone collections")
            self.cleanup_bone_collections(armature)
            
            if context.scene.avatar_toolkit.merge_twist_bones:
                logger.info("Merging twist bones")
                self.handle_twist_bones(armature)
                
            logger.info("Successfully converted Rigify armature to Unity format")
            self.report({'INFO'}, t("Tools.rigify_converted"))
            return {'FINISHED'}
            
        except Exception as e:
            logger.error(f"Failed to convert Rigify: {str(e)}", exc_info=True)
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

    def cleanup_extra_bones(self, armature: Object) -> None:
        """Remove unnecessary bones and merge neck bones"""
        logger.debug("Starting cleanup of extra bones")
        
        # Set armature as active object before mode switch
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode='EDIT')
        
        bones_to_remove: List[str] = []
        for bone in armature.data.edit_bones:
            if any(pattern in bone.name.lower() for pattern in rigify_unnecessary_bones):
                bones_to_remove.append(bone.name)
                
        for bone_name in bones_to_remove:
            if bone_name in armature.data.edit_bones:
                logger.debug(f"Removing bone: {bone_name}")
                armature.data.edit_bones.remove(armature.data.edit_bones[bone_name])
   
        if 'spine.004' in armature.data.edit_bones and 'spine.005' in armature.data.edit_bones:
            logger.debug("Merging neck bones")
            neck_start = armature.data.edit_bones['spine.004']
            neck_end = armature.data.edit_bones['spine.005']
            neck_start.tail = neck_end.tail
            armature.data.edit_bones.remove(neck_end)
            neck_start.name = "Neck"
            
        if 'spine.006' in armature.data.edit_bones:
            logger.debug("Renaming head bone")
            head_bone = armature.data.edit_bones['spine.006']
            head_bone.name = "Head"

    def move_def_bones(self, armature: Object) -> None:
        """Move DEF bones to their correct positions"""
        logger.debug("Moving DEF bones to correct positions")
        
        # Set armature as active object
        bpy.context.view_layer.objects.active = armature
        remap: Dict[str, str] = self.get_org_remap(armature)
        remap.update(self.get_special_remap())

        remove_bones_in_chain: List[str] = [
            'DEF-upper_arm.L.001', 'DEF-forearm.L.001',
            'DEF-upper_arm.R.001', 'DEF-forearm.R.001',
            'DEF-thigh.L.001', 'DEF-shin.L.001',
            'DEF-thigh.R.001', 'DEF-shin.R.001'
        ]

        transform_copies: List[str] = self.get_transform_copies(armature)

        logger.debug("Setting up transform copies")
        bpy.ops.object.mode_set(mode='POSE')
        for bone_name in transform_copies:
            bone = armature.pose.bones[bone_name]
            org_name = 'ORG-' + self.get_proto_name(bone_name)
            if org_name in armature.pose.bones:
                constraint = bone.constraints.new('COPY_TRANSFORMS')
                constraint.target = armature
                constraint.subtarget = org_name
                constr_count = len(bone.constraints)
                if constr_count > 1:
                    bone.constraints.move(constr_count-1, 0)

        logger.debug("Remapping bone parents")
        bpy.ops.object.mode_set(mode='EDIT')
        for remap_key in remap:
            if remap_key in armature.data.edit_bones and remap[remap_key] in armature.data.edit_bones:
                armature.data.edit_bones[remap_key].parent = armature.data.edit_bones[remap[remap_key]]

        logger.debug("Processing bone chain removal")
        bpy.ops.object.mode_set(mode='OBJECT')
        for bone_name in remove_bones_in_chain:
            if bone_name in armature.data.bones:
                armature.data.bones[bone_name].use_deform = False

        bpy.ops.object.mode_set(mode='EDIT')
        for bone_name in remove_bones_in_chain:
            if bone_name in armature.data.bones:
                remove_bone = armature.data.edit_bones[bone_name]
                parent_bone = remove_bone.parent
                parent_bone.tail = remove_bone.tail
                retarget_bones = list(remove_bone.children)
                for bone in retarget_bones:
                    bone.parent = parent_bone
                armature.data.edit_bones.remove(remove_bone)

    def rename_bones_for_unity(self, armature: Object) -> None:
        """Rename bones to Unity-compatible names"""
        logger.debug("Renaming bones to Unity format")
        for old_name, new_name in rigify_unity_names.items():
            bone = armature.pose.bones.get(old_name)
            if bone:
                logger.debug(f"Renaming bone: {old_name} -> {new_name}")
                bone.name = new_name

    def rename_basic_bones_for_unity(self, armature: Object) -> None:
        """Rename basic metarig bones to Unity-compatible names"""
        logger.debug("Renaming basic metarig bones")
        for old_name, new_name in rigify_basic_unity_names.items():
            bone = armature.pose.bones.get(old_name)
            if bone:
                logger.debug(f"Renaming basic bone: {old_name} -> {new_name}")
                bone.name = new_name

    def cleanup_bone_collections(self, armature: Object) -> None:
        """Remove all bone collections since they're not needed for Unity"""
        logger.debug("Cleaning up bone collections")
        if hasattr(armature.data, 'collections') and armature.data.collections:
            while len(armature.data.collections) > 0:
                collection = armature.data.collections[0]
                armature.data.collections.remove(collection)

            while len(armature.data.collections) > 1:
                collection = armature.data.collections[1]
                armature.data.collections.remove(collection)

    def handle_twist_bones(self, armature: Object) -> None:
        """Handle twist bones during conversion"""
        logger.debug("Processing twist bones")
        twist_bones: List[Tuple[str, str]] = [
            ("DEF-upper_arm_twist.L", "DEF-upper_arm.L"),
            ("DEF-upper_arm_twist.R", "DEF-upper_arm.R"),
            ("DEF-forearm_twist.L", "DEF-forearm.L"),
            ("DEF-forearm_twist.R", "DEF-forearm.R"),
            ("DEF-thigh_twist.L", "DEF-thigh.L"),
            ("DEF-thigh_twist.R", "DEF-thigh.R")
        ]

        bpy.ops.object.mode_set(mode='EDIT')
        for twist_bone, parent_bone in twist_bones:
            if twist_bone in armature.data.edit_bones and parent_bone in armature.data.edit_bones:
                logger.debug(f"Merging twist bone: {twist_bone} into {parent_bone}")
                twist = armature.data.edit_bones[twist_bone]
                parent = armature.data.edit_bones[parent_bone]
                parent.tail = twist.tail
                for child in twist.children:
                    child.parent = parent
                armature.data.edit_bones.remove(twist)

        bpy.ops.object.mode_set(mode='OBJECT')

    def get_org_remap(self, armature: Object) -> Dict[str, str]:
        """Get original bone remapping"""
        logger.debug("Getting original bone remapping")
        remap: Dict[str, str] = {}
        for bone in armature.data.bones:
            if self.is_def_bone(bone.name):
                name = self.get_proto_name(bone.name)
                parent = bone.parent
                while parent:
                    parent_name = self.get_proto_name(parent.name)
                    if parent_name != name:
                        if ('DEF-' + parent_name) in armature.data.bones:
                            remap[bone.name] = 'DEF-' + parent_name
                            break
                    parent = parent.parent
        return remap

    def get_special_remap(self) -> Dict[str, str]:
        """Get special bone remapping cases"""
        logger.debug("Getting special bone remapping")
        return {
            'DEF-thigh.L': 'DEF-pelvis.L',
            'DEF-thigh.R': 'DEF-pelvis.R',
            'DEF-upper_arm.L': 'DEF-shoulder.L',
            'DEF-upper_arm.R': 'DEF-shoulder.R',
        }

    def get_transform_copies(self, armature: Object) -> List[str]:
        """Get bones that need transform copies"""
        logger.debug("Getting transform copy bones")
        result: List[str] = []
        for bone in armature.pose.bones:
            if self.is_def_bone(bone.name) and not self.has_transform_copies(bone):
                result.append(bone.name)
        return result

    def has_transform_copies(self, bone: PoseBone) -> bool:
        """Check if bone has transform copy constraints"""
        return any(constraint.type == 'COPY_TRANSFORMS' for constraint in bone.constraints)

    def is_def_bone(self, bone_name: str) -> bool:
        """Check if bone is a DEF bone"""
        return bone_name.startswith('DEF-')

    def is_org_bone(self, bone_name: str) -> bool:
        """Check if bone is an ORG bone"""
        return bone_name.startswith('ORG-')

    def get_proto_name(self, bone_name: str) -> str:
        """Get the prototype name of a bone"""
        if self.is_def_bone(bone_name) or self.is_org_bone(bone_name):
            return bone_name[4:]
        return bone_name
