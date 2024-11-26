from io import BufferedReader
import os
import bpy
import struct
import traceback
import mathutils
from mathutils import Matrix, Vector

class PMXVertex:
    def __init__(self, position, normal, uv, bone_indices, bone_weights, edge_scale, additional_uvs):
        self.position = position
        self.normal = normal
        self.uv = uv
        self.bone_indices = bone_indices
        self.bone_weights = bone_weights
        self.edge_scale = edge_scale
        self.additional_uvs = additional_uvs

class PMXBone:
    def __init__(self, name, english_name, position, parent_index, layer, flag, 
                 tail_position, inherit_parent_index, inherit_influence, 
                 fixed_axis, local_x, local_z, external_key, 
                 ik_target_index, ik_loop_count, ik_limit_rad, ik_links):
        self.name = name
        self.english_name = english_name
        self.position = position
        self.parent_index = parent_index
        self.layer = layer
        self.flag = flag
        self.tail_position = tail_position
        self.inherit_parent_index = inherit_parent_index
        self.inherit_influence = inherit_influence
        self.fixed_axis = fixed_axis
        self.local_x = local_x
        self.local_z = local_z
        self.external_key = external_key
        self.ik_target_index = ik_target_index
        self.ik_loop_count = ik_loop_count
        self.ik_limit_rad = ik_limit_rad
        self.ik_links = ik_links

class PMXMaterial:
    def __init__(self, name, english_name, diffuse, specular, specular_strength,
                 ambient, flag, edge_color, edge_size, texture_index,
                 sphere_texture_index, sphere_mode, toon_sharing_flag,
                 toon_texture_index, comment, surface_count):
        self.name = name
        self.english_name = english_name
        self.diffuse = diffuse
        self.specular = specular
        self.specular_strength = specular_strength
        self.ambient = ambient
        self.flag = flag
        self.edge_color = edge_color
        self.edge_size = edge_size
        self.texture_index = texture_index
        self.sphere_texture_index = sphere_texture_index
        self.sphere_mode = sphere_mode
        self.toon_sharing_flag = toon_sharing_flag
        self.toon_texture_index = toon_texture_index
        self.comment = comment
        self.surface_count = surface_count

class PMXMorph:
    def __init__(self, name, english_name, panel, morph_type, offsets):
        self.name = name
        self.english_name = english_name
        self.panel = panel
        self.morph_type = morph_type
        self.offsets = offsets

class PMXRigidBody:
    def __init__(self, name, bone_index, group, shape_type, size, position, rotation, mass, linear_damping, angular_damping, restitution, friction, mode):
        self.name = name
        self.bone_index = bone_index
        self.group = group
        self.shape_type = shape_type
        self.size = size
        self.position = position
        self.rotation = rotation
        self.mass = mass
        self.linear_damping = linear_damping
        self.angular_damping = angular_damping
        self.restitution = restitution
        self.friction = friction
        self.mode = mode

class PMXJoint:
    def __init__(self, name, joint_type, rigid_body_a, rigid_body_b, position, rotation, linear_limit_min, linear_limit_max, angular_limit_min, angular_limit_max, spring_constant_translation, spring_constant_rotation):
        self.name = name
        self.joint_type = joint_type
        self.rigid_body_a = rigid_body_a
        self.rigid_body_b = rigid_body_b
        self.position = position
        self.rotation = rotation
        self.linear_limit_min = linear_limit_min
        self.linear_limit_max = linear_limit_max
        self.angular_limit_min = angular_limit_min
        self.angular_limit_max = angular_limit_max
        self.spring_constant_translation = spring_constant_translation
        self.spring_constant_rotation = spring_constant_rotation

def read_pmx_header(file: BufferedReader):
    magic = file.read(4)
    if magic != b'PMX ':
        raise ValueError("Invalid PMX file")
    
    version = struct.unpack('<f', file.read(4))[0]
    data_size = struct.unpack('<b', file.read(1))[0]
    encoding = struct.unpack('<b', file.read(1))[0]
    additional_uvs = struct.unpack('<b', file.read(1))[0]
    vertex_index_size = struct.unpack('<b', file.read(1))[0]
    texture_index_size = struct.unpack('<b', file.read(1))[0]
    material_index_size = struct.unpack('<b', file.read(1))[0]
    bone_index_size = struct.unpack('<b', file.read(1))[0]
    morph_index_size = struct.unpack('<b', file.read(1))[0]
    rigid_body_index_size = struct.unpack('<b', file.read(1))[0]

    model_name = str(file.read(struct.unpack('<i', file.read(4))[0]), 'utf-16-le', errors='replace')
    model_english_name = str(file.read(struct.unpack('<i', file.read(4))[0]), 'utf-16-le', errors='replace')
    model_comment = str(file.read(struct.unpack('<i', file.read(4))[0]), 'utf-16-le', errors='replace')
    model_english_comment = str(file.read(struct.unpack('<i', file.read(4))[0]), 'utf-16-le', errors='replace')

    return (version, encoding, additional_uvs, vertex_index_size, texture_index_size, 
            material_index_size, bone_index_size, morph_index_size, rigid_body_index_size,
            model_name, model_english_name, model_comment, model_english_comment)

def read_index_size(index, types):
    struct_format = "<??"
    byte_size = 0
    if index == 1:
        struct_format = replace_char(struct_format, 2, types[0])
        byte_size = 1
    elif index == 2:
        struct_format = replace_char(struct_format, 2, types[1])
        byte_size = 2
    else:
        struct_format = replace_char(struct_format, 2, types[2])
        byte_size = 4
    
    return struct_format, byte_size

def replace_char(string, index, character):
    temp = list(string)
    temp[index] = character
    return "".join(temp)

def read_morph(file: BufferedReader, vertex_struct, vertex_size):
    try:
        name_length = struct.unpack('<i', file.read(4))[0]
        name = str(file.read(name_length), 'utf-16-le', errors='replace')
        
        english_name_length = struct.unpack('<i', file.read(4))[0]
        english_name = str(file.read(english_name_length), 'utf-16-le', errors='replace')
        
        panel = int.from_bytes(file.read(1), byteorder='little', signed=True)
        morph_type = int.from_bytes(file.read(1), byteorder='little', signed=True)
        
        # Read offset count with error checking
        offset_count_bytes = file.read(4)
        if len(offset_count_bytes) != 4:
            return PMXMorph(name, english_name, panel, morph_type, [])
            
        offset_count = struct.unpack('<i', offset_count_bytes)[0]
        
        offsets = []
        if morph_type == 1:  # Vertex morph
            for _ in range(offset_count):
                vertex_index = struct.unpack(replace_char(vertex_struct, 1, '1'), file.read(vertex_size))[0]
                offset = struct.unpack('<3f', file.read(12))
                offsets.append((vertex_index, offset))
                
        return PMXMorph(name, english_name, panel, morph_type, offsets)
    except:
        return PMXMorph("", "", 0, 0, [])

def validate_pmx_data(header_data, vertices, faces, materials, bones):
    """Validate PMX data integrity"""
    if not vertices:
        raise ValueError("No vertices found in PMX file")
    if not faces:
        raise ValueError("No faces found in PMX file")
    if not materials:
        raise ValueError("No materials found in PMX file")
    if not bones:
        raise ValueError("No bones found in PMX file")
    return True

def handle_import_error(context, error_msg):
    """Handle import errors with user feedback"""
    context.window_manager.progress_end()
    bpy.ops.ui.popup_menu(message=error_msg)
    return {'CANCELLED'}

def read_vertex(file: BufferedReader, string_build, byte_size, additional_uvs):
    position = struct.unpack('<3f', file.read(12))
    normal = struct.unpack('<3f', file.read(12))
    uv = struct.unpack('<2f', file.read(8))
    uv = [uv[0], (1.0-uv[1])-1.0]
    
    additional_uv_read = []
    for _ in range(additional_uvs):
        additional_uv_read.append(struct.unpack('<4f', file.read(16)))
    
    weight_deform_type = struct.unpack('<B', file.read(1))[0]
    
    bone_indices = []
    bone_weights = []
    
    if weight_deform_type == 0:  # BDEF1
        string_build = replace_char(string_build, 1, '1')
        bone_indices = list(struct.unpack(string_build, file.read(byte_size*1)))
        bone_weights = [1.0]
    elif weight_deform_type == 1:  # BDEF2
        string_build = replace_char(string_build, 1, '2')
        bone_indices = list(struct.unpack(string_build, file.read(byte_size*2)))
        weight = struct.unpack('<f', file.read(4))[0]
        bone_weights = [weight, 1.0-weight]
    elif weight_deform_type == 2:  # BDEF4
        string_build = replace_char(string_build, 1, '4')
        bone_indices = list(struct.unpack(string_build, file.read(byte_size*4)))
        bone_weights = list(struct.unpack('<4f', file.read(16)))
    elif weight_deform_type == 3:  # SDEF
        string_build = replace_char(string_build, 1, '2')
        bone_indices = list(struct.unpack(string_build, file.read(byte_size*2)))
        weight = struct.unpack('<f', file.read(4))[0]
        bone_weights = [weight, 1.0-weight]
        # Skip SDEF data as we don't use it
        file.read(36)  # 3 vectors of 3 floats each (C, R0, R1)
    elif weight_deform_type == 4:  # QDEF
        string_build = replace_char(string_build, 1, '4')
        bone_indices = list(struct.unpack(string_build, file.read(byte_size*4)))
        bone_weights = list(struct.unpack('<4f', file.read(16)))
    
    edge_scale = struct.unpack('<f', file.read(4))[0]
    
    return PMXVertex(position, normal, uv, bone_indices, bone_weights, edge_scale, additional_uv_read)

def read_material(file: BufferedReader, string_build, byte_size):
    material_name = str(file.read(struct.unpack('<i', file.read(4))[0]), 'utf-16-le', errors='replace')
    material_english_name = str(file.read(struct.unpack('<i', file.read(4))[0]), 'utf-16-le', errors='replace')
    
    diffuse_color = struct.unpack('<4f', file.read(16))
    specular_color = struct.unpack('<3f', file.read(12))
    specular_strength = struct.unpack('<f', file.read(4))[0]
    ambient_color = struct.unpack('<3f', file.read(12))
    
    flag = struct.unpack('<b', file.read(1))[0]
    edge_color = struct.unpack('<4f', file.read(16))
    edge_size = struct.unpack('<f', file.read(4))[0]
    
    texture_index = struct.unpack(replace_char(string_build, 1, '1'), file.read(byte_size))[0]
    sphere_texture_index = struct.unpack(replace_char(string_build, 1, '1'), file.read(byte_size))[0]
    sphere_mode = struct.unpack('<b', file.read(1))[0]
    toon_sharing_flag = struct.unpack('<b', file.read(1))[0]
    
    if toon_sharing_flag == 0:
        toon_texture_index = struct.unpack(replace_char(string_build, 1, '1'), file.read(byte_size))[0]
    else:
        toon_texture_index = struct.unpack('<b', file.read(1))[0]
    
    comment = str(file.read(struct.unpack('<i', file.read(4))[0]), 'utf-16-le', errors='replace')
    surface_count = int(struct.unpack('<i', file.read(4))[0]/3)
    
    return PMXMaterial(material_name, material_english_name, diffuse_color, specular_color,
                      specular_strength, ambient_color, flag, edge_color, edge_size,
                      texture_index, sphere_texture_index, sphere_mode,
                      toon_sharing_flag, toon_texture_index, comment, surface_count)

def create_material_nodes(material: bpy.types.Material, texture_path: str, diffuse_color, specular_color, specular_strength, toon_texture_path=None):
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    
    nodes.clear()
    
    principled = nodes.new("ShaderNodeBsdfPrincipled")
    principled.location = (0, 0)
    principled.inputs["Base Color"].default_value = diffuse_color
    principled.inputs["Specular IOR Level"].default_value = specular_strength
    principled.inputs["Specular Tint"].default_value = (*specular_color, 1.0)
    
    # Handle transparency
    if diffuse_color[3] < 1.0:
        material.blend_method = 'HASHED'
        principled.inputs["Alpha"].default_value = diffuse_color[3]
    
    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (300, 0)
    
    # Main texture
    if texture_path and os.path.exists(texture_path):
        texture = nodes.new("ShaderNodeTexImage")
        texture.location = (-300, 0)
        texture.image = bpy.data.images.load(texture_path)
        links.new(texture.outputs["Color"], principled.inputs["Base Color"])
        links.new(texture.outputs["Alpha"], principled.inputs["Alpha"])
    
    # Toon texture
    if toon_texture_path and os.path.exists(toon_texture_path):
        toon = nodes.new("ShaderNodeTexImage")
        toon.location = (-300, -300)
        toon.image = bpy.data.images.load(toon_texture_path)
        mix = nodes.new("ShaderNodeMixRGB")
        mix.location = (-50, -150)
        mix.blend_type = 'MULTIPLY'
        links.new(toon.outputs["Color"], mix.inputs[2])
        links.new(mix.outputs["Color"], principled.inputs["Base Color"])
    
    links.new(principled.outputs["BSDF"], output.inputs["Surface"])

def read_bone(file: BufferedReader, string_build, byte_size):
    bone_name = str(file.read(struct.unpack('<i', file.read(4))[0]), 'utf-16-le', errors='replace')
    bone_english_name = str(file.read(struct.unpack('<i', file.read(4))[0]), 'utf-16-le', errors='replace')
    
    position = struct.unpack('<3f', file.read(12))
    parent_bone_index = struct.unpack(replace_char(string_build, 1, '1'), file.read(byte_size))[0]
    layer = struct.unpack('<i', file.read(4))[0]
    flag = struct.unpack('<H', file.read(2))[0]
    
    tail_position = [None, None, None]
    inherit_bone_parent_index = 0
    inherit_bone_parent_influence = 0.0
    fixed_axis = [0.0, 0.0, 0.0]
    local_x_vector = [0.0, 0.0, 0.0]
    local_z_vector = [0.0, 0.0, 0.0]
    external_key = 0
    ik_target_bone_index = 0
    ik_loop_count = -1
    ik_limit_radian = 0.0
    ik_links = []
    
    if not (flag & 0x0001):
        tail_position = struct.unpack('<3f', file.read(12))
    else:
        tail_index = struct.unpack(replace_char(string_build, 1, '1'), file.read(byte_size))[0]
    
    if flag & 0x0100 or flag & 0x0200:
        inherit_bone_parent_index = struct.unpack(replace_char(string_build, 1, '1'), file.read(byte_size))[0]
        inherit_bone_parent_influence = struct.unpack('<f', file.read(4))[0]
    
    if flag & 0x0400:
        fixed_axis = struct.unpack('<3f', file.read(12))
    
    if flag & 0x0800:
        local_x_vector = struct.unpack('<3f', file.read(12))
        local_z_vector = struct.unpack('<3f', file.read(12))
    
    if flag & 0x2000:
        external_key = struct.unpack('<i', file.read(4))[0]
    
    if flag & 0x0020:
        ik_target_bone_index = struct.unpack(replace_char(string_build, 1, '1'), file.read(byte_size))[0]
        ik_loop_count = struct.unpack('<i', file.read(4))[0]
        ik_limit_radian = struct.unpack('<f', file.read(4))[0]
        ik_link_count = struct.unpack('<i', file.read(4))[0]
        
        for _ in range(ik_link_count):
            ik_link_bone_index = struct.unpack(replace_char(string_build, 1, '1'), file.read(byte_size))[0]
            ik_link_limit = struct.unpack('<b', file.read(1))[0]
            if ik_link_limit == 1:
                angle_limit = (struct.unpack('<3f', file.read(12)), struct.unpack('<3f', file.read(12)))
                ik_links.append((ik_link_bone_index, True, angle_limit))
            else:
                ik_links.append((ik_link_bone_index, False, None))
    
    return PMXBone(bone_name, bone_english_name, position, parent_bone_index, layer,
                  flag, tail_position, inherit_bone_parent_index, inherit_bone_parent_influence,
                  fixed_axis, local_x_vector, local_z_vector, external_key,
                  ik_target_bone_index, ik_loop_count, ik_limit_radian, ik_links)

def create_bone_constraints(armature_obj: bpy.types.Object, bones: list[PMXBone]):
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode='POSE')
    
    # Clear existing constraints
    for pose_bone in armature_obj.pose.bones:
        while pose_bone.constraints:
            pose_bone.constraints.remove(pose_bone.constraints[0])

    # Handle rotation inheritance first
    for bone_data in bones:
        pose_bone = armature_obj.pose.bones.get(bone_data.name)
        if not pose_bone or bone_data.parent_index < 0:
            continue

        # Check if bone has vertex groups
        if not pose_bone.bone.use_deform:
            continue

        if bone_data.flag & 0x0100:  # Rotation inheritance
            if bone_data.inherit_parent_index >= 0:
                constraint = pose_bone.constraints.new('COPY_ROTATION')
                constraint.name = "MMD Rotation"
                constraint.target = armature_obj
                constraint.subtarget = bones[bone_data.inherit_parent_index].name
                constraint.influence = bone_data.inherit_influence
                constraint.target_space = 'LOCAL'
                constraint.owner_space = 'LOCAL'

    # Then handle IK constraints
    for bone_data in bones:
        pose_bone = armature_obj.pose.bones.get(bone_data.name)
        if not pose_bone:
            continue

        # Skip non-deforming bones
        if not pose_bone.bone.use_deform:
            continue

        if bone_data.flag & 0x0020:  # IK
            if bone_data.ik_target_index >= 0:
                constraint = pose_bone.constraints.new('IK')
                constraint.name = "MMD IK"
                constraint.target = armature_obj
                constraint.subtarget = bones[bone_data.ik_target_index].name
                constraint.chain_count = min(len(bone_data.ik_links), 3)
                constraint.iterations = min(bone_data.ik_loop_count, 8)
                constraint.use_tail = False
                constraint.use_stretch = False
                
                # Configure IK chain
                for link_bone_index, has_limits, angle_limits in bone_data.ik_links:
                    link_pose_bone = armature_obj.pose.bones.get(bones[link_bone_index].name)
                    if link_pose_bone and link_pose_bone.bone.use_deform:
                        link_pose_bone.rotation_mode = 'XYZ'
                        link_pose_bone.use_ik_limit_x = True
                        link_pose_bone.use_ik_limit_y = True
                        link_pose_bone.use_ik_limit_z = True
                        
                        if has_limits and angle_limits:
                            min_angles, max_angles = angle_limits
                            link_pose_bone.ik_min_x = max(-1.4, min_angles[0])
                            link_pose_bone.ik_max_x = min(1.4, max_angles[0])
                            link_pose_bone.ik_min_y = max(-1.4, min_angles[1])
                            link_pose_bone.ik_max_y = min(1.4, max_angles[1])
                            link_pose_bone.ik_min_z = max(-1.4, min_angles[2])
                            link_pose_bone.ik_max_z = min(1.4, max_angles[2])

    # Reset pose to default state
    bpy.ops.pose.select_all(action='SELECT')
    bpy.ops.pose.transforms_clear()
    bpy.ops.pose.select_all(action='DESELECT')
    
    bpy.ops.object.mode_set(mode='OBJECT')

def setup_physics(obj: bpy.types.Object, armature_obj: bpy.types.Object, rigid_bodies: list[PMXRigidBody], joints: list[PMXJoint]):
    """Set up physics for PMX model"""
    # Create rigid body collection if it doesn't exist
    if 'RigidBodies' not in bpy.data.collections:
        rigid_body_collection = bpy.data.collections.new('RigidBodies')
        bpy.context.scene.collection.children.link(rigid_body_collection)
    else:
        rigid_body_collection = bpy.data.collections['RigidBodies']

    # Create rigid bodies
    for rb in rigid_bodies:
        # Create mesh based on shape type
        if rb.shape_type == 0:  # Sphere
            bpy.ops.mesh.primitive_uv_sphere_add(radius=rb.size[0])
        elif rb.shape_type == 1:  # Box
            bpy.ops.mesh.primitive_cube_add()
            bpy.context.active_object.scale = rb.size
        elif rb.shape_type == 2:  # Capsule
            bpy.ops.mesh.primitive_cylinder_add(radius=rb.size[0], depth=rb.size[1])

        rb_obj = bpy.context.active_object
        rb_obj.name = f"RB_{rb.name}"
        rb_obj.location = rb.position
        rb_obj.rotation_euler = rb.rotation

        # Set up rigid body physics
        rb_obj.rigid_body.type = 'ACTIVE' if rb.mode == 0 else 'PASSIVE'
        rb_obj.rigid_body.mass = rb.mass
        rb_obj.rigid_body.linear_damping = rb.linear_damping
        rb_obj.rigid_body.angular_damping = rb.angular_damping
        rb_obj.rigid_body.restitution = rb.restitution
        rb_obj.rigid_body.friction = rb.friction

        # Parent to bone if specified
        if rb.bone_index >= 0:
            rb_obj.parent = armature_obj
            rb_obj.parent_type = 'BONE'
            rb_obj.parent_bone = bones[rb.bone_index].name

        # Move to rigid body collection
        rigid_body_collection.objects.link(rb_obj)
        bpy.context.scene.collection.objects.unlink(rb_obj)

    # Create joints
    for joint in joints:
        empty = bpy.data.objects.new(f"Joint_{joint.name}", None)
        empty.empty_display_type = 'ARROWS'
        empty.location = joint.position
        empty.rotation_euler = joint.rotation
        bpy.context.scene.collection.objects.link(empty)

        # Set up constraint
        constraint = empty.constraints.new('RIGID_BODY_JOINT')
        constraint.target = rigid_bodies[joint.rigid_body_a]
        constraint.child = rigid_bodies[joint.rigid_body_b]
        constraint.use_limit_lin_x = True
        constraint.use_limit_lin_y = True
        constraint.use_limit_lin_z = True
        constraint.use_limit_ang_x = True
        constraint.use_limit_ang_y = True
        constraint.use_limit_ang_z = True

        # Set limits
        constraint.limit_lin_x_lower = joint.linear_limit_min[0]
        constraint.limit_lin_x_upper = joint.linear_limit_max[0]
        constraint.limit_lin_y_lower = joint.linear_limit_min[1]
        constraint.limit_lin_y_upper = joint.linear_limit_max[1]
        constraint.limit_lin_z_lower = joint.linear_limit_min[2]
        constraint.limit_lin_z_upper = joint.linear_limit_max[2]
        constraint.limit_ang_x_lower = joint.angular_limit_min[0]
        constraint.limit_ang_x_upper = joint.angular_limit_max[0]
        constraint.limit_ang_y_lower = joint.angular_limit_min[1]
        constraint.limit_ang_y_upper = joint.angular_limit_max[1]
        constraint.limit_ang_z_lower = joint.angular_limit_min[2]
        constraint.limit_ang_z_upper = joint.angular_limit_max[2]

def create_armature(model_name: str, bones: list[PMXBone]) -> bpy.types.Object:
    armature = bpy.data.armatures.new(f"{model_name}_Armature")
    armature_obj = bpy.data.objects.new(f"{model_name}_Armature", armature)
    bpy.context.collection.objects.link(armature_obj)
    
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode='EDIT')
    
    # First pass: Create bones with proper names and types
    edit_bones = []
    for i, bone_data in enumerate(bones):
        bone_name = bone_data.name if bone_data.name else bone_data.english_name
        if not bone_name:
            bone_name = f"bone_{i}"
            
        edit_bone = armature.edit_bones.new(bone_name)
        edit_bone.head = Vector(bone_data.position)
        
        # Handle different bone types based on flags and names
        is_expression = bool(bone_data.flag & 0x0004)
        is_rotation_influenced = bool(bone_data.flag & 0x0100)
        is_ik = bool(bone_data.flag & 0x0020)
        is_twist = "twist" in bone_name.lower()
        
        if is_twist:
            # Twist bones need specific handling
            parent_pos = bones[bone_data.parent_index].position if bone_data.parent_index >= 0 else None
            if parent_pos:
                direction = Vector(bone_data.position) - Vector(parent_pos)
                if direction.length > 0.001:
                    edit_bone.tail = edit_bone.head + direction.normalized() * 0.1
                else:
                    edit_bone.tail = edit_bone.head + Vector((0, 0.05, 0))
            else:
                edit_bone.tail = edit_bone.head + Vector((0, 0.05, 0))
                
        elif is_expression:
            edit_bone.tail = edit_bone.head + Vector((0, 0.02, 0))
            edit_bone.use_deform = False
            
        elif is_ik:
            if bone_data.ik_links:
                target_pos = bones[bone_data.ik_links[0][0]].position
                direction = Vector(target_pos) - Vector(edit_bone.head)
                if direction.length > 0.001:
                    edit_bone.tail = edit_bone.head + direction.normalized() * 0.1
                else:
                    edit_bone.tail = edit_bone.head + Vector((0, 0.1, 0))
            else:
                edit_bone.tail = edit_bone.head + Vector((0, 0.1, 0))
                
        elif is_rotation_influenced:
            # Handle rotation influenced bones
            if bone_data.inherit_parent_index >= 0:
                target_pos = bones[bone_data.inherit_parent_index].position
                direction = Vector(target_pos) - Vector(edit_bone.head)
                if direction.length > 0.001:
                    edit_bone.tail = edit_bone.head + direction.normalized() * 0.08
                else:
                    edit_bone.tail = edit_bone.head + Vector((0, 0.08, 0))
            else:
                edit_bone.tail = edit_bone.head + Vector((0, 0.08, 0))
                
        else:
            # Standard bones
            if bone_data.tail_position[0] is not None:
                edit_bone.tail = Vector(bone_data.tail_position)
            else:
                child_positions = [bones[j].position for j in range(len(bones)) 
                                 if bones[j].parent_index == i]
                if child_positions:
                    avg_child_pos = Vector((0, 0, 0))
                    for pos in child_positions:
                        avg_child_pos += Vector(pos)
                    avg_child_pos /= len(child_positions)
                    edit_bone.tail = avg_child_pos
                else:
                    bone_length = 0.1 if bone_data.layer == 0 else 0.05
                    edit_bone.tail = edit_bone.head + Vector((0, bone_length, 0))
        
        edit_bones.append(edit_bone)

 
    # Second pass: Set up hierarchy and orientations
    for i, bone_data in enumerate(bones):
        edit_bone = edit_bones[i]
        
        # Parent bones
        if bone_data.parent_index >= 0:
            parent_bone = edit_bones[bone_data.parent_index]
            edit_bone.parent = parent_bone
            
            # Connect bones only if they should be connected
            if (Vector(bone_data.position) - Vector(parent_bone.tail)).length < 0.01:
                edit_bone.use_connect = True
        
        # Handle bone orientation
        if bone_data.fixed_axis != [0.0, 0.0, 0.0]:
            edit_bone.align_roll(Vector(bone_data.fixed_axis))
        elif bone_data.local_x != [0.0, 0.0, 0.0]:
            x_axis = Vector(bone_data.local_x).normalized()
            z_axis = Vector(bone_data.local_z).normalized()
            y_axis = z_axis.cross(x_axis)
            
            # Create and apply orientation matrix
            matrix = Matrix((x_axis, y_axis, z_axis)).to_3x3()
            edit_bone.matrix = matrix
    
    bpy.ops.object.mode_set(mode='OBJECT')
    return armature_obj



def assign_vertex_weights(obj: bpy.types.Object, vertices: list[PMXVertex], bones: list[PMXBone]):
    # Pre-create vertex groups
    vertex_groups = {}
    for bone in bones:
        vertex_groups[bone.name] = obj.vertex_groups.new(name=bone.name)
    
    # Batch assign weights
    for vertex_index, vertex in enumerate(vertices):
        for bone_idx, weight in zip(vertex.bone_indices, vertex.bone_weights):
            if bone_idx != -1 and weight > 0:
                vertex_groups[bones[bone_idx].name].add([vertex_index], weight, 'REPLACE')

def assign_materials(obj: bpy.types.Object, materials: list[PMXMaterial], textures: list[str], base_path: str):
    current_face_index = 0
    
    for material in materials:
        # Create or get material
        mat_name = material.name or f"Material_{len(obj.data.materials)}"
        if mat_name in bpy.data.materials:
            mat = bpy.data.materials[mat_name]
        else:
            mat = bpy.data.materials.new(name=mat_name)
        
        # Set up material nodes
        texture_path = None
        if material.texture_index >= 0 and material.texture_index < len(textures):
            texture_path = os.path.join(base_path, textures[material.texture_index])
        
        create_material_nodes(mat, texture_path, material.diffuse, material.specular, 
                            material.specular_strength)
        
        # Assign material to mesh
        if mat.name not in obj.data.materials:
            obj.data.materials.append(mat)
        
        # Assign faces to material
        mat_index = obj.data.materials.find(mat.name)
        for face in obj.data.polygons[current_face_index:current_face_index + material.surface_count]:
            face.material_index = mat_index
        
        current_face_index += material.surface_count

def import_pmx(filepath: str):
    wm = bpy.context.window_manager
    wm.progress_begin(0, 100)
    
    try:
        with open(filepath, 'rb') as file:
            # Read header (5%)
            wm.progress_update(5)
            header_data = read_pmx_header(file)
            version, encoding, additional_uvs, vertex_index_size, texture_index_size, \
            material_index_size, bone_index_size, morph_index_size, rigid_body_index_size, \
            model_name, model_english_name, model_comment, model_english_comment = header_data
            
            # Set up index size formats (10%)
            wm.progress_update(10)
            vertex_struct, vertex_size = read_index_size(vertex_index_size, 'BHi')
            bone_struct, bone_size = read_index_size(bone_index_size, 'bhi')
            texture_struct, texture_size = read_index_size(texture_index_size, 'bhi')
            
            # Read vertices (25%)
            vertex_count = struct.unpack('<i', file.read(4))[0]
            vertices = []
            for i in range(vertex_count):
                vertices.append(read_vertex(file, bone_struct, bone_size, additional_uvs))
                if i % 1000 == 0:
                    wm.progress_update(10 + (i/vertex_count * 15))
            
            # Read faces (35%)
            wm.progress_update(35)
            face_count = struct.unpack('<i', file.read(4))[0] // 3
            faces = []
            for _ in range(face_count):
                if vertex_index_size == 1:
                    faces.append(struct.unpack('<3B', file.read(3)))
                elif vertex_index_size == 2:
                    faces.append(struct.unpack('<3H', file.read(6)))
                else:
                    faces.append(struct.unpack('<3i', file.read(12)))
            
            # Read textures (45%)
            wm.progress_update(45)
            texture_count = struct.unpack('<i', file.read(4))[0]
            textures = []
            for _ in range(texture_count):
                texture_path = str(file.read(struct.unpack('<i', file.read(4))[0]), 'utf-16-le', errors='replace')
                textures.append(texture_path)
            
            # Read materials (55%)
            wm.progress_update(55)
            material_count = struct.unpack('<i', file.read(4))[0]
            materials = []
            for _ in range(material_count):
                materials.append(read_material(file, texture_struct, texture_size))
            
            # Read bones (65%)
            wm.progress_update(65)
            bone_count = struct.unpack('<i', file.read(4))[0]
            bones = []
            for _ in range(bone_count):
                bones.append(read_bone(file, bone_struct, bone_size))

            # Read morphs (75%)
            wm.progress_update(75)
            morph_count = struct.unpack('<i', file.read(4))[0]
            morphs = []
            for _ in range(morph_count):
                morphs.append(read_morph(file, vertex_struct, vertex_size))
            
            # Read rigid bodies (85%)
            wm.progress_update(85)
            try:
                rigid_body_count_bytes = file.read(4)
                if len(rigid_body_count_bytes) == 4:
                    rigid_body_count = struct.unpack('<i', rigid_body_count_bytes)[0]
                    rigid_bodies = []
                    for _ in range(rigid_body_count):
                        rigid_bodies.append(read_rigid_body(file, bone_struct, bone_size))
                else:
                    rigid_bodies = []
            except:
                rigid_bodies = []

            # Read joints (90%)
            wm.progress_update(90)
            try:
                joint_count_bytes = file.read(4)
                if len(joint_count_bytes) == 4:
                    joint_count = struct.unpack('<i', joint_count_bytes)[0]
                    joints = []
                    for _ in range(joint_count):
                        joints.append(read_joint(file, rigid_body_struct, rigid_body_size))
                else:
                    joints = []
            except:
                joints = []

            # Validate data (92%)
            wm.progress_update(92)
            validate_pmx_data(header_data, vertices, faces, materials, bones)

            # Create mesh and object (94%)
            wm.progress_update(94)
            mesh = bpy.data.meshes.new(model_name)
            mesh.from_pydata([v.position for v in vertices], [], faces)
            mesh.update()
            
            obj = bpy.data.objects.new(model_name, mesh)
            bpy.context.collection.objects.link(obj)
            
            # Create and set up armature (96%)
            wm.progress_update(96)
            armature_obj = create_armature(model_name, bones)
            obj.parent = armature_obj

            # Create shape keys (97%)
            wm.progress_update(97)
            for morph in morphs:
                if morph.morph_type == 1:
                    if not obj.data.shape_keys:
                        obj.shape_key_add(name='Basis')
                    shape_key = obj.shape_key_add(name=morph.name)
                    for vertex_index, offset in morph.offsets:
                        shape_key.data[vertex_index].co = (
                            vertices[vertex_index].position[0] + offset[0],
                            vertices[vertex_index].position[1] + offset[1],
                            vertices[vertex_index].position[2] + offset[2]
                        )
            
            # Set up physics (98%)
            wm.progress_update(98)
            setup_physics(obj, armature_obj, rigid_bodies, joints)
            
            # Final setup (99%)
            wm.progress_update(99)
            base_path = os.path.dirname(filepath)
            assign_materials(obj, materials, textures, base_path)
            assign_vertex_weights(obj, vertices, bones)
            
            # Add armature modifier
            mod = obj.modifiers.new(name="Armature", type='ARMATURE')
            mod.object = armature_obj
            
            # Set proper scale and orientation
            armature_obj.scale = (0.08, 0.08, 0.08)
            armature_obj.rotation_euler = (1.5708, 0, 0)

            # Select objects and set active
            armature_obj.select_set(True)
            obj.select_set(True)
            bpy.context.view_layer.objects.active = armature_obj

            # Disable automatic mirroring
            armature_obj.data.use_mirror_x = False

            # Add constraints
            create_bone_constraints(armature_obj, bones)

            # Apply transforms
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            
            # Ensure object mode
            bpy.context.view_layer.objects.active = armature_obj
            bpy.ops.object.mode_set(mode='OBJECT')

            wm.progress_end()
            return {'FINISHED'}
            
    except Exception as e:
        wm.progress_end()
        error_msg = f"PMX Import Error: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)  # Console output for debugging
        return {'CANCELLED'}
