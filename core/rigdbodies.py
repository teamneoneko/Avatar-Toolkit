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
            
            # Custom properties
            obj["is_rigid_body"] = True
            obj["rigid_type"] = "RIGID_BODY"
            
            # Get context and collection management
            context = bpy.context
            
            physics_collection = bpy.data.collections.get("Physics")
            if not physics_collection:
                physics_collection = bpy.data.collections.new("Physics")
                context.scene.collection.children.link(physics_collection)
            
            physics_collection.objects.link(obj)
            
            obj.location = Vector(position).xzy * self.scale
            obj.rotation_euler = Euler(Vector(rotation).xzy)
            obj.rotation_mode = 'YXZ'
            
            dimensions = Vector(shape_size).xzy * self.scale * 2
            obj.empty_display_size = max(dimensions) if dimensions else 0.1
            obj.scale = dimensions if dimensions else Vector((0.1, 0.1, 0.1))
            
            # Setup bone relationship if valid bone index
            if bone_index >= 0 and bone_index < len(self.bone_table):
                bone = self.bone_table[bone_index]
                if bone and bone.name:
                    try:
                        safe_bone_name = bone.name
                        logger.debug(f"Parenting rigid body to bone: {safe_bone_name}")
                        self._setup_bone_relationship(obj, bone, physics_mode)
                        self.rigid_table[obj.name] = obj

                    except Exception as e:
                        logger.error(f"Failed to setup bone relationship: {str(e)}")
            
            # Ensure rigid body world exists
            if not context.scene.rigidbody_world:
                bpy.ops.rigidbody.world_add()
            
            # Try to create the rigid body using a direct approach
            try:
                prev_active = context.view_layer.objects.active
                prev_selected = context.selected_objects.copy()
                
                bpy.ops.object.select_all(action='DESELECT')
                obj.select_set(True)
                context.view_layer.objects.active = obj
                
                bpy.ops.rigidbody.object_add(type='ACTIVE')
                
                if obj.rigid_body:
                    rb = obj.rigid_body
                    rb.type = 'ACTIVE' if physics_mode == 0 else 'PASSIVE'
                    rb.collision_shape = self._get_collision_shape(shape_type)
                    rb.mass = max(0.001, mass)
                    rb.friction = max(0, min(1, friction))
                    rb.restitution = max(0, min(1, restitution))
                    rb.linear_damping = linear_damping
                    rb.angular_damping = angular_damping
                    rb.collision_collections[0] = True
                    
                    for i in range(16):
                        rb.collision_collections[i] = False
                    rb.collision_collections[0] = True
                    rb.collision_collections[group_id + 1] = True
                    
                    for i in range(16):
                        collision_with_group = ((non_collision_group_mask & (1 << i)) == 0)
                        rb.collision_collections[i] = collision_with_group
                    
                    if rb.type == 'PASSIVE':
                        rb.kinematic = True
                    
                    logger.debug(f"Successfully created rigid body: {obj.name}")
                else:
                    logger.warning(f"Could not create rigid body for {obj.name}, continuing without physics")
                
                bpy.ops.object.select_all(action='DESELECT')
                for o in prev_selected:
                    o.select_set(True)
                context.view_layer.objects.active = prev_active
                
            except Exception as e:
                logger.warning(f"Could not create rigid body using operator: {str(e)}")
                # Try an alternative approach - add to rigid body world collection directly really we should not need this once we get the other method 100%.
                if context.scene.rigidbody_world and context.scene.rigidbody_world.collection:
                    if obj.name not in context.scene.rigidbody_world.collection.objects:
                        context.scene.rigidbody_world.collection.objects.link(obj)
            
            return obj
            
        except Exception as e:
            logger.error(f"Failed to create rigid body {name} | Error: {str(e)}")
            logger.debug(f"Stack trace: ", exc_info=True)
            return None

    def _setup_dynamic_bone_tracking(self, obj: bpy.types.Object, bone: bpy.types.PoseBone):
        """Setup dynamic rigid body with bone tracking"""
        try:
            # Calculate transformation
            m = bone.matrix @ bone.bone.matrix_local.inverted()
            self.rigid_body_matrix_map[obj] = m
            
            # Decompose matrix for location and rotation
            t, r, s = (m @ obj.matrix_local).decompose()
            obj.location = t
            obj.rotation_euler = r.to_euler(obj.rotation_mode)
            
            empty_name = f"track_{bone.name}"
            
            old_empty = bpy.data.objects.get(empty_name)
            if old_empty:
                bpy.data.objects.remove(old_empty, do_unlink=True)
            
            empty = bpy.data.objects.new(name=empty_name, object_data=None)
            empty.empty_display_type = 'ARROWS'
            empty.empty_display_size = 0.1
            
            physics_collection = bpy.data.collections.get("Physics")
            if physics_collection:
                physics_collection.objects.link(empty)
            else:
                bpy.context.scene.collection.objects.link(empty)
                
            empty.matrix_world = bone.matrix
            
            # Set tracking type using custom property and store it
            empty["mmd_type"] = "TRACK_TARGET"
            empty.hide_viewport = True
            self.empty_parent_map[empty] = obj
            
            if "mmd_tools_rigid_track" in bone.constraints:
                bone.constraints.remove(bone.constraints["mmd_tools_rigid_track"])
                
            const = bone.constraints.new('COPY_TRANSFORMS')
            const.name = "mmd_tools_rigid_track"
            const.target = empty
            const.influence = 1.0
            
            logger.debug(f"Successfully setup dynamic tracking for {obj.name} with {empty.name}")
            
        except Exception as e:
            logger.error(f"Failed to setup dynamic bone tracking: {str(e)}")

    def _create_non_collision_constraint(self, obj_a: bpy.types.Object, obj_b: bpy.types.Object):
        """Create individual non-collision constraint"""
        ncc = bpy.data.objects.new(name="ncc", object_data=None)
        ncc.empty_display_type = 'ARROWS'
        ncc.location = (0, 0, 0)
        bpy.context.scene.collection.objects.link(ncc)
        ncc.hide_viewport = True
        
        # Use proper context to add constraint
        context = bpy.context
        prev_active = context.view_layer.objects.active
        context.view_layer.objects.active = ncc
        
        try:
            with context.temp_override(active_object=ncc):
                bpy.ops.rigidbody.constraint_add(type='GENERIC')
        except (RuntimeError, AttributeError):
            # Fallback for older Blender versions
            override = context.copy()
            override["active_object"] = ncc
            bpy.ops.rigidbody.constraint_add(override, type='GENERIC')
            
        context.view_layer.objects.active = prev_active
        
        # Configure constraint
        if hasattr(ncc, 'rigid_body_constraint') and ncc.rigid_body_constraint:
            rb_const = ncc.rigid_body_constraint
            rb_const.disable_collisions = True
            rb_const.object1 = obj_a
            rb_const.object2 = obj_b
        
        return ncc

    def _ensure_context_collection(self, obj: bpy.types.Object):
        """Ensure object is in the correct collection"""
        for collection in bpy.data.collections:
            if obj.name in collection.objects:
                return
        bpy.context.scene.collection.objects.link(obj)

    def _setup_bone_relationship(self, obj: bpy.types.Object, bone: bpy.types.PoseBone, physics_mode: int):
        """Setup proper bone relationship based on physics mode"""
        try:
            # Log the setup attempt
            logger.debug(f"Setting up bone relationship for {obj.name} to bone {bone.name} with mode {physics_mode}")
            
            if physics_mode == 0:  # Static
                self._setup_static_bone_parenting(obj, bone)
            elif physics_mode == 1:  # Dynamic
                self._setup_dynamic_bone_tracking(obj, bone)
            else:  # Dynamic with bone influence
                self._setup_dynamic_bone_influence(obj, bone)
                
        except Exception as e:
            logger.error(f"Failed to setup bone relationship: {str(e)}")
            # Continue without failing the entire import

    def _setup_static_bone_parenting(self, obj: bpy.types.Object, bone: bpy.types.PoseBone):
        """Setup static rigid body parenting to bone"""
        try:
            # Calculate transformation matrix
            m = bone.matrix @ bone.bone.matrix_local.inverted()
            self.rigid_body_matrix_map[obj] = m
            
            # First unparent the object if it has a parent
            old_parent = obj.parent
            if old_parent:
                # Store the world matrix
                world_matrix = obj.matrix_world.copy()
                # Clear parent
                obj.parent = None
                # Restore world position
                obj.matrix_world = world_matrix
            
            # Set proper parent and keep transform
            obj.parent = self.armature_obj
            obj.parent_type = 'BONE'
            obj.parent_bone = bone.name
            
            # Update matrix
            obj.matrix_world = self.armature_obj.matrix_world @ m
            
            logger.debug(f"Successfully parented {obj.name} to bone {bone.name}")
            
        except Exception as e:
            logger.error(f"Failed to setup static bone parenting: {str(e)}")
        
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
