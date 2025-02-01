import bpy
from mathutils import Vector, Matrix, Euler
from typing import Dict, Optional, List, Tuple, Set
from .logging_setup import logger

class RigidBodyManager:
    """Manages creation and setup of rigid bodies with proper bone parenting"""
    
    def __init__(self, armature_obj: bpy.types.Object, scale: float = 1.0):
        self.armature_obj = armature_obj
        self.scale = scale
        self.rigid_table: Dict[int, bpy.types.Object] = {}
        self.bone_table = armature_obj.pose.bones if armature_obj else []
        self.rigid_body_matrix_map = {}
        self.empty_parent_map = {}
        self.fake_parent_map = {}
        self.non_collision_pairs = set()
        
    def create_rigid_body(self, 
                        name: str,
                        bone_index: int,
                        position: Tuple[float, float, float],
                        rotation: Tuple[float, float, float],
                        shape_type: int,
                        shape_size: Tuple[float, float, float],
                        physics_mode: int,
                        group_id: int,
                        non_collision_group_mask: int,
                        mass: float,
                        friction: float,
                        restitution: float,
                        linear_damping: float,
                        angular_damping: float) -> bpy.types.Object:
        """Create and setup a rigid body with proper bone parenting"""
        try:
            # Create rigid body object
            obj = bpy.data.objects.new(f"rigid_{name}", None)
            obj.empty_display_type = 'SPHERE'
            
            # Ensure object is in the active collection
            context = bpy.context
            if obj.name not in context.collection.objects:
                context.collection.objects.link(obj)
            
            # Set initial transform
            obj.location = Vector(position).xzy * self.scale
            obj.rotation_euler = Euler(Vector(rotation).xzy)
            obj.rotation_mode = 'YXZ'
            
            obj.mmd_type = 'RIGID_BODY'
            
            # Setup bone relationship if valid bone index
            if bone_index >= 0 and bone_index < len(self.bone_table):
                bone = self.bone_table[bone_index]
                self._setup_bone_relationship(obj, bone, physics_mode)
                
            # Set up physics shape and dimensions
            dimensions = Vector(shape_size).xzy * self.scale * 2
            obj.empty_display_size = max(dimensions) if dimensions else 0.1
            obj.scale = dimensions if dimensions else Vector((0.1, 0.1, 0.1))
            
            # Add rigid body physics with proper context
            view_layer = context.view_layer
            view_layer.objects.active = obj
            obj.select_set(True)
            
            with context.temp_override(active_object=obj, selected_objects=[obj]):
                bpy.ops.rigidbody.object_add(type='ACTIVE')
                
            # Configure rigid body properties
            rb = obj.rigid_body
            rb.type = 'ACTIVE' if physics_mode == 0 else 'PASSIVE'
            rb.collision_shape = self._get_collision_shape(shape_type)
            rb.mass = max(0.001, mass)
            rb.friction = max(0, min(1, friction))
            rb.restitution = max(0, min(1, restitution))
            rb.linear_damping = linear_damping
            rb.angular_damping = angular_damping
            rb.collision_collections[0] = True
            rb.collision_collections[group_id + 1] = True
            
            # Set collision masks
            for i in range(16):
                rb.collision_collections[i] = (non_collision_group_mask & (1 << i)) == 0
            
            if rb.type == 'PASSIVE':
                rb.kinematic = True
                
            logger.debug(f"Successfully created rigid body: {obj.name}")
            return obj
            
        except Exception as e:
            logger.error(f"Failed to create rigid body {name}: {str(e)}")
            raise

    def _ensure_context_collection(self, obj: bpy.types.Object):
        """Ensure object is in the correct collection"""
        for collection in bpy.data.collections:
            if obj.name in collection.objects:
                return
        bpy.context.scene.collection.objects.link(obj)

    def _setup_bone_relationship(self, obj: bpy.types.Object, bone: bpy.types.PoseBone, physics_mode: int):
        """Setup proper bone relationship based on physics mode"""
        if physics_mode == 0:  # Static
            self._setup_static_bone_parenting(obj, bone)
        elif physics_mode == 1:  # Dynamic
            self._setup_dynamic_bone_tracking(obj, bone)
        else:  # Dynamic with bone influence
            self._setup_dynamic_bone_influence(obj, bone)
            
    def _setup_static_bone_parenting(self, obj: bpy.types.Object, bone: bpy.types.PoseBone):
        """Setup static rigid body parenting to bone"""
        m = bone.matrix @ bone.bone.matrix_local.inverted()
        self.rigid_body_matrix_map[obj] = m
        
        obj.parent = self.armature_obj
        obj.parent_type = 'BONE'
        obj.parent_bone = bone.name
        obj.matrix_world = self.armature_obj.matrix_world @ m
        
    def _setup_dynamic_bone_tracking(self, obj: bpy.types.Object, bone: bpy.types.PoseBone):
        """Setup dynamic rigid body with bone tracking"""
        m = bone.matrix @ bone.bone.matrix_local.inverted()
        self.rigid_body_matrix_map[obj] = m
        t, r, s = (m @ obj.matrix_local).decompose()
        obj.location = t
        obj.rotation_euler = r.to_euler(obj.rotation_mode)
        
        empty = bpy.data.objects.new(name=f"track_{bone.name}", object_data=None)
        empty.empty_display_type = 'ARROWS'
        empty.empty_display_size = 0.1
        bpy.context.scene.collection.objects.link(empty)
        empty.matrix_world = bone.matrix
        empty.mmd_type = "TRACK_TARGET"
        empty.hide_viewport = True
        
        self.empty_parent_map[empty] = obj
        
        const = bone.constraints.new('COPY_TRANSFORMS')
        const.name = "mmd_tools_rigid_track"
        const.target = empty
        const.influence = 1.0
        
    def _setup_dynamic_bone_influence(self, obj: bpy.types.Object, bone: bpy.types.PoseBone):
        """Setup dynamic rigid body with bone influence"""
        self._setup_dynamic_bone_tracking(obj, bone)
        
        const = bone.constraints["mmd_tools_rigid_track"]
        const.influence = 0.5
        
    def create_non_collision_constraints(self, distance_scale: float = 1.5):
        """Create non-collision constraints between rigid bodies"""
        non_collision_pairs = []
        
        for obj_a in self.rigid_table.values():
            rb_a = obj_a.rigid_body
            for obj_b in self.rigid_table.values():
                if obj_a == obj_b:
                    continue
                    
                rb_b = obj_b.rigid_body
                if not (rb_a and rb_b):
                    continue
                    
                pair = frozenset((obj_a, obj_b))
                if pair in self.non_collision_pairs:
                    continue
                    
                distance = (obj_a.location - obj_b.location).length
                range_check = distance < distance_scale * (obj_a.empty_display_size + obj_b.empty_display_size) * 0.5
                
                if range_check:
                    non_collision_pairs.append((obj_a, obj_b))
                    self.non_collision_pairs.add(pair)
                    
        for obj_a, obj_b in non_collision_pairs:
            self._create_non_collision_constraint(obj_a, obj_b)
            
    def _create_non_collision_constraint(self, obj_a: bpy.types.Object, obj_b: bpy.types.Object):
        """Create individual non-collision constraint"""
        ncc = bpy.data.objects.new(name="ncc", object_data=None)
        ncc.empty_display_type = 'ARROWS'
        ncc.location = (0, 0, 0)
        bpy.context.scene.collection.objects.link(ncc)
        ncc.hide_viewport = True
        
        bpy.ops.rigidbody.constraint_add(type='GENERIC')
        rb_const = ncc.rigid_body_constraint
        rb_const.disable_collisions = True
        rb_const.object1 = obj_a
        rb_const.object2 = obj_b
        
        return ncc
        
    def _get_collision_shape(self, shape_type: int) -> str:
        """Convert collision shape type to Blender rigid body shape"""
        shapes = {
            0: 'SPHERE',
            1: 'BOX',
            2: 'CAPSULE'
        }
        return shapes.get(shape_type, 'SPHERE')
        
    def create_physics_container(self) -> bpy.types.Object:
        """Create empty object to contain physics objects"""
        physics_empty = bpy.data.objects.new("Physics", None)
        bpy.context.scene.collection.objects.link(physics_empty)
        physics_empty.parent = self.armature_obj
        return physics_empty
        
    def cleanup(self):
        """Clean up temporary objects and constraints"""
        for empty in self.empty_parent_map.keys():
            if empty.name in bpy.data.objects:
                bpy.data.objects.remove(empty, do_unlink=True)
                
        self.empty_parent_map.clear()
        self.rigid_body_matrix_map.clear()
        self.non_collision_pairs.clear()
