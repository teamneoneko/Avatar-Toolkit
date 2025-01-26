import struct
from dataclasses import dataclass
from typing import List, Tuple, Optional, Union, Dict
from mathutils import Vector
from ..logging_setup import logger

INDEX_TYPES = {
    1: {'vertex': 'B', 'bone': 'b', 'other': 'b'},  # unsigned/signed byte
    2: {'vertex': 'H', 'bone': 'h', 'other': 'h'},  # unsigned/signed short  
    4: {'vertex': 'I', 'bone': 'i', 'other': 'i'}   # unsigned/signed int
}

# Bone flag constants
BONE_FLAGS = {
    'INDEXED_TAIL_POSITION': 0x0001,
    'ROTATABLE': 0x0002,
    'TRANSLATABLE': 0x0004,
    'VISIBLE': 0x0008,
    'ENABLED': 0x0010,
    'IK': 0x0020,
    'INHERIT_ROTATION': 0x0100,
    'INHERIT_TRANSLATION': 0x0200,
    'FIXED_AXIS': 0x0400,
    'LOCAL_COORDINATE': 0x0800,
    'PHYSICS_AFTER_DEFORM': 0x1000,
    'EXTERNAL_PARENT_DEFORM': 0x2000
}

@dataclass
class PMXVertex:
    position: Vector
    normal: Vector
    uv: Tuple[float, float]
    bone_indices: List[int] 
    bone_weights: List[float]

@dataclass
class PMXMaterial:
    name: str
    name_en: str
    diffuse: Tuple[float, float, float, float]  # RGBA
    specular: Tuple[float, float, float]        # RGB
    specular_strength: float
    ambient: Tuple[float, float, float]         # RGB
    flags: int                                  # Drawing flags
    edge_color: Tuple[float, float, float, float]  # RGBA
    edge_scale: float
    texture_index: int
    environment_index: int
    environment_blend_mode: int
    toon_reference: int
    toon_value: Union[int, bytes]
    metadata: str
    surface_count: int

@dataclass
class PMXBone:
    name: str
    name_en: str
    position: Tuple[float, float, float]
    parent_index: int
    layer: int
    flags: int
    tail_position: Union[Tuple[float, float, float], int]
    inherit_bone: Optional[dict] = None
    fixed_axis: Optional[dict] = None
    local_coordinate: Optional[dict] = None
    external_parent: Optional[dict] = None
    ik: Optional[dict] = None

def load_pmx_file(filepath: str):
    """Load and parse PMX file format"""
    with open(filepath, 'rb') as f:
        # Debug file header
        header_bytes = f.read(4)
        logger.debug(f"File signature: {header_bytes}")
        f.seek(0)  # Reset position
        
        # Check PMX signature
        if f.read(4) != b'PMX ':
            raise ValueError("Not a valid PMX file")
            
        # Read version
        version = struct.unpack('<f', f.read(4))[0]
        logger.debug(f"PMX Version: {version}")
        
        # Read header info
        header_size = f.read(1)[0]
        logger.debug(f"Header size: {header_size}")
        
        # Read encoding flags
        encoding_flag = f.read(1)[0]
        encoding = 'utf-16-le' if encoding_flag == 0 else 'utf-8'
        logger.debug(f"Detected encoding flag: {encoding_flag}")
        additional_vec4s = f.read(1)[0]
        vertex_index_size = f.read(1)[0]
        texture_index_size = f.read(1)[0]
        material_index_size = f.read(1)[0]
        bone_index_size = f.read(1)[0]
        morph_index_size = f.read(1)[0]
        rigid_body_index_size = f.read(1)[0]
        
        logger.debug(f"Encoding: {encoding}")
        logger.debug(f"Additional Vec4s: {additional_vec4s}")
        logger.debug(f"Index Sizes - Vertex: {vertex_index_size}, Texture: {texture_index_size}, Material: {material_index_size}")
        logger.debug(f"Index Sizes - Bone: {bone_index_size}, Morph: {morph_index_size}, RigidBody: {rigid_body_index_size}")

        # Read model info
        name_jp = _read_text(f, encoding)
        name_en = _read_text(f, encoding)
        comment_jp = _read_text(f, encoding)
        comment_en = _read_text(f, encoding)
        
        logger.debug(f"Model name: {name_en} ({name_jp})")

        # Read vertices
        vertex_count = struct.unpack('<i', f.read(4))[0]
        logger.debug(f"Vertex count: {vertex_count}")
        vertices = _read_vertices(f, vertex_count)

        # Read faces
        face_count = struct.unpack('<i', f.read(4))[0]
        logger.debug(f"Face count: {face_count}")
        faces = _read_faces(f, face_count, vertex_index_size)

        # Read texture count and paths
        texture_count = struct.unpack('<i', f.read(4))[0]
        logger.debug(f"Texture count: {texture_count}")
        textures = _read_textures(f, texture_count, encoding)

        # Read materials with texture index size
        material_count = struct.unpack('<i', f.read(4))[0]
        logger.debug(f"Material count: {material_count}")
        materials = _read_materials(f, material_count, encoding, texture_index_size)

        # Read bones
        bone_count = struct.unpack('<i', f.read(4))[0]
        logger.debug(f"Bone count: {bone_count}")
        bones = _read_bones(f, bone_count, encoding, bone_index_size)

        # Read morphs
        morph_count = struct.unpack('<i', f.read(4))[0]
        logger.debug(f"Morph count: {morph_count}")
        morphs = []

        # Read rigid bodies
        rigid_body_count = struct.unpack('<i', f.read(4))[0]
        logger.debug(f"Rigid body count: {rigid_body_count}")
        rigid_bodies = _read_rigid_bodies(f, rigid_body_count, encoding, bone_index_size)

        # Read joints
        joint_count = struct.unpack('<i', f.read(4))[0]
        logger.debug(f"Joint count: {joint_count}")
        joints = _read_joints(f, joint_count, encoding, rigid_body_index_size)

        for _ in range(morph_count):
            morph_data = {
                'name': _read_text(f, encoding),
                'name_en': _read_text(f, encoding),
                'panel': struct.unpack('B', f.read(1))[0],
                'type': struct.unpack('B', f.read(1))[0],
                'offsets': []
            }
            
            offset_count = struct.unpack('<i', f.read(4))[0]
            
            for _ in range(offset_count):
                offset = {}
                morph_type = morph_data['type']
                
                if morph_type == 0:  # Group
                    offset['index'] = _read_index(f, morph_index_size)
                    offset['influence'] = struct.unpack('<f', f.read(4))[0]
                elif morph_type == 1:  # Vertex
                    offset['index'] = _read_index(f, vertex_index_size)
                    offset['translation'] = _read_vec3(f)
                elif morph_type == 2:  # Bone
                    offset['index'] = _read_index(f, bone_index_size)
                    offset['translation'] = _read_vec3(f)
                    offset['rotation'] = _read_vec4(f)
                elif morph_type == 3:  # UV
                    offset['index'] = _read_index(f, vertex_index_size)
                    offset['floats'] = _read_vec4(f)
                elif morph_type == 8:  # Material
                    offset['index'] = _read_index(f, material_index_size)
                    offset['is_add'] = struct.unpack('B', f.read(1))[0]
                    offset['diffuse'] = _read_vec4(f)
                    offset['specular'] = _read_vec3(f)
                    offset['specularity'] = struct.unpack('<f', f.read(4))[0]
                    offset['ambient'] = _read_vec3(f)
                    offset['edge_color'] = _read_vec4(f)
                    offset['edge_size'] = struct.unpack('<f', f.read(4))[0]
                    offset['texture_tint'] = _read_vec4(f)
                    offset['environment_tint'] = _read_vec4(f)
                    offset['toon_tint'] = _read_vec4(f)
                    
                morph_data['offsets'].append(offset)
                
            morphs.append(morph_data)

        return {
            'name': name_jp,
            'name_en': name_en,
            'vertices': vertices,
            'faces': faces,
            'textures': textures,
            'materials': materials,
            'bones': bones,
            'morphs': morphs,
            'rigid_bodies': rigid_bodies,
            'joints': joints,
            'comment_jp': comment_jp,
            'comment_en': comment_en
        }

def _read_text(f, encoding: str) -> str:
    """Read text according to PMX specification with robust UTF-16-LE handling"""

    # Read 4-byte length (int32_t)
    length = struct.unpack('<i', f.read(4))[0]
    
    if length <= 0:
        return ""
        
    # Read exact number of bytes
    text_bytes = f.read(length)
    
    # Try encodings in order of likelihood
    encodings = [encoding, 'shift-jis', 'cp932']
    
    for enc in encodings:
        try:
            return text_bytes.decode(enc)
        except UnicodeDecodeError:
            continue
            
    # If all decodings fail, return empty string to continue parsing
    return ""

def _read_vertices(f, count: int) -> List[PMXVertex]:
    """Read vertex data according to PMX 2.0/2.1 specification"""
    vertices = []
    for vertex_index in range(count):
        # Position, Normal, UV
        pos = struct.unpack('<fff', f.read(12))
        normal = struct.unpack('<fff', f.read(12))
        uv = struct.unpack('<ff', f.read(8))
        
        # Skip any additional UV coordinates (vec4s)
        additional_vec4_count = 0  # This should be passed from header
        if additional_vec4_count > 0:
            f.read(16 * additional_vec4_count)
        
        # Read weight type as a single byte
        weight_type = struct.unpack('<B', f.read(1))[0]
        
        if weight_type == 0:  # BDEF1
            indices = [struct.unpack('<h', f.read(2))[0]]  # Using correct index size
            weights = [1.0]
        elif weight_type == 1:  # BDEF2
            indices = [struct.unpack('<h', f.read(2))[0] for _ in range(2)]
            weights = [struct.unpack('<f', f.read(4))[0]]
            weights.append(1.0 - weights[0])
        elif weight_type == 2:  # BDEF4
            indices = [struct.unpack('<h', f.read(2))[0] for _ in range(4)]
            weights = [struct.unpack('<f', f.read(4))[0] for _ in range(4)]
        elif weight_type == 3:  # SDEF
            indices = [struct.unpack('<h', f.read(2))[0] for _ in range(2)]
            weights = [struct.unpack('<f', f.read(4))[0]]
            weights.append(1.0 - weights[0])
            sdef_c = struct.unpack('<fff', f.read(12))
            sdef_r0 = struct.unpack('<fff', f.read(12))
            sdef_r1 = struct.unpack('<fff', f.read(12))
        elif weight_type == 4:  # QDEF
            indices = [struct.unpack('<h', f.read(2))[0] for _ in range(4)]
            weights = [struct.unpack('<f', f.read(4))[0] for _ in range(4)]
        else:
            raise ValueError(f"Weight type {weight_type} is outside valid range (0-4)")
            
        # Edge scale
        edge_scale = struct.unpack('<f', f.read(4))[0]
            
        vertices.append(PMXVertex(
            Vector(pos),
            Vector(normal),
            uv,
            indices,
            weights
        ))
    return vertices


def _read_faces(f, count: int, index_size: int) -> List[Tuple[int, int, int]]:
    """Read face indices"""
    faces = []
    for _ in range(count // 3):
        if index_size == 1:
            indices = struct.unpack('BBB', f.read(3))
        elif index_size == 2:
            indices = struct.unpack('HHH', f.read(6))
        elif index_size == 4:
            indices = struct.unpack('III', f.read(12))
        faces.append(indices)
    return faces

def _read_textures(f, count: int, encoding: str) -> List[str]:
    """Read texture paths"""
    textures = []
    for _ in range(count):
        path = _read_text(f, encoding)
        # Handle reserved toon textures
        if any(toon in path.lower() for toon in [f"toon{i:02d}.bmp" for i in range(1, 11)]):
            logger.warning(f"Found reserved toon texture name: {path}")
        textures.append(path)
    return textures

def _read_vec2(f) -> Tuple[float, float]:
    """Read 2D vector"""
    return struct.unpack('<ff', f.read(8))

def _read_vec3(f) -> Tuple[float, float, float]:
    """Read 3D vector"""
    return struct.unpack('<fff', f.read(12))

def _read_vec4(f) -> Tuple[float, float, float, float]:
    """Read 4D vector"""
    return struct.unpack('<ffff', f.read(16))

def _read_index(f, size: int, index_type: str = 'other') -> int:
    """Read index value based on size and type"""
    format_char = INDEX_TYPES[size][index_type]
    return struct.unpack(f'<{format_char}', f.read(size))[0]

def _read_materials(f, count: int, encoding: str, texture_index_size: int) -> List[PMXMaterial]:
    """Read material data according to PMX 2.0/2.1 spec"""
    materials = []
    for _ in range(count):
        # Basic info
        name = _read_text(f, encoding)
        name_en = _read_text(f, encoding)
        
        # Colors and properties
        diffuse = _read_vec4(f)
        specular = _read_vec3(f)
        specular_strength = struct.unpack('<f', f.read(4))[0]
        ambient = _read_vec3(f)
        
        # Flags and edge properties
        flags = struct.unpack('B', f.read(1))[0]
        edge_color = _read_vec4(f)
        edge_scale = struct.unpack('<f', f.read(4))[0]
        
        # Texture references
        texture_index = _read_index(f, texture_index_size)
        environment_index = _read_index(f, texture_index_size)
        environment_blend_mode = struct.unpack('B', f.read(1))[0]
        
        # Toon properties
        toon_reference = struct.unpack('B', f.read(1))[0]
        if toon_reference == 0:
            toon_value = _read_index(f, texture_index_size)
        else:
            toon_value = struct.unpack('B', f.read(1))[0]
            
        # Additional data
        metadata = _read_text(f, encoding)
        surface_count = struct.unpack('<I', f.read(4))[0]
        
        materials.append(PMXMaterial(
            name=name,
            name_en=name_en,
            diffuse=diffuse,
            specular=specular,
            specular_strength=specular_strength,
            ambient=ambient,
            flags=flags,
            edge_color=edge_color,
            edge_scale=edge_scale,
            texture_index=texture_index,
            environment_index=environment_index,
            environment_blend_mode=environment_blend_mode,
            toon_reference=toon_reference,
            toon_value=toon_value,
            metadata=metadata,
            surface_count=surface_count
        ))
    return materials

def _read_bones(f, count: int, encoding: str, bone_index_size: int) -> List[PMXBone]:
    """Read bone data according to PMX spec"""
    bones = []
    for _ in range(count):
        # Basic bone data
        name = _read_text(f, encoding)
        name_en = _read_text(f, encoding)
        position = _read_vec3(f)
        parent_index = _read_index(f, bone_index_size, 'bone')
        layer = struct.unpack('<i', f.read(4))[0]
        flags = struct.unpack('<H', f.read(2))[0]
        
        # Handle tail position based on flag
        if flags & BONE_FLAGS['INDEXED_TAIL_POSITION']:
            tail_position = _read_index(f, bone_index_size, 'bone')
        else:
            tail_position = _read_vec3(f)
            
        bone_data = {
            'name': name,
            'name_en': name_en,
            'position': position,
            'parent_index': parent_index,
            'layer': layer,
            'flags': flags,
            'tail_position': tail_position
        }
        
        # Read inheritance data
        if flags & (BONE_FLAGS['INHERIT_ROTATION'] | BONE_FLAGS['INHERIT_TRANSLATION']):
            bone_data['inherit_bone'] = {
                'parent_index': _read_index(f, bone_index_size, 'bone'),
                'influence': struct.unpack('<f', f.read(4))[0]
            }
            
        # Read fixed axis data
        if flags & BONE_FLAGS['FIXED_AXIS']:
            bone_data['fixed_axis'] = {
                'axis_direction': _read_vec3(f)
            }
            
        # Read local coordinate data
        if flags & BONE_FLAGS['LOCAL_COORDINATE']:
            bone_data['local_coordinate'] = {
                'x_vector': _read_vec3(f),
                'z_vector': _read_vec3(f)
            }
            
        # Read external parent data
        if flags & BONE_FLAGS['EXTERNAL_PARENT_DEFORM']:
            bone_data['external_parent'] = {
                'parent_index': _read_index(f, bone_index_size, 'bone')
            }
            
        # Read IK data
        if flags & BONE_FLAGS['IK']:
            ik_data = {
                'target_index': _read_index(f, bone_index_size, 'bone'),
                'loop_count': struct.unpack('<i', f.read(4))[0],
                'limit_radian': struct.unpack('<f', f.read(4))[0],
                'links': []
            }
            
            link_count = struct.unpack('<i', f.read(4))[0]
            for _ in range(link_count):
                link = {
                    'bone_index': _read_index(f, bone_index_size, 'bone'),
                    'has_limits': struct.unpack('B', f.read(1))[0]
                }
                
                if link['has_limits']:
                    link['limit_min'] = _read_vec3(f)
                    link['limit_max'] = _read_vec3(f)
                    
                ik_data['links'].append(link)
                
            bone_data['ik'] = ik_data
            
        bones.append(PMXBone(**bone_data))
        
    return bones
    
def _read_rigid_bodies(f, count: int, encoding: str, bone_index_size: int) -> List[Dict]:
    """Read rigid body data according to PMX 2.0/2.1 spec"""
    rigid_bodies = []
    
    for i in range(count):
        try:
            # Read fixed-length data first
            data = {
                'name': _read_text(f, encoding) or f"RigidBody_{i}",
                'name_en': _read_text(f, encoding) or f"RigidBody_{i}",
                'bone_index': _read_index(f, bone_index_size, 'bone'),
                'group_id': struct.unpack('B', f.read(1))[0],
                'non_collision_group': struct.unpack('<H', f.read(2))[0],
                'shape_type': struct.unpack('B', f.read(1))[0],
                'shape_size': _read_vec3(f)
            }
            
            # Read position and rotation separately with validation
            pos = _read_vec3(f)
            rot = _read_vec3(f)
            data['position'] = pos
            data['rotation'] = rot
            
            # Read physics parameters with validation
            data.update({
                'mass': struct.unpack('<f', f.read(4))[0],
                'move_attenuation': struct.unpack('<f', f.read(4))[0],
                'rotation_damping': struct.unpack('<f', f.read(4))[0],
                'repulsion': struct.unpack('<f', f.read(4))[0],
                'friction': struct.unpack('<f', f.read(4))[0],
                'physics_mode': struct.unpack('B', f.read(1))[0]
            })
            
            logger.debug(f"Successfully read rigid body {i}: {data['name']}")
            rigid_bodies.append(data)
            
        except struct.error as e:
            logger.error(f"Failed to read rigid body {i}: {str(e)}")
            logger.debug(f"Current file position: {f.tell()}")
            break
            
    return rigid_bodies



def _read_joints(f, count: int, encoding: str, rigid_body_index_size: int) -> List[Dict]:
    """Read joint data according to PMX 2.1 spec"""
    joints = []
    for _ in range(count):
        joint = {
            'name': _read_text(f, encoding),
            'name_en': _read_text(f, encoding),
            'joint_type': struct.unpack('B', f.read(1))[0],
            'rigid_body_a': _read_index(f, rigid_body_index_size, 'other'),
            'rigid_body_b': _read_index(f, rigid_body_index_size, 'other'),
            'position': _read_vec3(f),
            'rotation': _read_vec3(f),
            'position_min': _read_vec3(f),
            'position_max': _read_vec3(f),
            'rotation_min': _read_vec3(f),
            'rotation_max': _read_vec3(f),
            'spring_position': _read_vec3(f),
            'spring_rotation': _read_vec3(f)
        }
        joints.append(joint)
    return joints

