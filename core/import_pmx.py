import bpy
import struct
import traceback
import mathutils

from mathutils import Matrix, Vector

def replace_char(string, index, character):
    temp = list(string)
    temp[index] = character
    return "".join(temp)

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
    print(model_name)
    print(model_english_name)
    print(model_comment)
    model_english_comment = str(file.read(struct.unpack('<i', file.read(4))[0]), 'utf-16-le', errors='replace')
    print(model_english_comment)
    return version, encoding, additional_uvs, vertex_index_size, texture_index_size, material_index_size, bone_index_size, morph_index_size, rigid_body_index_size, model_name, model_english_name, model_comment, model_english_comment

def read_vertex(file, string_build, byte_size, additional_uvs):
    position = struct.unpack('<3f', file.read(12))
    normal = struct.unpack('<3f', file.read(12))
    uv = struct.unpack('<2f', file.read(8))
    additional_uv_read = []
    for i in range(0,additional_uvs):
        additional_uv_read.append(struct.unpack('<4f', file.read(16)))
    
    weight_deform_type = struct.unpack('<B', file.read(1))[0]
    
    C_num = []
    R0_num = []
    R1_num = []
    
    #in the if-else chain, multiplying byte_size by a number should reflect the string_build's 1st (not 0th) character which is how many bone indices there are.
    if weight_deform_type == 0: #BDEF 1
        string_build = replace_char(string_build,1,'1') #how many bone indices there are
        bone_indices = list(struct.unpack(string_build, file.read(byte_size*1))) 
        bone_weights = [1.0]
    elif weight_deform_type == 1: #BDEF2
        string_build = replace_char(string_build,1,'2') #how many bone indices there are
        bone_indices = list(struct.unpack(string_build, file.read(byte_size*2)))
        bone_1_weight = struct.unpack('<f', file.read(4))[0]
        bone_weights = [bone_1_weight, 1.0-bone_1_weight]
    elif weight_deform_type == 2: #BDEF4
        string_build = replace_char(string_build,1,'4') #how many bone indices there are
        bone_indices = list(struct.unpack(string_build, file.read(byte_size*4))) 
        bone_weights = list(struct.unpack('<4f', file.read(4*4))) 
    elif weight_deform_type == 3: #SDEF
        string_build = replace_char(string_build,1,'2') #how many bone indices there are
        bone_indices = list(struct.unpack(string_build, file.read(byte_size*2)))
        bone_1_weight = struct.unpack('<f', file.read(4))[0]
        bone_weights = [bone_1_weight, 1.0-bone_1_weight]
        C_num = struct.unpack('<3f', file.read(12))
        R0_num = struct.unpack('<3f', file.read(12))
        R1_num = struct.unpack('<3f', file.read(12))
    elif weight_deform_type == 4: #QDEF
        string_build = replace_char(string_build,1,'4') #how many bone indices there are
        bone_indices = list(struct.unpack(string_build, file.read(byte_size*4))) 
        bone_weights = list(struct.unpack('<4f', file.read(4*4))) 
    else:
        raise IOError("Unsupported weight deform type \""+str(weight_deform_type)+"\" for file!")
    
    
    
    edge_scale = struct.unpack('<f', file.read(4))[0]
    return position, normal, uv, bone_indices, bone_weights, edge_scale, additional_uv_read

def read_material(file, string_build, byte_size):
    material_name = str(file.read(struct.unpack('<i', file.read(4))[0]), 'utf-16-le', errors='replace')
    material_english_name = str(file.read(struct.unpack('<i', file.read(4))[0]), 'utf-16-le', errors='replace')
    
    diffuse_color = struct.unpack('<4f', file.read(16))
    specular_color = struct.unpack('<3f', file.read(12))
    specular_strength = struct.unpack('<f', file.read(4))[0]
    ambient_color = struct.unpack('<3f', file.read(12))
    
    flag = struct.unpack('<b', file.read(1))[0]
    edge_color = struct.unpack('<4f', file.read(16))
    edge_size = struct.unpack('<f', file.read(4))[0]
    #this is bad don't do this, replaced it.. - @989onan
    #texture_index = struct.unpack(f'<{texture_index_size}B', file.read(texture_index_size))[0]
    texture_index = struct.unpack(replace_char(string_build, 1, '1'), file.read(byte_size))[0]
    sphere_texture_index = struct.unpack(replace_char(string_build, 1, '1'), file.read(byte_size))[0]
    sphere_mode = struct.unpack('<b', file.read(1))[0]
    toon_sharing_flag = struct.unpack('<b', file.read(1))[0]
    
    if toon_sharing_flag == 0:
        toon_texture_index = struct.unpack(replace_char(string_build, 1, '1'), file.read(byte_size))[0]
    else:
        toon_texture_index = struct.unpack('<b', file.read(1))[0]
    
    
    comment = str(file.read(struct.unpack('<i', file.read(4))[0]), 'utf-16-le', errors='replace')
    surface_count = struct.unpack('<i', file.read(4))[0]/3
    
    return material_name, material_english_name, diffuse_color, specular_color, specular_strength, ambient_color, flag, edge_color, edge_size, texture_index, sphere_texture_index, sphere_mode, toon_sharing_flag, toon_texture_index, comment, surface_count

def read_bone(file, string_build, byte_size):
    bone_name = str(file.read(struct.unpack('<i', file.read(4))[0]), 'utf-16-le', errors='replace')
    bone_english_name = str(file.read(struct.unpack('<i', file.read(4))[0]), 'utf-16-le', errors='replace')
    
    
    position = struct.unpack('<3f', file.read(12))
    parent_bone_index = struct.unpack(replace_char(string_build, 1, '1'), file.read(byte_size))[0]
    layer = struct.unpack('<i', file.read(4))[0]
    flag = struct.unpack('<H', file.read(2))[0]
    
    tail_position = [None,None,None]
    tail_index = 0.0
    inherit_bone_parent_index = 0
    inherit_bone_parent_influence = 0.0
    fixed_axis = [0.0,0.0,0.0]
    local_x_vector = [0.0,0.0,0.0]
    local_z_vector = [0.0,0.0,0.0]
    external_key = 0
    ik_target_bone_index = 0.0
    ik_loop_count = -1
    ik_limit_radian = 0.0
    ik_link_count = -1
    
    
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
    
    ik_links = []
    if flag & 0x0020:
        ik_target_bone_index = struct.unpack(replace_char(string_build, 1, '1'), file.read(byte_size))[0]
        ik_loop_count = struct.unpack('<i', file.read(4))[0]
        ik_limit_radian = struct.unpack('<f', file.read(4))[0]
        ik_link_count = struct.unpack('<i', file.read(4))[0]
        
        
        for _ in range(ik_link_count):
            ik_link_bone_index = struct.unpack(replace_char(string_build, 1, '1'), file.read(byte_size))[0]
            ik_link_limit_min = struct.unpack('<3f', file.read(12))
            ik_link_limit_max = struct.unpack('<3f', file.read(12))
            ik_links.append((ik_link_bone_index, ik_link_limit_min, ik_link_limit_max))
    
    return bone_name, bone_english_name, position, parent_bone_index, layer, flag, tail_position, inherit_bone_parent_index, inherit_bone_parent_influence, fixed_axis, local_x_vector, local_z_vector, external_key, ik_target_bone_index, ik_loop_count, ik_limit_radian, ik_links

def read_morph(file, morph_struct, morph_bytesize, vertex_struct, vertex_size, bone_struct, bone_size, material_struct, material_size, rigid_struct, rigid_size):
    morph_name = str(file.read(struct.unpack('<i', file.read(4))[0]), 'utf-16-le', errors='replace')
    morph_english_name = str(file.read(struct.unpack('<i', file.read(4))[0]), 'utf-16-le', errors='replace')
    
    panel = struct.unpack('<b', file.read(1))[0]
    morph_type = struct.unpack('<b', file.read(1))[0]
    offset_size = struct.unpack('<i', file.read(4))[0]
    
    
    
    
    morph_data = []
    for _ in range(offset_size):
        if morph_type == 0:  # Group
            morph_index = struct.unpack(replace_char(morph_struct, 1, '1'), file.read(morph_bytesize))[0]
            morph_value = struct.unpack('<f', file.read(4))[0]
            morph_data.append((morph_index, morph_value))
        elif morph_type == 1:  # Vertex
            vertex_index = struct.unpack(replace_char(vertex_struct, 1, '1'), file.read(vertex_size))[0]
            position_offset = struct.unpack('<3f', file.read(12))
            morph_data.append((vertex_index, position_offset))
        elif morph_type == 2:  # Bone
            bone_index = struct.unpack(bone_struct, file.read(bone_size))[0]
            position_offset = struct.unpack('<3f', file.read(12))
            rotation_offset = struct.unpack('<4f', file.read(16))
            morph_data.append((bone_index, position_offset, rotation_offset))
        elif morph_type == 3:  # UV
            vertex_index = struct.unpack(replace_char(vertex_struct, 1, '1'), file.read(vertex_size))[0]
            uv_offset = struct.unpack('<4f', file.read(16))
            morph_data.append((vertex_index, uv_offset))
        elif morph_type == 4:  # UV extended1
            vertex_index = struct.unpack(replace_char(vertex_struct, 1, '1'), file.read(vertex_size))[0]
            uv_offset = struct.unpack('<4f', file.read(16))
            morph_data.append((vertex_index, uv_offset))
        elif morph_type == 5:  # UV extended2
            vertex_index = struct.unpack(replace_char(vertex_struct, 1, '1'), file.read(vertex_size))[0]
            uv_offset = struct.unpack('<4f', file.read(16))
            morph_data.append((vertex_index, uv_offset))
        elif morph_type == 6:  # UV extended3
            vertex_index = struct.unpack(replace_char(vertex_struct, 1, '1'), file.read(vertex_size))[0]
            uv_offset = struct.unpack('<4f', file.read(16))
            morph_data.append((vertex_index, uv_offset))
        elif morph_type == 7:  # UV extended4
            vertex_index = struct.unpack(replace_char(vertex_struct, 1, '1'), file.read(vertex_size))[0]
            uv_offset = struct.unpack('<4f', file.read(16))
            morph_data.append((vertex_index, uv_offset))
        elif morph_type == 8:  # Material
            material_index = struct.unpack(replace_char(material_struct, 1, '1'), file.read(material_size))[0]
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
        elif morph_type == 9:  # Flip
            morph_index = struct.unpack(replace_char(morph_struct, 1, '1'), file.read(morph_bytesize))[0]
            morph_value = struct.unpack('<f', file.read(4))[0]
            morph_data.append((morph_index, morph_value))
        elif morph_type == 10:  # Impulse
            morph_index = struct.unpack(replace_char(rigid_struct, 1, '1'), file.read(rigid_size))[0]
            local_flag = struct.unpack('<b', file.read(1))[0]
            movement_speed = struct.unpack('<3f', file.read(12))
            rotation_torque = struct.unpack('<3f', file.read(12))
            morph_data.append((morph_index, local_flag, movement_speed, rotation_torque))
    
    return morph_name, morph_english_name, panel, morph_type, morph_data

def read_index_size(index, types):
    
    struct = "<??"
    byte_size = 0
    if index == 1:
        struct = replace_char(struct, 2, types[0])
        byte_size = 1
    elif index == 2:
        struct = replace_char(struct,2,types[1])
        byte_size = 2
    else:
        struct = replace_char(struct,2,types[2])
        byte_size = 4
    
    return struct, byte_size

def import_pmx(filepath):
    try:
        faces = []
        vertices = []
        textures = []
        materials = []
        bones = []
        morphs = []
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
                
                
                #====== Start reading index sizes and create helper prebuilts =====
                morph_struct, morph_size = read_index_size(morph_index_size, 'bhi')
                
                vertex_struct, vertex_size = read_index_size(vertex_index_size, 'BHi')
                
                bone_struct, bone_size = read_index_size(bone_index_size, 'bhi')
                
                material_struct, material_size = read_index_size(material_index_size, 'bhi')
                
                texture_struct, texture_size = read_index_size(texture_index_size, 'bhi')
                
                rigid_struct, rigid_size = read_index_size(rigid_body_index_size, 'bhi')
                
                
                
                #====== End of reading index sizes and create helper prebuilts =====
                
                
                for _ in range(vertex_count):
                    position, normal, uv, bone_indices, bone_weights, edge_scale, additional_uv_read = read_vertex(file, bone_struct, bone_size, additional_uvs)
                    vertices.append((position, normal, uv, bone_indices, bone_weights, edge_scale))
                
                # Read faces
                print("stage 4")
                face_count = struct.unpack('<i', file.read(4))[0]
                print("stage 5")
                
                def read_data(data, length):
                    return list(struct.unpack(data, file.read(length)))
                
                
                
                
                #storing function to use in for-loop to prevent checking the same thing a bajillion times - @989onan
                face_funct = lambda: print("invalid face funct")
                if vertex_index_size == 1:
                    face_funct = lambda: read_data('<3B',3)
                elif vertex_index_size == 2:
                    face_funct = lambda: read_data('<3H',6)
                else:
                    face_funct = lambda: read_data('<3i',12)
                for _ in range(face_count // 3):
                    faces.append(face_funct())
                print("stage 6")
                # Read textures
                texture_count = struct.unpack('<i', file.read(4))[0]
                
                for _ in range(texture_count):
                    texture_path = str(file.read(struct.unpack('<i', file.read(4))[0]), 'utf-16-le', errors='replace')
                    textures.append(texture_path)
                print("stage 7")
                # Read materials
                material_count = struct.unpack('<i', file.read(4))[0]
                print("material count "+str(material_count))
                for _ in range(material_count):
                    material_name, material_english_name, diffuse_color, specular_color, specular_strength, ambient_color, flag, edge_color, edge_size, texture_index, sphere_texture_index, sphere_mode, toon_sharing_flag, toon_texture_index, comment, surface_count = read_material(file, texture_struct, texture_size)
                    materials.append((material_name, material_english_name, diffuse_color, specular_color, specular_strength, ambient_color, flag, edge_color, edge_size, texture_index, sphere_texture_index, sphere_mode, toon_sharing_flag, toon_texture_index, comment, surface_count))
                print("stage 8")
                # Read bones
                bone_count = struct.unpack('<i', file.read(4))[0]
                
                
                print("bone count: "+str(bone_count))
                for _ in range(bone_count):
                    bone_name, bone_english_name, position, parent_bone_index, layer, flag, tail_position, inherit_bone_parent_index, inherit_bone_parent_influence, fixed_axis, local_x_vector, local_z_vector, external_key, ik_target_bone_index, ik_loop_count, ik_limit_radian, ik_links = read_bone(file, bone_struct, bone_size)
                    bones.append((bone_name, bone_english_name, position, parent_bone_index, layer, flag, tail_position, inherit_bone_parent_index, inherit_bone_parent_influence, fixed_axis, local_x_vector, local_z_vector, external_key, ik_target_bone_index, ik_loop_count, ik_limit_radian, ik_links))
                
                # Read morphs
                morph_count = struct.unpack('<i', file.read(4))[0]
                print("morph count: "+str(morph_count))
                
                
                
                
                
                for _ in range(morph_count):
                    morph_name, morph_english_name, panel, morph_type, morph_data = read_morph(file, morph_struct, morph_size, vertex_struct, vertex_size, bone_struct, bone_size, material_struct, material_size, rigid_struct, rigid_size)
                    morphs.append((morph_name, morph_english_name, panel, morph_type, morph_data))
                print("finished reading file!")
        except Exception as e:
            print(str(e))
            #pass
            
            #raise IOError("Could not read PMX file") from e
        # Create Blender objects and assign PMX data
        mesh = bpy.data.meshes.new(model_name)
        mesh.from_pydata([v[0] for v in vertices], [], faces)
        mesh.update()
        
        obj = bpy.data.objects.new(model_name, mesh)
        bpy.context.collection.objects.link(obj)
        
        # Assign vertex normals
        custom_normals = [(Vector(i[1]).xzy).normalized() for i in vertices]
        mesh.normals_split_custom_set_from_vertices(custom_normals)
        
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
            #material.ambient = material_data[5] #TODO: this doesn't exist
            # Set other material properties based on the PMX data
            
            mesh.materials.append(material)
        
        # Create armature and assign bones
        armature = bpy.data.armatures.new(model_name + "_Armature")
        armature_obj = bpy.data.objects.new(model_name + "_Armature", armature)
        bpy.context.collection.objects.link(armature_obj)
        obj.parent = armature_obj
        modifier = obj.modifiers.new("Armature", 'ARMATURE')
        modifier.object = armature_obj

        
        
        bpy.context.view_layer.objects.active = armature_obj
        bpy.ops.object.mode_set(mode='EDIT')
        
        for bone_data in bones:
            bone = armature.edit_bones.new(bone_data[0])
            bone.head = bone_data[2]
            
            if bone_data[6][0] != None:
                bone.tail = bone_data[6]
            else:
                bone.tail = [bone.head[0],bone.head[1],bone.head[2]+1]
                #print("fire2!")
                
            
            #print(bone_data)
            if bone_data[3] != -1 or bone_data[3] != -1:
                #print("parent bone index: " + str(bone_data[3]))
                #print("parent bone name: \""+bones[bone_data[3]][0]+"\"")
                #print("parent edit bone name: \""+armature.edit_bones[bones[bone_data[3]][0]].name+"\"")
                #print("fire1!")
                
                parent_bone = armature.edit_bones[bones[bone_data[3]][0]]
                parent_bone.tail = bone.head.xyz
                
                bone.parent = parent_bone
            # Set other bone properties based on the PMX data
        
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Assign bone weights to the mesh
        for i, vertex in enumerate(vertices):
            for j in range(0,len(vertex[3])):
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
        
        #ROTATE LAST!
        armature_obj.rotation_euler[0] = 1.5708
        armature_obj.rotation_euler[2] = 3.14159
        armature_obj.select_set(True)
        obj.select_set(True)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        
        
        print(f"Successfully imported PMX file: {filepath}")
        print(f"Model Name: {model_name}")
        print(f"Model English Name: {model_english_name}")
        print(f"Model Comment: {model_comment}")
        print(f"Model English Comment: {model_english_comment}")
    except Exception as e:
        print(f"Error importing PMX file: {filepath}")
        print(f"Error details hhh: {traceback.format_exc()}")