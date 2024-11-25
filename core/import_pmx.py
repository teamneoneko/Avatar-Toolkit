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

def create_material_nodes(material: bpy.types.Material, texture_path: str, diffuse_color, specular_color, specular_strength):
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    
    nodes.clear()
    
    principled = nodes.new("ShaderNodeBsdfPrincipled")
    principled.location = (0, 0)
    principled.inputs["Base Color"].default_value = diffuse_color
    principled.inputs["Specular IOR Level"].default_value = specular_strength
    principled.inputs["Specular Tint"].default_value = (*specular_color, 1.0)
    
    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (300, 0)
    
    if texture_path:
        texture = nodes.new("ShaderNodeTexImage")
        texture.location = (-300, 0)
        
        if os.path.exists(texture_path):
            if texture_path in bpy.data.images:
                texture.image = bpy.data.images[texture_path]
            else:
                texture.image = bpy.data.images.load(texture_path)
            
            links.new(texture.outputs["Color"], principled.inputs["Base Color"])
            links.new(texture.outputs["Alpha"], principled.inputs["Alpha"])
    
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

def create_armature(model_name: str, bones: list[PMXBone]) -> bpy.types.Object:
    armature = bpy.data.armatures.new(f"{model_name}_Armature")
    armature_obj = bpy.data.objects.new(f"{model_name}_Armature", armature)
    bpy.context.collection.objects.link(armature_obj)
    
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode='EDIT')
    
    # First pass: Create bones with correct positions and sizes
    edit_bones = []  # Using a list instead of dict for indexed access
    for i, bone_data in enumerate(bones):
        bone_name = f"bone_{i}"
        edit_bone = armature.edit_bones.new(bone_name)
        edit_bone.head = Vector(bone_data.position)
        
        # Calculate proper tail position with enhanced logic
        if bone_data.tail_position[0] is not None:
            edit_bone.tail = Vector(bone_data.tail_position)
        else:
            # Check for special bone types using flags
            if bone_data.flag & 0x0020:  # IK bone
                bone_length = 0.1
            elif bone_data.flag & 0x0100:  # Rotation influenced
                bone_length = 0.08
            elif bone_data.flag & 0x0200:  # Movement influenced
                bone_length = 0.08
            else:
                # Find child bones
                child_positions = [bones[j].position for j in range(len(bones)) 
                                 if bones[j].parent_index == i]
                if child_positions:
                    # Use closest child position
                    closest_child = min(child_positions, 
                                     key=lambda p: (Vector(p) - Vector(bone_data.position)).length)
                    edit_bone.tail = Vector(closest_child)
                    continue
                else:
                    # Default length based on bone layer
                    bone_length = 0.1 if bone_data.layer == 0 else 0.05
            
            # Apply calculated length
            direction = Vector((0, bone_length, 0))
            if bone_data.parent_index >= 0:
                parent_pos = Vector(bones[bone_data.parent_index].position)
                if (Vector(bone_data.position) - parent_pos).length > 0.001:
                    direction = (Vector(bone_data.position) - parent_pos).normalized() * bone_length
            edit_bone.tail = edit_bone.head + direction
        
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
    try:
        with open(filepath, 'rb') as file:
            # Read header
            header_data = read_pmx_header(file)
            version, encoding, additional_uvs, vertex_index_size, texture_index_size, \
            material_index_size, bone_index_size, morph_index_size, rigid_body_index_size, \
            model_name, model_english_name, model_comment, model_english_comment = header_data
            
            # Set up index size formats
            vertex_struct, vertex_size = read_index_size(vertex_index_size, 'BHi')
            bone_struct, bone_size = read_index_size(bone_index_size, 'bhi')
            texture_struct, texture_size = read_index_size(texture_index_size, 'bhi')
            
            # Read vertices
            vertex_count = struct.unpack('<i', file.read(4))[0]
            vertices = []
            for _ in range(vertex_count):
                vertices.append(read_vertex(file, bone_struct, bone_size, additional_uvs))
            
            # Read faces
            face_count = struct.unpack('<i', file.read(4))[0] // 3
            faces = []
            for _ in range(face_count):
                if vertex_index_size == 1:
                    faces.append(struct.unpack('<3B', file.read(3)))
                elif vertex_index_size == 2:
                    faces.append(struct.unpack('<3H', file.read(6)))
                else:
                    faces.append(struct.unpack('<3i', file.read(12)))
            
            # Read textures
            texture_count = struct.unpack('<i', file.read(4))[0]
            textures = []
            for _ in range(texture_count):
                texture_path = str(file.read(struct.unpack('<i', file.read(4))[0]), 'utf-16-le', errors='replace')
                textures.append(texture_path)
            
            # Read materials
            material_count = struct.unpack('<i', file.read(4))[0]
            materials = []
            for _ in range(material_count):
                materials.append(read_material(file, texture_struct, texture_size))
            
            # Read bones
            bone_count = struct.unpack('<i', file.read(4))[0]
            bones = []
            for _ in range(bone_count):
                bones.append(read_bone(file, bone_struct, bone_size))
            
            # Create mesh and object
            mesh = bpy.data.meshes.new(model_name)
            mesh.from_pydata([v.position for v in vertices], [], faces)
            mesh.update()
            
            obj = bpy.data.objects.new(model_name, mesh)
            bpy.context.collection.objects.link(obj)
            
            # Create and set up armature
            armature_obj = create_armature(model_name, bones)
            obj.parent = armature_obj
            
            # Add armature modifier
            mod = obj.modifiers.new(name="Armature", type='ARMATURE')
            mod.object = armature_obj
            
            # Assign materials and weights
            base_path = os.path.dirname(filepath)
            assign_materials(obj, materials, textures, base_path)
            assign_vertex_weights(obj, vertices, bones)
            
            # Set proper scale and orientation
            armature_obj.scale = (0.08, 0.08, 0.08)
            armature_obj.rotation_euler = (1.5708, 0, 0)

            # Select both armature and mesh
            armature_obj.select_set(True)
            obj.select_set(True)
            bpy.context.view_layer.objects.active = armature_obj

            # Apply transforms
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            
            return {'FINISHED'}
            
    except Exception as e:
        print(f"Error importing PMX: {str(e)}")
        traceback.print_exc()
        return {'CANCELLED'}
