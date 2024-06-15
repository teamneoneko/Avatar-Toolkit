import bpy
import struct
import traceback

def read_pmx_header(file):
    # Read PMX header information
    magic = file.read(4)
    if magic != b'PMX ':
        raise ValueError("Invalid PMX file")
    
    version = struct.unpack('<f', file.read(4))[0]
    
    # Read additional header fields
    data_size = struct.unpack('<b', file.read(1))[0]
    encoding = struct.unpack('<b', file.read(1))[0]
    additional_uvs = struct.unpack('<b', file.read(1))[0]
    vertex_index_size = struct.unpack('<b', file.read(1))[0]
    texture_index_size = struct.unpack('<b', file.read(1))[0]
    material_index_size = struct.unpack('<b', file.read(1))[0]
    bone_index_size = struct.unpack('<b', file.read(1))[0]
    morph_index_size = struct.unpack('<b', file.read(1))[0]
    rigid_body_index_size = struct.unpack('<b', file.read(1))[0]
    print(rigid_body_index_size)
    # Read model name and comments
    model_name = str(file.read(struct.unpack('<i', file.read(4))[0]), 'utf-16-le', errors='replace')
    model_english_name = str(file.read(struct.unpack('<i', file.read(4))[0]), 'utf-16-le', errors='replace')
    
    model_comment = str(file.read(struct.unpack('<i', file.read(4))[0]), 'utf-16-le', errors='replace')
    #print(model_name)
    #print(model_english_name)
    model_english_comment = str(file.read(struct.unpack('<i', file.read(4))[0]), 'utf-16-le', errors='replace')
    #print(model_english_comment)
    return version, encoding, additional_uvs, vertex_index_size, texture_index_size, material_index_size, bone_index_size, morph_index_size, rigid_body_index_size, model_name, model_english_name, model_comment, model_english_comment

def read_vertex(file, vertex_index_size):
    position = struct.unpack('<3f', file.read(12))
    normal = struct.unpack('<3f', file.read(12))
    uv = struct.unpack('<2f', file.read(8))
    
    if vertex_index_size == 1:
        bone_indices = list(struct.unpack('<4B', file.read(4)))
    elif vertex_index_size == 2:
        bone_indices = list(struct.unpack('<4H', file.read(8)))
    else:
        bone_indices = list(struct.unpack('<4I', file.read(16)))
    
    bone_weights = list(struct.unpack('<4f', file.read(16)))
    edge_scale = struct.unpack('<f', file.read(4))[0]
    
    return position, normal, uv, bone_indices, bone_weights, edge_scale

def read_material(file, texture_index_size):
    material_name = str(file.read(struct.unpack('<i', file.read(4))[0]), 'utf-16-le', errors='replace')
    material_english_name = str(file.read(struct.unpack('<i', file.read(4))[0]), 'utf-16-le', errors='replace')
    
    diffuse_color = struct.unpack('<4f', file.read(16))
    specular_color = struct.unpack('<3f', file.read(12))
    specular_strength = struct.unpack('<f', file.read(4))[0]
    ambient_color = struct.unpack('<3f', file.read(12))
    
    flag = struct.unpack('<b', file.read(1))[0]
    edge_color = struct.unpack('<4f', file.read(16))
    edge_size = struct.unpack('<f', file.read(4))[0]
    texture_index = struct.unpack(f'<{texture_index_size}B', file.read(texture_index_size))[0]
    sphere_texture_index = struct.unpack(f'<{texture_index_size}B', file.read(texture_index_size))[0]
    sphere_mode = struct.unpack('<b', file.read(1))[0]
    toon_sharing_flag = struct.unpack('<b', file.read(1))[0]
    
    if toon_sharing_flag == 0:
        toon_texture_index = struct.unpack(f'<{texture_index_size}B', file.read(texture_index_size))[0]
    else:
        toon_texture_index = struct.unpack('<b', file.read(1))[0]
    
    
    comment = str(file.read(struct.unpack('<i', file.read(4))[0]), 'utf-16-le', errors='replace')
    
    return material_name, material_english_name, diffuse_color, specular_color, specular_strength, ambient_color, flag, edge_color, edge_size, texture_index, sphere_texture_index, sphere_mode, toon_sharing_flag, toon_texture_index, comment

def read_bone(file, bone_index_size):
    bone_name = str(file.read(struct.unpack('<i', file.read(4))[0]), 'utf-16-le', errors='replace')
    bone_english_name = str(file.read(struct.unpack('<i', file.read(4))[0]), 'utf-16-le', errors='replace')
    
    position = struct.unpack('<3f', file.read(12))
    parent_bone_index = struct.unpack(f'<{bone_index_size}B', file.read(bone_index_size))[0]
    layer = struct.unpack('<i', file.read(4))[0]
    flag = struct.unpack('<H', file.read(2))[0]
    
    if flag & 0x0001:
        tail_position = struct.unpack('<3f', file.read(12))
    else:
        tail_index = struct.unpack(f'<{bone_index_size}B', file.read(bone_index_size))[0]
    
    if flag & 0x0100 or flag & 0x0200:
        inherit_bone_parent_index = struct.unpack(f'<{bone_index_size}B', file.read(bone_index_size))[0]
        inherit_bone_parent_influence = struct.unpack('<f', file.read(4))[0]
    
    if flag & 0x0400:
        fixed_axis = struct.unpack('<3f', file.read(12))
    
    if flag & 0x0800:
        local_x_vector = struct.unpack('<3f', file.read(12))
        local_z_vector = struct.unpack('<3f', file.read(12))
    
    if flag & 0x2000:
        external_key = struct.unpack('<i', file.read(4))[0]
    
    if flag & 0x0020:
        ik_target_bone_index = struct.unpack(f'<{bone_index_size}B', file.read(bone_index_size))[0]
        ik_loop_count = struct.unpack('<i', file.read(4))[0]
        ik_limit_radian = struct.unpack('<f', file.read(4))[0]
        ik_link_count = struct.unpack('<i', file.read(4))[0]
        
        ik_links = []
        for _ in range(ik_link_count):
            ik_link_bone_index = struct.unpack(f'<{bone_index_size}B', file.read(bone_index_size))[0]
            ik_link_limit_min = struct.unpack('<3f', file.read(12))
            ik_link_limit_max = struct.unpack('<3f', file.read(12))
            ik_links.append((ik_link_bone_index, ik_link_limit_min, ik_link_limit_max))
    
    return bone_name, bone_english_name, position, parent_bone_index, layer, flag, tail_position, inherit_bone_parent_index, inherit_bone_parent_influence, fixed_axis, local_x_vector, local_z_vector, external_key, ik_target_bone_index, ik_loop_count, ik_limit_radian, ik_links

def read_morph(file, morph_index_size):
    morph_name = str(file.read(struct.unpack('<i', file.read(4))[0]), 'utf-16-le', errors='replace')
    morph_english_name = str(file.read(struct.unpack('<i', file.read(4))[0]), 'utf-16-le', errors='replace')
    
    panel = struct.unpack('<b', file.read(1))[0]
    morph_type = struct.unpack('<b', file.read(1))[0]
    offset_size = struct.unpack('<i', file.read(4))[0]
    
    morph_data = []
    for _ in range(offset_size):
        if morph_type == 0:  # Group
            morph_index = struct.unpack(f'<{morph_index_size}B', file.read(morph_index_size))[0]
            morph_value = struct.unpack('<f', file.read(4))[0]
            morph_data.append((morph_index, morph_value))
        elif morph_type == 1:  # Vertex
            vertex_index = struct.unpack('<i', file.read(4))[0]
            position_offset = struct.unpack('<3f', file.read(12))
            morph_data.append((vertex_index, position_offset))
        elif morph_type == 2:  # Bone
            bone_index = struct.unpack(f'<{morph_index_size}B', file.read(morph_index_size))[0]
            position_offset = struct.unpack('<3f', file.read(12))
            rotation_offset = struct.unpack('<4f', file.read(16))
            morph_data.append((bone_index, position_offset, rotation_offset))
        elif morph_type == 3:  # UV
            vertex_index = struct.unpack('<i', file.read(4))[0]
            uv_offset = struct.unpack('<4f', file.read(16))
            morph_data.append((vertex_index, uv_offset))
        elif morph_type == 4:  # UV extended1
            vertex_index = struct.unpack('<i', file.read(4))[0]
            uv_offset = struct.unpack('<4f', file.read(16))
            morph_data.append((vertex_index, uv_offset))
        elif morph_type == 5:  # UV extended2
            vertex_index = struct.unpack('<i', file.read(4))[0]
            uv_offset = struct.unpack('<4f', file.read(16))
            morph_data.append((vertex_index, uv_offset))
        elif morph_type == 6:  # UV extended3
            vertex_index = struct.unpack('<i', file.read(4))[0]
            uv_offset = struct.unpack('<4f', file.read(16))
            morph_data.append((vertex_index, uv_offset))
        elif morph_type == 7:  # UV extended4
            vertex_index = struct.unpack('<i', file.read(4))[0]
            uv_offset = struct.unpack('<4f', file.read(16))
            morph_data.append((vertex_index, uv_offset))
        elif morph_type == 8:  # Material
            material_index = struct.unpack('<i', file.read(4))[0]
            offset_type = struct.unpack('<b', file.read(1))[0]
            diffuse_offset = struct.unpack('<4f', file.read(16))
            specular_offset = struct.unpack('<3f', file.read(12))
            specular_factor_offset = struct.unpack('<f', file.read(4))[0]
            ambient_offset = struct.unpack('<3f', file.read(12))
            edge_color_offset = struct.unpack('<4f', file.read(16))
            edge_size_offset = struct.unpack('<f', file.read(4))[0]
            texture_factor_offset = struct.unpack('<4f', file.read(16))
            sphere_texture_factor_offset = struct.unpack('<4f', file.read(16))
            toon_texture_factor_offset = struct.unpack('<4f', file.read(16))
            morph_data.append((material_index, offset_type, diffuse_offset, specular_offset, specular_factor_offset, ambient_offset, edge_color_offset, edge_size_offset, texture_factor_offset, sphere_texture_factor_offset, toon_texture_factor_offset))
    
    return morph_name, morph_english_name, panel, morph_type, morph_data

def import_pmx(filepath):
    try:
        with open(filepath, mode='rb') as file:
            
            print("stage 1")
            version, encoding, additional_uvs, vertex_index_size, texture_index_size, material_index_size, bone_index_size, morph_index_size, rigid_body_index_size, model_name, model_english_name, model_comment, model_english_comment = read_pmx_header(file)
            print("stage 2")
            # Read vertices
            print("fix 3")
            vertex_count = struct.unpack('<i', file.read(4))[0]
            print("stage 3")
            print(vertex_count)
            vertices = []
            for _ in range(vertex_count):
                position, normal, uv, bone_indices, bone_weights, edge_scale = read_vertex(file, vertex_index_size)
                vertices.append((position, normal, uv, bone_indices, bone_weights, edge_scale))
            
            # Read faces
            print("stage 4")
            face_count = struct.unpack('<i', file.read(4))[0]
            print("stage 5")
            print(face_count)
            print(additional_uvs)
            print(vertex_index_size)
            faces = []
            for _ in range(face_count // 3):
                face_indices = struct.unpack('<3i', file.read(12))
                faces.append(face_indices)
            print("stage 6")
            # Read textures
            texture_count = struct.unpack('<i', file.read(4))[0]
            textures = []
            for _ in range(texture_count):
                texture_path = str(file.read(struct.unpack('<i', file.read(4))[0]), 'utf-16-le', errors='replace')
                textures.append(texture_path)
            print("stage 7")
            # Read materials
            material_count = struct.unpack('<i', file.read(4))[0]
            materials = []
            for _ in range(material_count):
                material_name, material_english_name, diffuse_color, specular_color, specular_strength, ambient_color, flag, edge_color, edge_size, texture_index, sphere_texture_index, sphere_mode, toon_sharing_flag, toon_texture_index, comment = read_material(file, texture_index_size)
                materials.append((material_name, material_english_name, diffuse_color, specular_color, specular_strength, ambient_color, flag, edge_color, edge_size, texture_index, sphere_texture_index, sphere_mode, toon_sharing_flag, toon_texture_index, comment))
            print("stage 8")
        # Read bones
        bone_count = struct.unpack('<i', file.read(4))[0]
        bones = []
        for _ in range(bone_count):
            bone_name, bone_english_name, position, parent_bone_index, layer, flag, tail_position, inherit_bone_parent_index, inherit_bone_parent_influence, fixed_axis, local_x_vector, local_z_vector, external_key, ik_target_bone_index, ik_loop_count, ik_limit_radian, ik_links = read_bone(file, bone_index_size)
            bones.append((bone_name, bone_english_name, position, parent_bone_index, layer, flag, tail_position, inherit_bone_parent_index, inherit_bone_parent_influence, fixed_axis, local_x_vector, local_z_vector, external_key, ik_target_bone_index, ik_loop_count, ik_limit_radian, ik_links))
        
        # Read morphs
        morph_count = struct.unpack('<i', file.read(4))[0]
        morphs = []
        for _ in range(morph_count):
            morph_name, morph_english_name, panel, morph_type, morph_data = read_morph(file, morph_index_size)
            morphs.append((morph_name, morph_english_name, panel, morph_type, morph_data))
        
        # Create Blender objects and assign PMX data
        mesh = bpy.data.meshes.new(model_name)
        mesh.from_pydata([v[0] for v in vertices], [], faces)
        mesh.update()
        
        obj = bpy.data.objects.new(model_name, mesh)
        bpy.context.collection.objects.link(obj)
        
        # Assign vertex normals
        for i, vertex in enumerate(vertices):
            mesh.vertices[i].normal = vertex[1]
        
        # Assign UV coordinates
        uv_layer = mesh.uv_layers.new()
        for i, vertex in enumerate(vertices):
            uv_layer.data[i].uv = vertex[2]
        
        # Assign materials
        for material_data in materials:
            material = bpy.data.materials.new(material_data[0])
            material.diffuse_color = material_data[2]
            material.specular_color = material_data[3]
            material.specular_intensity = material_data[4]
            material.ambient = material_data[5]
            # Set other material properties based on the PMX data
            
            mesh.materials.append(material)
        
        # Create armature and assign bones
        armature = bpy.data.armatures.new(model_name + "_Armature")
        armature_obj = bpy.data.objects.new(model_name + "_Armature", armature)
        bpy.context.collection.objects.link(armature_obj)
        
        bpy.context.view_layer.objects.active = armature_obj
        bpy.ops.object.mode_set(mode='EDIT')
        
        for bone_data in bones:
            bone = armature.edit_bones.new(bone_data[0])
            bone.head = bone_data[2]
            bone.tail = bone_data[6]
            
            if bone_data[3] != -1:
                parent_bone = armature.edit_bones[bone_data[3]]
                bone.parent = parent_bone
            
            # Set other bone properties based on the PMX data
        
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Assign bone weights to the mesh
        for i, vertex in enumerate(vertices):
            for j in range(4):
                if vertex[3][j] != -1:
                    bone_name = bones[vertex[3][j]][0]
                    weight = vertex[4][j]
                    
                    vertex_group = obj.vertex_groups.get(bone_name)
                    if not vertex_group:
                        vertex_group = obj.vertex_groups.new(name=bone_name)
                    
                    vertex_group.add([i], weight, 'REPLACE')
        
        # Assign morphs to the mesh
        for morph_data in morphs:
            morph_name = morph_data[0]
            morph_type = morph_data[3]
            
            if morph_type == 1:  # Vertex morph
                shape_key = obj.shape_key_add(name=morph_name)
                for offset_data in morph_data[4]:
                    vertex_index = offset_data[0]
                    offset = offset_data[1]
                    shape_key.data[vertex_index].co += mathutils.Vector(offset)
            # Handle other morph types based on the PMX specification
        
            print(f"Successfully imported PMX file: {filepath}")
            print(f"Model Name: {model_name}")
            print(f"Model English Name: {model_english_name}")
            print(f"Model Comment: {model_comment}")
            print(f"Model English Comment: {model_english_comment}")
    except Exception as e:
        print(f"Error importing PMX file: {filepath}")
        print(f"Error details hhh: {traceback.format_exc()}")