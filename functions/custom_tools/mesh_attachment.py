import bpy
from bpy.types import Operator, Context, Object
from mathutils import Vector
from typing import Set, Optional

from ...core.logging_setup import logger
from ...core.translations import t
from ...core.common import (
    get_active_armature,
    validate_armature,
    get_all_meshes,
    ProgressTracker,
    calculate_bone_orientation,
    add_armature_modifier
)

class AvatarToolkit_OT_AttachMesh(Operator):
    """Attach a mesh to an armature bone with automatic weight setup"""
    bl_idname = "avatar_toolkit.attach_mesh"
    bl_label = t("AttachMesh.label")
    bl_description = t("AttachMesh.desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        armature = get_active_armature(context)
        return armature is not None and context.mode == 'OBJECT' and len(get_all_meshes(context)) > 0

    def execute(self, context: Context) -> Set[str]:
        try:
            logger.info("Starting mesh attachment process")
            
            mesh_name = context.scene.avatar_toolkit.attach_mesh
            armature = get_active_armature(context)
            attach_bone_name = context.scene.avatar_toolkit.attach_bone
            mesh = bpy.data.objects.get(mesh_name)

            with ProgressTracker(context, 10, "Attaching Mesh") as progress:
                # Validation steps
                is_valid, error_msg = validate_mesh_transforms(mesh)
                if not is_valid:
                    raise ValueError(error_msg)
                progress.step(t("AttachMesh.validate_transforms"))

                is_valid, error_msg = validate_mesh_name(armature, mesh_name)
                if not is_valid:
                    raise ValueError(error_msg)
                progress.step(t("AttachMesh.validate_name"))

                # Parent mesh to armature
                mesh.parent = armature
                mesh.parent_type = 'OBJECT'
                progress.step(t("AttachMesh.parent_mesh"))

                # Setup vertex groups
                if mesh.vertex_groups:
                    for vg in mesh.vertex_groups:
                        mesh.vertex_groups.remove(vg)
                
                bpy.ops.object.select_all(action='DESELECT')
                mesh.select_set(True)
                context.view_layer.objects.active = mesh
                
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                vg = mesh.vertex_groups.new(name=mesh_name)
                bpy.ops.object.vertex_group_assign()
                bpy.ops.object.mode_set(mode='OBJECT')
                progress.step(t("AttachMesh.setup_weights"))

                # Create and setup bone
                bpy.ops.object.select_all(action='DESELECT')
                armature.select_set(True)
                context.view_layer.objects.active = armature
                bpy.ops.object.mode_set(mode='EDIT')

                attach_to_bone = armature.data.edit_bones.get(attach_bone_name)
                if not attach_to_bone:
                    raise ValueError(t("AttachMesh.error.bone_not_found", bone=attach_bone_name))

                mesh_bone = armature.data.edit_bones.new(mesh_name)
                mesh_bone.parent = attach_to_bone
                progress.step(t("AttachMesh.create_bone"))

                # Calculate bone placement
                verts_in_group = [v for v in mesh.data.vertices 
                                for g in v.groups if g.group == vg.index]
                dimensions, roll_angle = calculate_bone_orientation(mesh, verts_in_group)
                
                # Set bone position and orientation
                center = Vector((0, 0, 0))
                for v in verts_in_group:
                    center += mesh.data.vertices[v.index].co
                center /= len(verts_in_group)
                
                mesh_bone.head = center
                mesh_bone.tail = center + Vector((0, 0, max(0.1, dimensions.z)))
                mesh_bone.roll = roll_angle
                progress.step(t("AttachMesh.position_bone"))

                bpy.ops.object.mode_set(mode='OBJECT')
                add_armature_modifier(mesh, armature)
                progress.step(t("AttachMesh.add_modifier"))

            logger.info(f"Successfully attached mesh {mesh_name} to bone {attach_bone_name}")
            self.report({'INFO'}, t("AttachMesh.success"))
            return {'FINISHED'}

        except Exception as e:
            logger.error(f"Failed to attach mesh: {str(e)}")
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

def validate_mesh_transforms(mesh):
    """Validate mesh transforms are suitable for attaching."""
    if not mesh:
        return False, "Mesh not found"
    
    # Check for non-uniform scale
    scale = mesh.scale
    if abs(scale[0] - scale[1]) > 0.001 or abs(scale[1] - scale[2]) > 0.001:
        return False, "Mesh has non-uniform scale. Please apply scale (Ctrl+A)"
    
    return True, ""

def validate_mesh_name(armature, mesh_name):
    """Validate mesh name doesn't conflict with existing bones."""
    if mesh_name in armature.data.bones:
        return False, f"Bone named '{mesh_name}' already exists in armature"
    return True, ""