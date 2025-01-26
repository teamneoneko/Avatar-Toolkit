import bpy
import os
import time
from typing import Optional, Dict, List, Set, Tuple
from mathutils import Vector, Matrix, Euler
from ..common import ProgressTracker
from ..logging_setup import logger
from .mmd_parser import load_pmx_file, BONE_FLAGS

class PMXImporter:
    CATEGORIES = {
        0: "SYSTEM",
        1: "EYEBROW", 
        2: "EYE",
        3: "MOUTH"
    }
    
    def __init__(self):
        self.model = None
        self.scale = 1.0
        self.use_mipmap = True
        self.sph_blend_factor = 1.0
        self.spa_blend_factor = 1.0
        
        # Core objects
        self.armature_obj: Optional[bpy.types.Object] = None
        self.mesh_obj: Optional[bpy.types.Object] = None
        self.root_obj: Optional[bpy.types.Object] = None
        
        # Reference tables
        self.bone_table: List[bpy.types.PoseBone] = []
        self.material_table: List[bpy.types.Material] = []
        self.texture_table: List[str] = []
        self.rigid_table: Dict[int, bpy.types.Object] = {}
        self.vertex_group_table = None
        self.material_face_count = []
        self.image_table: Dict[int, bpy.types.Image] = {}
        
        self.sdef_vertices = {}
        self.blender_ik_links: Set[int] = set()
        
    def execute(self, context: bpy.types.Context, filepath: str, **options):
        """Execute PMX import with given options"""
        with ProgressTracker(context, 8, "Importing PMX") as progress:
            start_time = time.time()
            
            try:
                # Load settings
                self.scale = options.get('scale', 1.0)
                self.use_mipmap = options.get('use_mipmap', True)
                self.sph_blend_factor = options.get('sph_blend_factor', 1.0)
                self.spa_blend_factor = options.get('spa_blend_factor', 1.0)
                
                # Import PMX file and log contents
                self.model = self._load_pmx_file(filepath)
                logger.debug(f"Loaded model keys: {self.model.keys()}")
                logger.debug(f"Bones data present: {'bones' in self.model}")
                
                progress.step("Creating objects")
                
                # Create objects
                self._create_base_objects(context)
                
                # Import components
                progress.step("Importing vertices")
                self._import_vertices()
                
                progress.step("Importing materials") 
                self._import_materials()
                
                progress.step("Importing faces")
                self._import_faces()
                
                progress.step("Importing bones")
                self._import_bones()
                
                progress.step("Importing morphs")
                self._import_morphs()
                
                progress.step("Importing physics")
                self._import_rigid_bodies()
                self._import_joints()
                
                progress.step("Finalizing")
                self._finalize_import()
                
                elapsed_time = time.time() - start_time
                logger.info(f"PMX import completed in {elapsed_time:.2f} seconds")
                return {'FINISHED'}
                
            except Exception as e:
                logger.error(f"PMX import failed: {str(e)}")
                return {'CANCELLED'}
            
    def _load_pmx_file(self, filepath: str):
        """Load PMX file and return model data"""
        try:
            return load_pmx_file(filepath)
        except Exception as e:
            logger.error(f"Failed to load PMX file: {str(e)}")
            raise

    def _import_vertices(self):
        """Import vertices with weights and UV data"""
        mesh = self.mesh_obj.data
        pmx_vertices = self.model['vertices']
        
        # Create vertices
        mesh.vertices.add(len(pmx_vertices))
        mesh.vertices.foreach_set("co", [c for v in pmx_vertices for c in Vector(v.position).xzy * self.scale])
        
        # Create vertex groups from bone names
        self.vertex_group_table = []
        for bone_data in self.model['bones']:
            vg = self.mesh_obj.vertex_groups.new(name=bone_data.name) 
            self.vertex_group_table.append(vg)
                
        # Assign weights
        for i, pv in enumerate(pmx_vertices):
            for bone_idx, weight in zip(pv.bone_indices, pv.bone_weights):
                if weight > 0:
                    self.vertex_group_table[bone_idx].add([i], weight, 'ADD')


    def _import_faces(self):
        """Import face indices and create mesh faces"""
        mesh = self.mesh_obj.data
        faces = self.model['faces']
        
        # Create faces
        mesh.loops.add(len(faces) * 3)
        mesh.polygons.add(len(faces))
        
        # Set face indices
        mesh.loops.foreach_set("vertex_index", [i for face in faces for i in face])
        
        # Set polygon data
        poly_lengths = [3] * len(faces)
        mesh.polygons.foreach_set("loop_total", poly_lengths)
        mesh.polygons.foreach_set("loop_start", [i * 3 for i in range(len(faces))])
        mesh.polygons.foreach_set("vertices", [i for face in faces for i in face])
        
        # Update mesh
        mesh.update()

    def _import_materials(self):
        """Import materials with textures and properties"""
        self._import_textures()
        
        for i, pmx_mat in enumerate(self.model['materials']):
            mat = bpy.data.materials.new(name=pmx_mat.name)
            self.material_table.append(mat)
            
            # Setup material
            mat.use_nodes = True
            nodes = mat.node_tree.nodes
            
            # Create principled BSDF
            principled = nodes.get('Principled BSDF')
            if not principled:
                principled = nodes.new('ShaderNodeBsdfPrincipled')
                
            # Set basic properties with updated input names
            principled.inputs['Base Color'].default_value = pmx_mat.diffuse[:4]
            principled.inputs['Specular IOR Level'].default_value = sum(pmx_mat.specular) / 3.0
            principled.inputs['Roughness'].default_value = 1.0 - (pmx_mat.specular_strength / 100.0)

            # Add texture if present
            if pmx_mat.texture_index >= 0 and pmx_mat.texture_index < len(self.texture_table):
                tex_image = self.texture_table[pmx_mat.texture_index]
                tex_node = nodes.new('ShaderNodeTexImage')
                tex_node.image = tex_image
                mat.node_tree.links.new(tex_node.outputs['Color'], principled.inputs['Base Color'])
                self.image_table[i] = tex_image

            self.material_face_count.append(pmx_mat.surface_count)
            self.mesh_obj.data.materials.append(mat)

    def _import_textures(self):
        """Import and load textures"""
        self.texture_table = []
        base_path = os.path.dirname(self.model['textures'][0]) if self.model['textures'] else ""
        
        for tex_path in self.model['textures']:
            # Handle relative/absolute paths
            if os.path.isabs(tex_path):
                full_path = tex_path
            else:
                full_path = os.path.join(base_path, tex_path)
                
            # Load texture
            try:
                image = bpy.data.images.load(full_path)
                image.use_fake_user = True
                if self.use_mipmap:
                    image.use_generated_mipmap = True
            except:
                # Create empty image if loading fails
                image = bpy.data.images.new(
                    name=os.path.basename(tex_path),
                    width=1,
                    height=1
                )
                
            self.texture_table.append(image)

    def _import_bones(self):
        """Import bones with constraints and IK"""
        with bpy.context.temp_override(active_object=self.armature_obj):
            bpy.ops.object.mode_set(mode='EDIT')
            
            # Create edit bones
            edit_bones = self.armature_obj.data.edit_bones
            for bone in self.model['bones']:
                edit_bone = edit_bones.new(name=bone.name)
                position = bone.position
                edit_bone.head = Vector((position[0], position[1], position[2])).xzy * self.scale
                
                # Set tail position
                if bone.tail_position and isinstance(bone.tail_position, tuple):
                    tail = Vector((bone.tail_position[0], bone.tail_position[1], bone.tail_position[2])).xzy * self.scale
                    edit_bone.tail = edit_bone.head + tail
                else:
                    edit_bone.tail = edit_bone.head + Vector((0, 0.1, 0))
                    
                # Set parent with index validation
                if bone.parent_index >= 0 and bone.parent_index < len(edit_bones):
                    edit_bone.parent = edit_bones[bone.parent_index]
        
            bpy.ops.object.mode_set(mode='POSE')
            
            # Setup pose bones and constraints
            pose_bones = self.armature_obj.pose.bones
            self.bone_table = pose_bones
            
            # Only process bones up to the valid range
            max_bone_index = len(pose_bones)
            for i, bone in enumerate(self.model['bones']):
                if i >= max_bone_index:
                    break
                    
                pose_bone = pose_bones[i]
                
                if bone.flags & BONE_FLAGS['IK']:
                    self._create_ik_constraint(pose_bone, bone)
                    
                if bone.flags & (BONE_FLAGS['INHERIT_ROTATION'] | BONE_FLAGS['INHERIT_TRANSLATION']):
                    self._create_additional_transform(pose_bone, bone)

    def _create_ik_constraint(self, pose_bone, pmx_bone):
        """Create IK constraint for a bone"""
        if pmx_bone.ik and pmx_bone.ik['target_index'] >= 0:
            target_index = pmx_bone.ik['target_index']
            if target_index < len(self.bone_table):
                target_bone = self.bone_table[target_index]
                ik = pose_bone.constraints.new('IK')
                ik.target = self.armature_obj
                ik.subtarget = target_bone.name
                ik.chain_count = len(pmx_bone.ik['links'])
                ik.iterations = pmx_bone.ik['loop_count']
                
            # Set IK limits
            for link in pmx_bone.ik['links']:
                if link['has_limits']:
                    bone = self.bone_table[link['bone_index']]
                    bone.use_ik_limit_x = bone.use_ik_limit_y = bone.use_ik_limit_z = True
                    bone.ik_min_x = link['limit_min'][0]
                    bone.ik_min_y = link['limit_min'][1]
                    bone.ik_min_z = link['limit_min'][2]
                    bone.ik_max_x = link['limit_max'][0]
                    bone.ik_max_y = link['limit_max'][1]
                    bone.ik_max_z = link['limit_max'][2]

    def _create_additional_transform(self, pose_bone, pmx_bone):
        """Create additional transform constraints for a bone"""
        if pmx_bone.inherit_bone:
            parent_bone = self.bone_table[pmx_bone.inherit_bone['parent_index']]
            influence = pmx_bone.inherit_bone['influence']
            
            # Create copy rotation constraint
            if pmx_bone.flags & BONE_FLAGS['INHERIT_ROTATION']:
                rot = pose_bone.constraints.new('COPY_ROTATION')
                rot.target = self.armature_obj
                rot.subtarget = parent_bone.name
                rot.influence = influence
                
            # Create copy location constraint
            if pmx_bone.flags & BONE_FLAGS['INHERIT_TRANSLATION']:
                loc = pose_bone.constraints.new('COPY_LOCATION')
                loc.target = self.armature_obj
                loc.subtarget = parent_bone.name
                loc.influence = influence

    def _import_morphs(self):
        """Import vertex, material, bone, and UV morphs"""
        # Create base shape key
        if not self.mesh_obj.data.shape_keys:
            self.mesh_obj.shape_key_add(name="Basis")

        # Vertex morphs
        for morph in self.model['morphs']:
            if morph['type'] == 1:  # Vertex morph
                shape_key = self.mesh_obj.shape_key_add(name=morph['name'])
                for offset in morph['offsets']:
                    shape_key.data[offset['index']].co += Vector(offset['translation']).xzy * self.scale

        # Material morphs
        for morph in self.model['morphs']:
            if morph['type'] == 8:  # Material morph
                for offset in morph['offsets']:
                    if offset['index'] < len(self.material_table):
                        mat = self.material_table[offset['index']]
                        self._apply_material_morph(mat, offset)

    def _apply_material_morph(self, material, offset):
        """Apply material morph data to the specified material"""
        if material.node_tree:
            principled = material.node_tree.nodes.get('Principled BSDF')
            if principled:
                if offset['is_add']:
                    # Additive blending
                    principled.inputs['Base Color'].default_value = [
                        a + b for a, b in zip(principled.inputs['Base Color'].default_value, offset['diffuse'])
                    ]
                    principled.inputs['Specular IOR Level'].default_value += sum(offset['specular']) / 3.0
                    principled.inputs['Roughness'].default_value += offset['specularity']
                else:
                    # Multiplicative blending
                    principled.inputs['Base Color'].default_value = [
                        a * b for a, b in zip(principled.inputs['Base Color'].default_value, offset['diffuse'])
                    ]
                    principled.inputs['Specular IOR Level'].default_value *= sum(offset['specular']) / 3.0
                    principled.inputs['Roughness'].default_value *= offset['specularity']

    def _import_rigid_bodies(self):
        """Import rigid body physics with enhanced error handling"""
        if not self.model.get('rigid_bodies'):
            logger.warning("No rigid bodies found in model")
            return
            
        logger.info(f"Importing {len(self.model['rigid_bodies'])} rigid bodies")
        
        for i, rigid in enumerate(self.model['rigid_bodies']):
            try:
                obj = bpy.data.objects.new(f"rigid_{rigid['name']}", None)
                obj.empty_display_type = 'SPHERE'
                bpy.context.scene.collection.objects.link(obj)
                
                # Set transform with validation
                obj.location = Vector(rigid['position']).xzy * self.scale
                obj.rotation_euler = Euler(Vector(rigid['rotation']).xzy)
                
                # Setup rigid body physics with validation
                obj.rigid_body.type = 'ACTIVE' if rigid['physics_mode'] == 0 else 'PASSIVE'
                obj.rigid_body.collision_shape = self._get_collision_shape(rigid['shape_type'])
                obj.rigid_body.mass = max(0.001, rigid['mass'])
                obj.rigid_body.friction = max(0, min(1, rigid['friction']))
                obj.rigid_body.restitution = max(0, min(1, rigid['repulsion']))
                
                # Link to bone if valid
                if rigid['bone_index'] >= 0 and rigid['bone_index'] < len(self.bone_table):
                    bone = self.bone_table[rigid['bone_index']]
                    constraint = obj.constraints.new('CHILD_OF')
                    constraint.target = self.armature_obj
                    constraint.subtarget = bone.name
                    
                self.rigid_table[i] = obj
                logger.debug(f"Successfully imported rigid body {i}: {rigid['name']}")
                
            except Exception as e:
                logger.error(f"Failed to import rigid body {i}: {str(e)}")


    def _import_joints(self):
        """Import physics joints/constraints"""
        for joint in self.model['joints']:
            obj = bpy.data.objects.new(f"joint_{joint['name']}", None)
            obj.empty_display_type = 'ARROWS'
            bpy.context.scene.collection.objects.link(obj)
            
            # Set transform
            obj.location = Vector(joint['position']).xzy * self.scale
            obj.rotation_euler = Euler(Vector(joint['rotation']).xzy)
            
            # Create constraint
            rb_const = obj.rigid_body_constraint
            rb_const.type = 'GENERIC_SPRING'
            
            # Set connected rigid bodies
            if joint['rigid_body_a'] in self.rigid_table:
                rb_const.object1 = self.rigid_table[joint['rigid_body_a']]
            if joint['rigid_body_b'] in self.rigid_table:
                rb_const.object2 = self.rigid_table[joint['rigid_body_b']]
                
            # Set joint limits
            self._set_joint_limits(rb_const, joint)

    def _finalize_import(self):
        """Final import steps and cleanup"""
        # Add armature modifier
        arm_mod = self.mesh_obj.modifiers.new(name="Armature", type='ARMATURE')
        arm_mod.object = self.armature_obj
        
        # Ensure objects are visible
        self.armature_obj.hide_viewport = False
        self.armature_obj.hide_render = False
        self.mesh_obj.hide_viewport = False
        self.mesh_obj.hide_render = False
        
        # Set viewport display options
        self.armature_obj.show_in_front = True
        self.armature_obj.data.display_type = 'STICK'
        
        # Set custom normals
        self.mesh_obj.data.use_auto_smooth = True
        self.mesh_obj.data.normals_split_custom_set([Vector(v.normal).xzy for v in self.model.vertices])
        
        # Parent objects
        self.mesh_obj.parent = self.armature_obj
        
        # Select and make active in viewport
        bpy.ops.object.select_all(action='DESELECT')
        self.mesh_obj.select_set(True)
        self.armature_obj.select_set(True)
        bpy.context.view_layer.objects.active = self.armature_obj
        
        # Frame imported objects in viewport
        bpy.ops.view3d.view_selected(use_all_regions=True)
        
        if self.rigid_table:
            physics_empty = bpy.data.objects.new("Physics", None)
            bpy.context.scene.collection.objects.link(physics_empty)
            physics_empty.parent = self.armature_obj
            for rigid in self.rigid_table.values():
                rigid.parent = physics_empty

    def _get_collision_shape(self, shape_type: int) -> str:
        """Convert PMX collision shape type to Blender rigid body shape"""
        shapes = {
            0: 'SPHERE',
            1: 'BOX',
            2: 'CAPSULE'
        }
        return shapes.get(shape_type, 'SPHERE')

    def _set_joint_limits(self, rb_const, joint):
        """Set joint constraint limits"""
        rb_const.use_limit_lin_x = rb_const.use_limit_lin_y = rb_const.use_limit_lin_z = True
        rb_const.use_limit_ang_x = rb_const.use_limit_ang_y = rb_const.use_limit_ang_z = True
        
        # Linear limits
        rb_const.limit_lin_x_lower = joint['position_min'][0] * self.scale
        rb_const.limit_lin_x_upper = joint['position_max'][0] * self.scale
        rb_const.limit_lin_y_lower = joint['position_min'][1] * self.scale
        rb_const.limit_lin_y_upper = joint['position_max'][1] * self.scale
        rb_const.limit_lin_z_lower = joint['position_min'][2] * self.scale
        rb_const.limit_lin_z_upper = joint['position_max'][2] * self.scale
        
        # Angular limits
        rb_const.limit_ang_x_lower = joint['rotation_min'][0]
        rb_const.limit_ang_x_upper = joint['rotation_max'][0]
        rb_const.limit_ang_y_lower = joint['rotation_min'][1]
        rb_const.limit_ang_y_upper = joint['rotation_max'][1]
        rb_const.limit_ang_z_lower = joint['rotation_min'][2]
        rb_const.limit_ang_z_upper = joint['rotation_max'][2]


    def _create_base_objects(self, context: bpy.types.Context) -> None:
        """Create base armature and mesh objects"""
        # Create armature
        armature = bpy.data.armatures.new(name=self.model['name'])
        self.armature_obj = bpy.data.objects.new(self.model['name'], armature)
        context.scene.collection.objects.link(self.armature_obj)
        
        # Create mesh
        mesh = bpy.data.meshes.new(name=f"{self.model['name']}_mesh")
        self.mesh_obj = bpy.data.objects.new(f"{self.model['name']}_mesh", mesh)
        context.scene.collection.objects.link(self.mesh_obj)
        
        # Set active object and mode
        context.view_layer.objects.active = self.armature_obj
        self.armature_obj.select_set(True)
        
        # Initialize armature edit mode
        bpy.ops.object.mode_set(mode='EDIT')
        
        # Return to object mode
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Ensure viewport visibility
        self.armature_obj.hide_viewport = False
        self.mesh_obj.hide_viewport = False
        
        # Set collection visibility
        for collection in self.armature_obj.users_collection:
            collection.hide_viewport = False

def import_pmx(context: bpy.types.Context, filepath: str, **options) -> Set[str]:
    """Import a PMX file into Blender"""
    importer = PMXImporter()
    return importer.execute(context, filepath, **options)