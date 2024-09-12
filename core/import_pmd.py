import bpy
import struct
import mathutils
import traceback
import os

from bpy.types import Material, Operator, Context, Object, Image, Mesh, MeshUVLoopLayer, Float2AttributeValue, ShaderNodeTexImage, ShaderNodeBsdfPrincipled, ShaderNodeOutputMaterial

def read_pmd_header(file):
    # Read PMD header information
    magic = file.read(3)
    if magic != b'Pmd':
        raise ValueError("Invalid PMD file")
    
    version = struct.unpack('<f', file.read(4))[0]
    
    # Read additional header fields
    model_name = file.read(20).decode('shift-jis').rstrip('\0')
    comment = file.read(256).decode('shift-jis').rstrip('\0')
    
    return version, model_name, comment

def read_pmd_vertex(file):
    # Read PMD vertex information
    position = struct.unpack('<3f', file.read(12))
    normal = struct.unpack('<3f', file.read(12))
    uv = struct.unpack('<2f', file.read(8))
    bone_indices = list(struct.unpack('<2H', file.read(4)))
    bone_weights = struct.unpack('<b', file.read(1))[0] / 100
    edge_flag = struct.unpack('<b', file.read(1))[0]
    
    return position, normal, uv, bone_indices, bone_weights, edge_flag

def read_pmd_material(file):
    # Read PMD material information
    diffuse_color = struct.unpack('<4f', file.read(16))
    specular_color = struct.unpack('<3f', file.read(12))
    specular_intensity = struct.unpack('<f', file.read(4))[0]
    ambient_color = struct.unpack('<3f', file.read(12))
    toon_index = struct.unpack('<b', file.read(1))[0]
    edge_flag = struct.unpack('<b', file.read(1))[0]
    vertex_count = struct.unpack('<i', file.read(4))[0]
    texture_file_name = file.read(20).decode('shift-jis').rstrip('\0')
    
    return diffuse_color, specular_color, specular_intensity, ambient_color, toon_index, edge_flag, vertex_count, texture_file_name

def read_pmd_bone(file):
    # Read PMD bone information
    bone_name = file.read(20).decode('shift-jis').rstrip('\0')
    parent_bone_index = struct.unpack('<h', file.read(2))[0]
    tail_pos_bone_index = struct.unpack('<h', file.read(2))[0]
    bone_type = struct.unpack('<b', file.read(1))[0]
    ik_parent_bone_index = struct.unpack('<h', file.read(2))[0]
    bone_head_pos = struct.unpack('<3f', file.read(12))
    
    return bone_name, parent_bone_index, tail_pos_bone_index, bone_type, ik_parent_bone_index, bone_head_pos

def read_pmd_ik(file):
    # Read PMD IK information
    ik_bone_index = struct.unpack('<h', file.read(2))[0]
    ik_target_bone_index = struct.unpack('<h', file.read(2))[0]
    ik_chain_length = struct.unpack('<b', file.read(1))[0]
    iterations = struct.unpack('<h', file.read(2))[0]
    limit_angle = struct.unpack('<f', file.read(4))[0]
    
    ik_child_bone_indices = []
    for _ in range(ik_chain_length):
        ik_child_bone_index = struct.unpack('<h', file.read(2))[0]
        ik_child_bone_indices.append(ik_child_bone_index)
    
    return ik_bone_index, ik_target_bone_index, ik_chain_length, iterations, limit_angle, ik_child_bone_indices

def read_pmd_morph(file):
    # Read PMD morph information
    morph_name = file.read(20).decode('shift-jis').rstrip('\0')
    morph_vertex_count = struct.unpack('<i', file.read(4))[0]
    morph_type = struct.unpack('<b', file.read(1))[0]
    
    morph_vertices = []
    for _ in range(morph_vertex_count):
        morph_vertex_index = struct.unpack('<i', file.read(4))[0]
        morph_vertex_pos = struct.unpack('<3f', file.read(12))
        morph_vertices.append((morph_vertex_index, morph_vertex_pos))
    
    return morph_name, morph_vertex_count, morph_type, morph_vertices

def import_pmd(filepath):
    try:
        with open(filepath, 'rb') as file:
            version, model_name, comment = read_pmd_header(file)
            
            # Read vertices
            vertex_count = struct.unpack('<i', file.read(4))[0]
            vertices = []
            for _ in range(vertex_count):
                position, normal, uv, bone_indices, bone_weights, edge_flag = read_pmd_vertex(file)
                vertices.append((position, normal, uv, bone_indices, bone_weights, edge_flag))
            
            # Read faces
            face_count = struct.unpack('<i', file.read(4))[0]
            faces = []
            for _ in range(face_count // 3):
                face_indices = struct.unpack('<3i', file.read(12))
                faces.append(face_indices)
            
            # Read materials
            material_count = struct.unpack('<i', file.read(4))[0]
            materials = []
            for _ in range(material_count):
                diffuse_color, specular_color, specular_intensity, ambient_color, toon_index, edge_flag, vertex_count, texture_file_name = read_pmd_material(file)
                materials.append((diffuse_color, specular_color, specular_intensity, ambient_color, toon_index, edge_flag, vertex_count, texture_file_name))
            
            # Read bones
            bone_count = struct.unpack('<h', file.read(2))[0]
            bones = []
            for _ in range(bone_count):
                bone_name, parent_bone_index, tail_pos_bone_index, bone_type, ik_parent_bone_index, bone_head_pos = read_pmd_bone(file)
                bones.append((bone_name, parent_bone_index, tail_pos_bone_index, bone_type, ik_parent_bone_index, bone_head_pos))
            
            # Read IKs
            ik_count = struct.unpack('<h', file.read(2))[0]
            iks = []
            for _ in range(ik_count):
                ik_bone_index, ik_target_bone_index, ik_chain_length, iterations, limit_angle, ik_child_bone_indices = read_pmd_ik(file)
                iks.append((ik_bone_index, ik_target_bone_index, ik_chain_length, iterations, limit_angle, ik_child_bone_indices))
            
            # Read morphs
            morph_count = struct.unpack('<h', file.read(2))[0]
            morphs = []
            for _ in range(morph_count):
                morph_name, morph_vertex_count, morph_type, morph_vertices = read_pmd_morph(file)
                morphs.append((morph_name, morph_vertex_count, morph_type, morph_vertices))
            
            # Create Blender objects and assign PMD data
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
                material: bpy.types.Material
                if f"Material_{len(mesh.materials)}" in bpy.data.materials:
                    material = bpy.data.materials[f"Material_{len(mesh.materials)}"]
                else:
                    material = bpy.data.materials.new(f"Material_{len(mesh.materials)}")

                material.use_nodes = True
                for node in [node for node in material.node_tree.nodes]:
                    material.node_tree.nodes.remove(node)
                
                principled_node: ShaderNodeBsdfPrincipled = material.node_tree.nodes.new(type="ShaderNodeBsdfPrincipled")
                principled_node.location.x = 7.29706335067749
                principled_node.location.y = 298.918212890625
                principled_node.inputs["Base Color"].default_value = material_data[0]
                principled_node.inputs["Specular Tint"].default_value = [material_data[1][0],material_data[1][1],material_data[1][2],1.0]
                principled_node.inputs["Specular IOR Level"].default_value = material_data[2]

                output_node: ShaderNodeOutputMaterial = material.node_tree.nodes.new(type="ShaderNodeOutputMaterial")
                output_node.location.x = 297.29705810546875
                output_node.location.y = 298.918212890625

                albedo_node: ShaderNodeTexImage = material.node_tree.nodes.new(type="ShaderNodeTexImage")
                albedo_node.location.x = -588.6177978515625
                albedo_node.location.y = 414.1948547363281

                if texture_file_name in bpy.data.images:
                    albedo_node.image = bpy.data.images[texture_file_name]
                else:
                    albedo_node.image = bpy.data.images.new(name=texture_file_name,width=32,height=32)
                    albedo_node.image.filepath = os.path.join(os.path.dirname(filepath),texture_file_name)
                    albedo_node.image.source = 'FILE'
                    albedo_node.image.reload()
                    
                

                material.node_tree.links.new(principled_node.inputs["Base Color"], albedo_node.outputs["Color"])
                material.node_tree.links.new(principled_node.inputs["Alpha"], albedo_node.outputs["Alpha"])
                material.node_tree.links.new(output_node.inputs["Surface"], principled_node.outputs["BSDF"])
                
                #material.ambient = material_data[5] #TODO: this doesn't exist
                # Set other material properties based on the PMX data
                if not (material.name in mesh.materials):
                    mesh.materials.append(material)

                #surprised this works - @989onan
                end: int = cur_polygon_index+material_data[15]-1
                for face in mesh.polygons.items()[cur_polygon_index:end]:
                    face[1].material_index = mesh.materials.find(material.name)
                
                cur_polygon_index = cur_polygon_index+material_data[15]
                # Set other material properties based on the PMD data
            
            # Create armature and assign bones
            armature = bpy.data.armatures.new(model_name + "_Armature")
            armature_obj = bpy.data.objects.new(model_name + "_Armature", armature)
            bpy.context.collection.objects.link(armature_obj)
            
            bpy.context.view_layer.objects.active = armature_obj
            bpy.ops.object.mode_set(mode='EDIT')
            
            for bone_data in bones:
                bone = armature.edit_bones.new(bone_data[0])
                bone.head = bone_data[5]
                
                if bone_data[1] != -1:
                    parent_bone = armature.edit_bones[bone_data[1]]
                    bone.parent = parent_bone
                    bone.tail = parent_bone.head
                else:
                    bone.tail = bone.head + mathutils.Vector((0, 0.1, 0))
                
                # Set other bone properties based on the PMD data
            
            bpy.ops.object.mode_set(mode='OBJECT')
            
            # Assign bone weights to the mesh
            for i, vertex in enumerate(vertices):
                for j in range(2):
                    if vertex[3][j] != 65535:
                        bone_name = bones[vertex[3][j]][0]
                        weight = vertex[4] if j == 0 else 1 - vertex[4]
                        
                        vertex_group = obj.vertex_groups.get(bone_name)
                        if not vertex_group:
                            vertex_group = obj.vertex_groups.new(name=bone_name)
                        
                        vertex_group.add([i], weight, 'REPLACE')
            
            # Assign IK constraints to bones
            for ik_data in iks:
                ik_bone = armature.bones[bones[ik_data[0]][0]]
                ik_target_bone = armature.bones[bones[ik_data[1]][0]]
                
                ik_constraint = ik_bone.constraints.new('IK')
                ik_constraint.target = armature_obj
                ik_constraint.subtarget = ik_target_bone.name
                ik_constraint.chain_count = ik_data[2]
                ik_constraint.iterations = ik_data[3]
                ik_constraint.limit_mode = 'LIMITDIST_INSIDE'
                ik_constraint.limit_mode_max_x = ik_data[4]
            
            # Assign morphs to the mesh
            for morph_data in morphs:
                morph_name = morph_data[0]
                morph_type = morph_data[2]
                
                if morph_type == 0:  # Vertex morph
                    shape_key = obj.shape_key_add(name=morph_name)
                    for vertex_data in morph_data[3]:
                        vertex_index = vertex_data[0]
                        vertex_offset = vertex_data[1]
                        shape_key.data[vertex_index].co += mathutils.Vector(vertex_offset)
            
            print(f"Successfully imported PMD file: {filepath}")
            print(f"Model Name: {model_name}")
            print(f"Comment: {comment}")
    except Exception:
        print(f"Error importing PMD file: {filepath}")
        print(f"Error details: {traceback.format_exc()}")
