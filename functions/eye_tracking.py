import os
import bpy
import copy
import math
import bmesh
import mathutils
import json
from bpy.types import Operator, Object, Context, UILayout, WindowManager, Event, ShapeKey, EditBone, PoseBone
from typing import Optional, Dict, Tuple, Set, List, Any, Union, ClassVar
from collections import OrderedDict
from random import random
from itertools import chain

from ..core.logging_setup import logger
from ..core.translations import t
from ..core.common import (
    ProgressTracker,
    get_active_armature,
    get_all_meshes,
    get_armature_list,
    validate_armature,
    validate_mesh_for_pose,
    cache_vertex_positions,
    apply_vertex_positions
)

VALID_EYE_NAMES: Dict[str, List[str]] = {
    'left': ['LeftEye', 'Eye_L', 'eye_L', 'eye.L', 'EyeLeft', 'left_eye', 'l_eye'],
    'right': ['RightEye', 'Eye_R', 'eye_R', 'eye.R', 'EyeRight', 'right_eye', 'r_eye']
}

class CreateEyesAV3Button(bpy.types.Operator):
    """Creates eye tracking setup compatible with VRChat Avatar 3.0 system"""
    bl_idname: str = 'avatar_toolkit.create_eye_tracking_av3'
    bl_label: str = t('EyeTracking.create.av3.label')
    bl_description: str = t('EyeTracking.create.av3.desc')
    bl_options: Set[str] = {'REGISTER', 'UNDO'}

    mesh: Optional[Object] = None

    @classmethod
    def poll(cls, context):
        toolkit = context.scene.avatar_toolkit
        if not toolkit.head or not toolkit.eye_left or not toolkit.eye_right:
            return False
        return True

    def execute(self, context):
        toolkit = context.scene.avatar_toolkit
        armature = get_active_armature(context)
        
        with ProgressTracker(context, 100, "Creating AV3 Eye Tracking") as progress:
            try:
                context.view_layer.objects.active = armature
                bpy.ops.object.mode_set(mode='EDIT')
                progress.step("Setting up bones")

                # Set up bones
                head = armature.data.edit_bones.get(toolkit.head)
                old_eye_left = armature.data.edit_bones.get(toolkit.eye_left)
                old_eye_right = armature.data.edit_bones.get(toolkit.eye_right)

                # Store original names and transformations
                left_name = old_eye_left.name
                right_name = old_eye_right.name
                left_matrix = old_eye_left.matrix.copy()
                right_matrix = old_eye_right.matrix.copy()
                left_length = old_eye_left.length
                right_length = old_eye_right.length

                # Unparent and remove original bones
                old_eye_left.parent = None
                old_eye_right.parent = None
                armature.data.edit_bones.remove(old_eye_left)
                armature.data.edit_bones.remove(old_eye_right)

                # Create new eye bones with original names
                new_left_eye = armature.data.edit_bones.new(left_name)
                new_right_eye = armature.data.edit_bones.new(right_name)
                
                # Parent them
                new_left_eye.parent = head
                new_right_eye.parent = head

                # Calculate straight up orientation matrix
                straight_up_matrix = mathutils.Matrix.Rotation(math.pi/2, 3, 'X')

                # Apply rotation while preserving position
                for eye_data in [(new_left_eye, left_matrix, left_length), 
                               (new_right_eye, right_matrix, right_length)]:
                    new_eye, orig_matrix, length = eye_data
                    new_matrix = straight_up_matrix.to_4x4()
                    new_matrix.translation = orig_matrix.translation
                    new_eye.matrix = new_matrix
                    new_eye.length = length

                # Disable mirroring to prevent unwanted behavior
                armature.data.use_mirror_x = False


                progress.step("Finalizing setup")
                bpy.ops.object.mode_set(mode='OBJECT')
                
                self.report({'INFO'}, t('EyeTracking.success'))
                return {'FINISHED'}

            except Exception as e:
                logger.error(f"Eye tracking setup failed: {str(e)}")
                return {'CANCELLED'}

class CreateEyesSDK2Button(bpy.types.Operator):
    """Creates eye tracking setup compatible with VRChat SDK2 system"""
    bl_idname: str = 'avatar_toolkit.create_eye_tracking_sdk2'
    bl_label: str = t('EyeTracking.create.sdk2.label')
    bl_description: str = t('EyeTracking.create.sdk2.desc')
    bl_options: Set[str] = {'REGISTER', 'UNDO'}

    mesh: Optional[Object] = None

    @classmethod
    def poll(cls, context):
        if not get_all_meshes(context):
            return False

        toolkit = context.scene.avatar_toolkit
        if not toolkit.head or not toolkit.eye_left or not toolkit.eye_right:
            return False

        if toolkit.disable_eye_blinking and toolkit.disable_eye_movement:
            return False

        return True

    def execute(self, context):
        toolkit = context.scene.avatar_toolkit
        armature = get_active_armature(context)
        
        with ProgressTracker(context, 100, "Creating SDK2 Eye Tracking") as progress:
            # Validate setup
            validator = EyeTrackingValidator()
            is_valid, message = validator.validate_setup(context, toolkit.mesh_name_eye)
            if not is_valid:
                self.report({'ERROR'}, message)
                return {'CANCELLED'}

            try:
                context.view_layer.objects.active = armature
                bpy.ops.object.mode_set(mode='EDIT')
                progress.step("Setting up bones")

                self.mesh = bpy.data.objects.get(toolkit.mesh_name_eye)

                # Set up bones
                head = armature.data.edit_bones.get(toolkit.head)
                old_eye_left = armature.data.edit_bones.get(toolkit.eye_left)
                old_eye_right = armature.data.edit_bones.get(toolkit.eye_right)

                # Create new eye bones
                new_left_eye = armature.data.edit_bones.new('LeftEye')
                new_right_eye = armature.data.edit_bones.new('RightEye')
                
                # Parent them
                new_left_eye.parent = head
                new_right_eye.parent = head

                # Calculate positions for SDK2 style
                fix_eye_position(context, old_eye_left, new_left_eye, head, False)
                fix_eye_position(context, old_eye_right, new_right_eye, head, True)

                progress.step("Processing vertex groups")
                if not toolkit.disable_eye_movement:
                    # Switch to object mode for vertex group operations
                    bpy.ops.object.mode_set(mode='OBJECT')
                    bpy.ops.object.select_all(action='DESELECT')
                    self.mesh.select_set(True)
                    context.view_layer.objects.active = self.mesh
                    
                    copy_vertex_group(self, old_eye_left.name, 'LeftEye')
                    copy_vertex_group(self, old_eye_right.name, 'RightEye')
                    
                    # Return to armature edit mode
                    context.view_layer.objects.active = armature
                    bpy.ops.object.mode_set(mode='EDIT')

                progress.step("Processing shape keys")
                if not toolkit.disable_eye_blinking:
                    shapes = [toolkit.wink_left, toolkit.wink_right,
                             toolkit.lowerlid_left, toolkit.lowerlid_right]
                    new_shapes = ['vrc.blink_left', 'vrc.blink_right',
                                'vrc.lowerlid_left', 'vrc.lowerlid_right']

                progress.step("Finalizing setup")
                bpy.ops.object.mode_set(mode='OBJECT')
                toolkit.eye_mode = 'TESTING'
                
                self.report({'INFO'}, t('EyeTracking.success'))
                return {'FINISHED'}

            except Exception as e:
                logger.error(f"Eye tracking setup failed: {str(e)}")
                return {'CANCELLED'}

class EyeTrackingBackup:
    """Manages backup and restoration of eye bone positions"""
    def __init__(self) -> None:
        self.backup_path: str = os.path.join(bpy.app.tempdir, "eye_tracking_backup.json")
        self.bone_positions: Dict[str, Dict[str, Tuple[float, float, float]]] = {}
        
    def store_bone_positions(self, armature) -> bool:
        try:
            self.bone_positions = {
                'LeftEye': {
                    'head': tuple(armature.data.bones['LeftEye'].head_local),
                    'tail': tuple(armature.data.bones['LeftEye'].tail_local)
                },
                'RightEye': {
                    'head': tuple(armature.data.bones['RightEye'].head_local),
                    'tail': tuple(armature.data.bones['RightEye'].tail_local)
                }
            }
            
            with open(self.backup_path, 'w') as f:
                json.dump(self.bone_positions, f)
            return True
        except Exception as e:
            logger.error(f"Backup failed: {str(e)}")
            return False
            
    def restore_bone_positions(self, armature) -> bool:
        try:
            if not os.path.exists(self.backup_path):
                return False
                
            with open(self.backup_path, 'r') as f:
                backup_data = json.load(f)
                
            bpy.ops.object.mode_set(mode='EDIT')
            
            for bone_name, positions in backup_data.items():
                if bone_name in armature.data.edit_bones:
                    bone = armature.data.edit_bones[bone_name]
                    bone.head = positions['head']
                    bone.tail = positions['tail']
                    
            return True
        except Exception as e:
            logger.error(f"Restore failed: {str(e)}")
            return False

class EyeTrackingValidator:
    """Validates eye tracking setup requirements and configurations"""
    @staticmethod
    def find_eye_vertex_groups(mesh_name: str) -> Tuple[Optional[str], Optional[str]]:
        """Locates left and right eye vertex groups in mesh"""
        mesh = bpy.data.objects.get(mesh_name)
        if not mesh:
            return None, None
            
        left_group = None
        right_group = None
        
        for group in mesh.vertex_groups:
            if any(name.lower() in group.name.lower() for name in VALID_EYE_NAMES['left']):
                left_group = group.name
            if any(name.lower() in group.name.lower() for name in VALID_EYE_NAMES['right']):
                right_group = group.name
                
        return left_group, right_group

    @staticmethod
    def validate_setup(context: Context, mesh_name: str) -> Tuple[bool, str]:
        """Validates complete eye tracking setup configuration"""
        armature = get_active_armature(context)
        if not armature:
            return False, t('EyeTracking.validation.noArmature')
            
        mesh = bpy.data.objects.get(mesh_name)
        if not mesh:
            return False, t('EyeTracking.validation.noMesh', mesh=mesh_name)
            
        if not mesh.data.shape_keys:
            return False, t('EyeTracking.validation.noShapekeys')
            
        left_group, right_group = EyeTrackingValidator.find_eye_vertex_groups(mesh_name)
        missing_groups = []
        
        if not left_group:
            missing_groups.append(t('EyeTracking.validation.leftEye'))
        if not right_group:
            missing_groups.append(t('EyeTracking.validation.rightEye'))
            
        if missing_groups:
            return False, t('EyeTracking.validation.missingGroups', groups=', '.join(missing_groups))
            
        required_bones = [context.scene.avatar_toolkit.head, 
                         context.scene.avatar_toolkit.eye_left, 
                         context.scene.avatar_toolkit.eye_right]
        missing_bones = [bone for bone in required_bones if bone not in armature.data.bones]
        
        if missing_bones:
            return False, t('EyeTracking.validation.missingBones', bones=', '.join(missing_bones))
            
        return True, t('EyeTracking.validation.success')
            
class StartTestingButton(bpy.types.Operator):
    """Initiates eye tracking testing mode"""
    bl_idname: str = 'avatar_toolkit.start_eye_testing'
    bl_label: str = t('EyeTracking.testing.start.label')
    bl_description: str = t('EyeTracking.testing.start.desc')
    bl_options: Set[str] = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        armature = get_active_armature(context)
        return armature and 'LeftEye' in armature.pose.bones and 'RightEye' in armature.pose.bones

    def execute(self, context):
        armature = get_active_armature(context)
        bpy.ops.object.mode_set(mode='POSE')
        armature.data.pose_position = 'POSE'

        global eye_left, eye_right, eye_left_data, eye_right_data, eye_left_rot, eye_right_rot
        eye_left = armature.pose.bones.get('LeftEye')
        eye_right = armature.pose.bones.get('RightEye')
        eye_left_data = armature.data.bones.get('LeftEye')
        eye_right_data = armature.data.bones.get('RightEye')

        # Save initial rotations
        eye_left.rotation_mode = 'XYZ'
        eye_left_rot = copy.deepcopy(eye_left.rotation_euler)
        eye_right.rotation_mode = 'XYZ'
        eye_right_rot = copy.deepcopy(eye_right.rotation_euler)

        if not all([eye_left, eye_right, eye_left_data, eye_right_data]):
            return {'FINISHED'}

        # Reset shape keys
        mesh = bpy.data.objects[context.scene.avatar_toolkit.mesh_name_eye]
        for shape_key in mesh.data.shape_keys.key_blocks:
            shape_key.value = 0

        # Clear transforms
        for pb in armature.data.bones:
            pb.select = True
        bpy.ops.pose.transforms_clear()
        for pb in armature.data.bones:
            pb.select = False
            pb.hide = True

        eye_left_data.hide = False
        eye_right_data.hide = False

        context.scene.avatar_toolkit.eye_rotation_x = 0
        context.scene.avatar_toolkit.eye_rotation_y = 0

        return {'FINISHED'}
    
class StopTestingButton(bpy.types.Operator):
    """Terminates eye tracking testing mode"""
    bl_idname: str = 'avatar_toolkit.stop_eye_testing'
    bl_label: str = t('EyeTracking.testing.stop.label')
    bl_description: str = t('EyeTracking.testing.stop.desc')
    bl_options: Set[str] = {'REGISTER', 'UNDO'}

    def execute(self, context):
        global eye_left, eye_right, eye_left_data, eye_right_data, eye_left_rot, eye_right_rot
        toolkit = context.scene.avatar_toolkit
        
        if eye_left:
            toolkit.eye_rotation_x = 0
            toolkit.eye_rotation_y = 0

        if not context.object or context.object.mode != 'POSE':
            armature = get_active_armature(context)
            bpy.ops.object.mode_set(mode='POSE')

        armature = get_active_armature(context)
        for pb in armature.data.bones:
            pb.hide = False
            pb.select = True
        bpy.ops.pose.transforms_clear()
        for pb in armature.data.bones:
            pb.select = False

        mesh = bpy.data.objects[toolkit.mesh_name_eye]
        for shape_key in mesh.data.shape_keys.key_blocks:
            shape_key.value = 0

        eye_left = None
        eye_right = None
        eye_left_data = None
        eye_right_data = None
        eye_left_rot = []
        eye_right_rot = []

        bpy.ops.object.mode_set(mode='OBJECT')

        return {'FINISHED'}

def set_rotation(self, context):
    """Updates eye bone rotations based on current settings"""
    global eye_left, eye_right, eye_left_rot, eye_right_rot
    toolkit = context.scene.avatar_toolkit

    if not eye_left or not eye_right:
        StartTestingButton.execute(StartTestingButton, context)
        return None

    eye_left.rotation_mode = 'XYZ'
    eye_right.rotation_mode = 'XYZ'

    x_rotation = math.radians(toolkit.eye_rotation_x)
    y_rotation = math.radians(toolkit.eye_rotation_y)
    
    eye_left.rotation_euler[0] = eye_left_rot[0] + x_rotation
    eye_left.rotation_euler[1] = eye_left_rot[1] + y_rotation

    eye_right.rotation_euler[0] = eye_right_rot[0] + x_rotation
    eye_right.rotation_euler[1] = eye_right_rot[1] + y_rotation

    return None

class ResetRotationButton(bpy.types.Operator):
    """Resets eye bone rotations to default values"""
    bl_idname: str = 'avatar_toolkit.reset_eye_rotation'
    bl_label: str = t('EyeTracking.reset.label')
    bl_description: str = t('EyeTracking.reset.desc')
    bl_options: Set[str] = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        armature = get_active_armature(context)
        return armature and 'LeftEye' in armature.pose.bones and 'RightEye' in armature.pose.bones

    def execute(self, context):
        toolkit = context.scene.avatar_toolkit
        armature = get_active_armature(context)

        toolkit.eye_rotation_x = 0
        toolkit.eye_rotation_y = 0

        global eye_left, eye_right, eye_left_data, eye_right_data
        eye_left = armature.pose.bones.get('LeftEye')
        eye_right = armature.pose.bones.get('RightEye')
        eye_left_data = armature.data.bones.get('LeftEye')
        eye_right_data = armature.data.bones.get('RightEye')

        for eye in [eye_left, eye_right]:
            eye.rotation_mode = 'XYZ'
            for i in range(3):
                eye.rotation_euler[i] = 0

        return {'FINISHED'}

class AdjustEyesButton(bpy.types.Operator):
    """Adjusts eye bone positions and orientations"""
    bl_idname: str = 'avatar_toolkit.adjust_eyes'
    bl_label: str = t('EyeTracking.adjust.label')
    bl_description: str = t('EyeTracking.adjust.desc')
    bl_options: Set[str] = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        armature = get_active_armature(context)
        return armature and all(bone in armature.pose.bones for bone in ['LeftEye', 'RightEye'])

    def execute(self, context):
        toolkit = context.scene.avatar_toolkit
        if toolkit.disable_eye_movement:
            return {'FINISHED'}

        mesh_name = toolkit.mesh_name_eye
        mesh = bpy.data.objects.get(mesh_name)

        if not mesh:
            self.report({'ERROR'}, t('EyeTracking.error.noMesh'))
            return {'CANCELLED'}

        for eye in ['LeftEye', 'RightEye']:
            if not any(g.group == mesh.vertex_groups[eye].index for v in mesh.data.vertices for g in v.groups):
                self.report({'ERROR'}, t('EyeTracking.error.noVertexGroup', bone=eye))
                return {'CANCELLED'}

        armature = get_active_armature(context)
        bpy.ops.object.mode_set(mode='EDIT')

        new_eye_left = armature.data.edit_bones.get('LeftEye')
        new_eye_right = armature.data.edit_bones.get('RightEye')
        old_eye_left = armature.pose.bones.get(toolkit.eye_left)
        old_eye_right = armature.pose.bones.get(toolkit.eye_right)

        fix_eye_position(context, old_eye_left, new_eye_left, None, False)
        fix_eye_position(context, old_eye_right, new_eye_right, None, True)

        bpy.ops.object.mode_set(mode='POSE')

        global eye_left, eye_right, eye_left_data, eye_right_data
        eye_left = armature.pose.bones.get('LeftEye')
        eye_right = armature.pose.bones.get('RightEye')
        eye_left_data = armature.data.bones.get('LeftEye')
        eye_right_data = armature.data.bones.get('RightEye')

        return {'FINISHED'}
    
class StartIrisHeightButton(bpy.types.Operator):
    """Adjusts iris height for eye meshes"""
    bl_idname: str = 'avatar_toolkit.adjust_iris_height'
    bl_label: str = t('EyeTracking.iris.label')
    bl_description: str = t('EyeTracking.iris.desc')
    bl_options: Set[str] = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        armature = get_active_armature(context)
        return armature and all(bone in armature.pose.bones for bone in ['LeftEye', 'RightEye'])

    def execute(self, context):
        toolkit = context.scene.avatar_toolkit
        if toolkit.disable_eye_movement:
            return {'FINISHED'}

        armature = get_active_armature(context)
        armature.hide_viewport = True

        mesh = bpy.data.objects[toolkit.mesh_name_eye]
        mesh.select_set(True)
        context.view_layer.objects.active = mesh
        bpy.ops.object.mode_set(mode='EDIT')

        if len(mesh.vertex_groups) > 0:
            bpy.ops.mesh.select_mode(type='VERT')

            for vg_name in ['LeftEye', 'RightEye']:
                vg = mesh.vertex_groups.get(vg_name)
                if vg:
                    bpy.ops.object.vertex_group_set_active(group=vg.name)
                    bpy.ops.object.vertex_group_select()

            bm = bmesh.from_edit_mesh(mesh.data)
            for v in bm.verts:
                if v.select:
                    v.co.y += toolkit.iris_height * 0.01
                    logger.debug(f"Adjusted vertex position: {v.co}")
            bmesh.update_edit_mesh(mesh.data)

        return {'FINISHED'}

class TestBlinking(bpy.types.Operator):
    """Tests eye blinking animations"""
    bl_idname: str = 'avatar_toolkit.test_blinking'
    bl_label: str = t('EyeTracking.blink.test.label')
    bl_description: str = t('EyeTracking.blink.test.desc')
    bl_options: Set[str] = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        toolkit = context.scene.avatar_toolkit
        mesh = bpy.data.objects.get(toolkit.mesh_name_eye)
        return (mesh and mesh.data.shape_keys and 
                all(key in mesh.data.shape_keys.key_blocks for key in ['vrc.blink_left', 'vrc.blink_right']))

    def execute(self, context):
        toolkit = context.scene.avatar_toolkit
        mesh = bpy.data.objects[toolkit.mesh_name_eye]
        shapes = ['vrc.blink_left', 'vrc.blink_right']

        for shape_key in mesh.data.shape_keys.key_blocks:
            shape_key.value = toolkit.eye_blink_shape if shape_key.name in shapes else 0

        return {'FINISHED'}
    
class TestLowerlid(bpy.types.Operator):
    """Tests lower eyelid movements"""
    bl_idname: str = 'avatar_toolkit.test_lowerlid'
    bl_label: str = t('EyeTracking.lowerlid.test.label')
    bl_description: str = t('EyeTracking.lowerlid.test.desc')
    bl_options: Set[str] = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        toolkit = context.scene.avatar_toolkit
        mesh = bpy.data.objects.get(toolkit.mesh_name_eye)
        return (mesh and mesh.data.shape_keys and 
                all(key in mesh.data.shape_keys.key_blocks for key in ['vrc.lowerlid_left', 'vrc.lowerlid_right']))

    def execute(self, context):
        toolkit = context.scene.avatar_toolkit
        mesh = bpy.data.objects[toolkit.mesh_name_eye]
        shapes = OrderedDict()
        shapes['vrc.lowerlid_left'] = toolkit.eye_lowerlid_shape
        shapes['vrc.lowerlid_right'] = toolkit.eye_lowerlid_shape

        for shape_key in mesh.data.shape_keys.key_blocks:
            shape_key.value = toolkit.eye_lowerlid_shape if shape_key.name in shapes else 0

        return {'FINISHED'}

class ResetBlinkTest(bpy.types.Operator):
    """Resets all eye blinking test values"""
    bl_idname: str = 'avatar_toolkit.reset_blink_test'
    bl_label: str = t('EyeTracking.blink.reset.label')
    bl_description: str = t('EyeTracking.blink.reset.desc')
    bl_options: Set[str] = {'REGISTER', 'UNDO'}

    def execute(self, context):
        toolkit = context.scene.avatar_toolkit
        mesh = bpy.data.objects[toolkit.mesh_name_eye]
        
        for shape_key in mesh.data.shape_keys.key_blocks:
            shape_key.value = 0
            
        toolkit.eye_blink_shape = 1
        toolkit.eye_lowerlid_shape = 1

        return {'FINISHED'}

def fix_eye_position(context: Context, old_eye: Union[EditBone, PoseBone], new_eye: EditBone, head: Optional[EditBone], right_side: bool) -> None:
    """Adjusts eye bone positions and orientations for proper tracking"""
    toolkit = context.scene.avatar_toolkit
    scale = -toolkit.eye_distance + 1
    mesh = bpy.data.objects[toolkit.mesh_name_eye]

    if not toolkit.disable_eye_movement:
        if head:
            coords_eye = find_center_vector_of_vertex_group(mesh, old_eye.name)
        else:
            coords_eye = find_center_vector_of_vertex_group(mesh, new_eye.name)

        if coords_eye is False:
            return

        if head:
            p1 = mesh.matrix_world @ head.head
            p2 = mesh.matrix_world @ coords_eye
            length = (p1 - p2).length
            logger.debug(f"Eye distance: {length}")

    x_cord, y_cord, z_cord = get_bone_orientations()

    if toolkit.disable_eye_movement:
        if head is not None:
            new_eye.head[x_cord] = head.head[x_cord] + (0.05 if right_side else -0.05)
            new_eye.head[y_cord] = head.head[y_cord]
            new_eye.head[z_cord] = head.head[z_cord]
    else:
        new_eye.head[x_cord] = old_eye.head[x_cord] + scale * (coords_eye[0] - old_eye.head[x_cord])
        new_eye.head[y_cord] = old_eye.head[y_cord] + scale * (coords_eye[1] - old_eye.head[y_cord])
        new_eye.head[z_cord] = old_eye.head[z_cord] + scale * (coords_eye[2] - old_eye.head[z_cord])

    new_eye.tail[x_cord] = new_eye.head[x_cord]
    new_eye.tail[y_cord] = new_eye.head[y_cord]
    new_eye.tail[z_cord] = new_eye.head[z_cord] + 0.1

def repair_shapekeys(mesh_name: str, vertex_group: str) -> None:
    """Repairs VRChat shape keys by adjusting vertex positions"""
    armature = get_active_armature(bpy.context)
    mesh = bpy.data.objects[mesh_name]
    mesh.select_set(True)
    bpy.context.view_layer.objects.active = mesh
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.object.mode_set(mode='OBJECT')

    bm = bmesh.new()
    bm.from_mesh(mesh.data)
    bm.verts.ensure_lookup_table()

    logger.debug(f'Processing vertex group: {vertex_group}')
    group = mesh.vertex_groups.get(vertex_group)
    if group is None:
        logger.warning(f'Group {vertex_group} not found, using fallback method')
        repair_shapekeys_mouth(mesh_name)
        return

    vcoords = None
    gi = group.index
    for v in mesh.data.vertices:
        for g in v.groups:
            if g.group == gi:
                vcoords = v.co.xyz

    if not vcoords:
        return

    logger.info('Repairing shape keys')
    moved = False
    i = 0
    for key in bm.verts.layers.shape.keys():
        if not key.startswith('vrc.'):
            continue
        logger.debug(f'Repairing shape: {key}')
        value = bm.verts.layers.shape.get(key)
        for index, vert in enumerate(bm.verts):
            if vert.co.xyz == vcoords:
                if index < i:
                    continue
                shapekey = vert
                shapekey_coords = mesh.matrix_world @ shapekey[value]
                shapekey_coords[0] -= 0.00007 * randBoolNumber()
                shapekey_coords[1] -= 0.00007 * randBoolNumber()
                shapekey_coords[2] -= 0.00007 * randBoolNumber()
                shapekey[value] = mesh.matrix_world.inverted() @ shapekey_coords
                logger.debug(f'Repaired shape: {key}')
                i += 1
                moved = True
                break

    bm.to_mesh(mesh.data)

    if not moved:
        logger.warning('Shape key repair failed, using random method')
        repair_shapekeys_mouth(mesh_name)

def randBoolNumber() -> int:
    """Generates random boolean value as integer"""
    return -1 if random() < 0.5 else 1

def repair_shapekeys_mouth(mesh_name: str) -> None:
    """Repairs mouth-related shape keys using fallback method"""
    mesh = bpy.data.objects[mesh_name]
    mesh.select_set(True)
    bpy.context.view_layer.objects.active = mesh
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.object.mode_set(mode='OBJECT')

    bm = bmesh.new()
    bm.from_mesh(mesh.data)
    bm.verts.ensure_lookup_table()

    moved = False
    for key in bm.verts.layers.shape.keys():
        if not key.startswith('vrc'):
            continue
        value = bm.verts.layers.shape.get(key)
        for vert in bm.verts:
            shapekey = vert
            shapekey_coords = mesh.matrix_world @ shapekey[value]
            shapekey_coords[0] -= 0.00007
            shapekey_coords[1] -= 0.00007
            shapekey_coords[2] -= 0.00007
            shapekey[value] = mesh.matrix_world.inverted() @ shapekey_coords
            moved = True
            break

    bm.to_mesh(mesh.data)

    if not moved:
        logger.error('Random shape key repair failed')

def get_bone_orientations() -> Tuple[int, int, int]:
    """Returns standardized bone orientation axes"""
    return (0, 1, 2)  # x, y, z coordinates

def find_center_vector_of_vertex_group(mesh: Object, group_name: str) -> Union[mathutils.Vector, bool]:
    """Calculates center position of vertex group"""
    group = mesh.vertex_groups.get(group_name)
    if not group:
        return False

    vertices = []
    for vert in mesh.data.vertices:
        for g in vert.groups:
            if g.group == group.index:
                vertices.append(vert.co)

    if not vertices:
        return False

    return sum((v for v in vertices), mathutils.Vector()) / len(vertices)

def vertex_group_exists(mesh_obj: Object, group_name: str) -> bool:
    """Verifies existence and validity of vertex group"""
    if not mesh_obj or group_name not in mesh_obj.vertex_groups:
        return False
        
    group = mesh_obj.vertex_groups[group_name]
    for vert in mesh_obj.data.vertices:
        for g in vert.groups:
            if g.group == group.index and g.weight > 0:
                return True
    return False

def copy_vertex_group(self: Any, vertex_group: str, rename_to: str) -> None:
    """Creates copy of vertex group with new name"""
    vertex_group_index = 0
    # Select and make mesh active
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    self.mesh.select_set(True)
    bpy.context.view_layer.objects.active = self.mesh
    
    for group in self.mesh.vertex_groups:
        if group.name == vertex_group:
            self.mesh.vertex_groups.active_index = vertex_group_index
            bpy.ops.object.vertex_group_copy()
            self.mesh.vertex_groups[vertex_group + '_copy'].name = rename_to
            break
        vertex_group_index += 1


def copy_shape_key(self: Any, context: Context, from_shape: str, new_names: List[str], new_index: int) -> str:
    """Creates copy of shape key with new name"""
    blinking = not context.scene.avatar_toolkit.disable_eye_blinking
    new_name = new_names[new_index - 1]

    # Rename existing shapekey if it exists
    for shapekey in self.mesh.data.shape_keys.key_blocks:
        shapekey.value = 0
        if shapekey.name == new_name:
            shapekey.name = shapekey.name + '_old'
            if from_shape == new_name:
                from_shape = shapekey.name

    # Create new shape key
    for index, shapekey in enumerate(self.mesh.data.shape_keys.key_blocks):
        if from_shape == shapekey.name:
            self.mesh.active_shape_key_index = index
            shapekey.value = 1
            self.mesh.shape_key_add(name=new_name, from_mix=blinking)
            break

    # Reset shape keys
    for shapekey in self.mesh.data.shape_keys.key_blocks:
        shapekey.value = 0
    self.mesh.active_shape_key_index = 0

    return from_shape

# Global state for eye tracking
eye_left = None
eye_right = None
eye_left_data = None
eye_right_data = None
eye_left_rot = []
eye_right_rot = []

class VertexGroupCache:
    """Cache for vertex group operations"""
    _cache = {}
    
    @classmethod
    def get_vertex_indices(cls, mesh_name: str, group_name: str) -> Optional[set]:
        cache_key = f"{mesh_name}_{group_name}"
        
        if cache_key in cls._cache:
            return cls._cache[cache_key]
            
        mesh = bpy.data.objects.get(mesh_name)
        if not mesh:
            return None
            
        group = mesh.vertex_groups.get(group_name)
        if not group:
            return None
            
        indices = {v.index for v in mesh.data.vertices
                  if any(g.group == group.index for g in v.groups)}
                  
        cls._cache[cache_key] = indices
        return indices
    
    @classmethod
    def clear_cache(cls):
        cls._cache.clear()

class RotateEyeBonesForAv3Button(Operator):
    """Reorients eye bones for VRChat Avatar 3.0 compatibility"""
    bl_idname: str = "avatar_toolkit.rotate_eye_bones"
    bl_label: str = t("EyeTracking.rotate.label")
    bl_description: str = t("EyeTracking.rotate.desc")
    bl_options: Set[str] = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        armature = get_active_armature(context)
        return armature and all(bone in armature.pose.bones for bone in ['LeftEye', 'RightEye'])

    def execute(self, context):
        armature = get_active_armature(context)
        straight_up_matrix = mathutils.Matrix.Rotation(math.pi/2, 3, 'X')
        
        bpy.ops.object.mode_set(mode='EDIT')
        
        for eye_name in ['LeftEye', 'RightEye']:
            eye_bone = armature.data.edit_bones[eye_name]
            new_matrix = straight_up_matrix.to_4x4()
            new_matrix.translation = eye_bone.matrix.translation
            eye_bone.matrix = new_matrix
            
        bpy.ops.object.mode_set(mode='OBJECT')
        return {'FINISHED'}

class ResetEyeTrackingButton(Operator):
    """Resets all eye tracking settings to default values"""
    bl_idname: str = 'avatar_toolkit.reset_eye_tracking'
    bl_label: str = t('EyeTracking.reset.label')
    bl_description: str = t('EyeTracking.reset.desc')
    bl_options: Set[str] = {'REGISTER', 'UNDO'}

    def execute(self, context):
        global eye_left, eye_right, eye_left_data, eye_right_data, eye_left_rot, eye_right_rot
        eye_left = eye_right = eye_left_data = eye_right_data = None
        eye_left_rot = eye_right_rot = []
        context.scene.avatar_toolkit.eye_mode = 'CREATION'
        return {'FINISHED'}

def validate_weights(mesh_obj: Object, vertex_group: str) -> bool:
    """Validates vertex group weight assignments"""
    group = mesh_obj.vertex_groups.get(vertex_group)
    if not group:
        return False
        
    for vertex in mesh_obj.data.vertices:
        for group_element in vertex.groups:
            if group_element.group == group.index and group_element.weight > 0:
                return True
    return False

def get_eye_bone_names(armature: Object) -> Dict[str, Optional[str]]:
    """Retrieves standardized eye bone names from armature"""
    eye_bones = {'left': None, 'right': None}
    
    for bone in armature.data.bones:
        if any(name.lower() in bone.name.lower() for name in VALID_EYE_NAMES['left']):
            eye_bones['left'] = bone.name
        if any(name.lower() in bone.name.lower() for name in VALID_EYE_NAMES['right']):
            eye_bones['right'] = bone.name
            
    return eye_bones

def stop_testing(context: Context) -> None:
    """Stops eye tracking testing mode and resets all values"""
    global eye_left, eye_right, eye_left_data, eye_right_data, eye_left_rot, eye_right_rot
    
    if not all([eye_left, eye_right, eye_left_data, eye_right_data, eye_left_rot, eye_right_rot]):
        return
        
    armature = get_active_armature(context)
    if not armature:
        return
        
    bpy.ops.object.mode_set(mode='POSE')
    
    # Reset rotations
    context.scene.avatar_toolkit.eye_rotation_x = 0
    context.scene.avatar_toolkit.eye_rotation_y = 0
    
    # Clear transforms
    for bone in armature.data.bones:
        bone.hide = False
        bone.select = True
    bpy.ops.pose.transforms_clear()
    
    # Reset shape keys
    mesh = bpy.data.objects.get(context.scene.avatar_toolkit.mesh_name_eye)
    if mesh and mesh.data.shape_keys:
        for shape_key in mesh.data.shape_keys.key_blocks:
            shape_key.value = 0
    
    # Clear globals
    eye_left = eye_right = eye_left_data = eye_right_data = None
    eye_left_rot = eye_right_rot = []
