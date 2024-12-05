import bpy
import numpy as np
from typing import List, TypedDict, Any, Literal, TypeAlias, cast
from bpy.types import Operator, Context, Object, Event
from ...core.logging_setup import logger
from ...core.translations import t
from ...core.common import (
    get_active_armature,
    get_all_meshes,
    validate_armature
)

# Constants
MERGE_ITERATION_COUNT = 20
MERGE_DISTANCE_DEFAULT = 0.0001

# Type definitions
ModalReturnType: TypeAlias = Literal['RUNNING_MODAL', 'FINISHED', 'CANCELLED']

class MeshEntry(TypedDict):
    mesh: Object
    shapekeys: list[str]
    vertices: int
    cur_vertex_pass: int

def create_duplicate_for_merge(context: Context, mesh: Object, shapekey_name: str) -> Object:
    """Creates a duplicate mesh object for merge testing"""
    context.view_layer.objects.active = mesh
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    mesh.select_set(True)
    bpy.ops.object.duplicate()
    bpy.ops.object.shape_key_move(type='TOP')
    
    duplicate = context.view_layer.objects.active
    duplicate.name = f"{shapekey_name}_object_is_{mesh.name}"
    return duplicate

def process_vertex_merging(mesh_data: bpy.types.Mesh, vertices_original: dict[int, Any], current_vertex: int) -> list[int]:
    """Process vertex merging and return merged vertex indices"""
    merged_vertices = []
    i, j = 0, 0
    
    while i < len(vertices_original):
        if j + 1 > len(mesh_data.vertices):
            merged_vertices.append(i)
            j = j - 1
        elif mesh_data.vertices[j].co.xyz != vertices_original[i]:
            merged_vertices.append(i)
            j = j - 1
        elif vertices_original[i] == vertices_original[current_vertex]:
            merged_vertices.append(i)
        i, j = i + 1, j + 1
    
    return merged_vertices

class AvatarToolkit_OT_RemoveDoublesAdvanced(Operator):
    bl_idname = "avatar_toolkit.remove_doubles_advanced"
    bl_label = t("Optimization.remove_doubles_advanced")
    bl_description = t("Optimization.remove_doubles_advanced_desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        """Check if the operator can be executed"""
        armature = get_active_armature(context)
        if not armature:
            return False
        valid, _ = validate_armature(armature)
        return valid

    def execute(self, context: Context) -> set[str]:
        """Execute the advanced remove doubles operator"""
        context.scene.avatar_toolkit.remove_doubles_advanced = True
        bpy.ops.avatar_toolkit.remove_doubles('INVOKE_DEFAULT')
        return {'RUNNING_MODAL'}

class AvatarToolkit_OT_RemoveDoubles(Operator):
    bl_idname = "avatar_toolkit.remove_doubles"
    bl_label = t("Optimization.remove_doubles")
    bl_description = t("Optimization.remove_doubles_desc")
    bl_options = {'REGISTER', 'UNDO'}

    objects_to_do: list[MeshEntry] = []

    @classmethod
    def poll(cls, context: Context) -> bool:
        """Check if the operator can be executed"""
        armature = get_active_armature(context)
        if not armature:
            return False
        valid, _ = validate_armature(armature)
        return valid

    def draw(self, context: Context) -> None:
        """Draw the operator's UI"""
        layout = self.layout
        layout.prop(context.scene.avatar_toolkit, "remove_doubles_merge_distance")
        layout.label(text=t("Optimization.remove_doubles_warning"))
        layout.label(text=t("Optimization.remove_doubles_wait"))

    def invoke(self, context: Context, event: Event) -> set[str]:
        """Initialize the operator"""
        logger.info("Starting modal execution of merge doubles safely")
        return context.window_manager.invoke_props_dialog(self)

    def setup_mesh_entry(self, mesh: Object) -> MeshEntry:
        """Set up mesh entry data structure"""
        mesh_entry: MeshEntry = {
            "mesh": mesh,
            "shapekeys": [],
            "vertices": len(mesh.data.vertices),
            "cur_vertex_pass": 0
        }
        
        if mesh.data.shape_keys:
            mesh_entry["shapekeys"] = [shape.name for shape in mesh.data.shape_keys.key_blocks]
        
        return mesh_entry

    def execute(self, context: Context) -> set[str]:
        """Execute the remove doubles operator"""
        try:
            armature = get_active_armature(context)
            if not armature:
                self.report({'WARNING'}, t("Optimization.no_armature"))
                return {'CANCELLED'}

            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')

            objects = get_all_meshes(context)
            self.objects_to_do = []

            for mesh in objects:
                if mesh.data.name not in [obj["mesh"].data.name for obj in self.objects_to_do]:
                    logger.debug(f"Setting up data for object {mesh.name}")
                    mesh_entry = self.setup_mesh_entry(mesh)
                    self.objects_to_do.append(mesh_entry)

            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
            
        except Exception as e:
            logger.error(f"Error in execute: {str(e)}")
            return {'CANCELLED'}

    def modify_mesh(self, context: Context, mesh: MeshEntry) -> None:
        """Basic mesh modification for simple cases"""
        try:
            mesh["mesh"].select_set(True)
            context.view_layer.objects.active = mesh["mesh"]
            mesh_data = mesh["mesh"].data
            
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.object.mode_set(mode='OBJECT')
            
            # Select vertices with different positions in shape keys
            for index, point in enumerate(mesh["mesh"].active_shape_key.points):
                if point.co.xyz != mesh_data.shape_keys.key_blocks[0].points[index].co.xyz:
                    mesh_data.vertices[index].select = True
                    logger.debug(f"Shapekey has moved vertex at index {index}")
                    
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.object.mode_set(mode='OBJECT')
            mesh["mesh"].select_set(False)
            
        except Exception as e:
            logger.error(f"Error in modify_mesh: {str(e)}")

    def modify_mesh_advanced(self, context: Context, mesh_entry: MeshEntry) -> bool:
        """Advanced mesh modification with shape key handling"""
        try:
            final_merged_vertex_group = []
            initialized_final = False
            merge_distance = context.scene.avatar_toolkit.remove_doubles_merge_distance

            for shapekey_name in mesh_entry["shapekeys"]:
                duplicate = create_duplicate_for_merge(context, mesh_entry["mesh"], shapekey_name)
                vertices_original = {i: v.co.xyz for i, v in enumerate(duplicate.data.vertices)}
                
                # Process merging
                merged_vertices = process_vertex_merging(duplicate.data, vertices_original, mesh_entry["cur_vertex_pass"])
                
                if not initialized_final:
                    final_merged_vertex_group = merged_vertices.copy()
                    initialized_final = True
                else:
                    final_merged_vertex_group = [v for v in final_merged_vertex_group if v in merged_vertices]
                
                bpy.ops.object.delete()

            # Apply final merging
            if final_merged_vertex_group:
                self.apply_final_merging(context, mesh_entry, final_merged_vertex_group, merge_distance)
                
            return not (len(final_merged_vertex_group) > 1)
            
        except Exception as e:
            logger.error(f"Error in modify_mesh_advanced: {str(e)}")
            return True

    def apply_final_merging(self, context: Context, mesh_entry: MeshEntry, vertex_group: list[int], merge_distance: float) -> None:
        """Apply final vertex merging operations"""
        mesh = mesh_entry["mesh"]
        context.view_layer.objects.active = mesh
        mesh.select_set(True)
        
        bpy.ops.object.mode_set(mode='OBJECT')
        select_target_group = [False] * len(mesh.data.vertices)
        for vertex_index in vertex_group:
            select_target_group[vertex_index] = True
            
        mesh.data.vertices.foreach_set("select", select_target_group)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.remove_doubles(threshold=merge_distance, use_unselected=False)
        bpy.ops.object.mode_set(mode='OBJECT')

    def process_simple_mesh(self, context: Context, mesh: MeshEntry, merge_distance: float) -> None:
        """Process mesh without shapekeys using simple merge operation"""
        logger.debug(f"Processing mesh without shapekeys: {mesh['mesh'].name}")
        mesh["mesh"].select_set(True)
        context.view_layer.objects.active = mesh["mesh"]
        bpy.ops.object.mode_set(mode='EDIT')
        mesh["mesh"].data.vertices.foreach_set("select", [False] * len(mesh["mesh"].data.vertices))

        bpy.ops.mesh.select_all(action="INVERT")
        bpy.ops.mesh.remove_doubles(threshold=merge_distance, use_unselected=False)
        bpy.ops.object.mode_set(mode='OBJECT')
        mesh["mesh"].select_set(False)

    def finish_mesh_processing(self, context: Context, mesh: MeshEntry, advanced: bool, merge_distance: float) -> None:
        """Complete the mesh processing by performing final merge operations"""
        logger.debug("Finishing mesh processing")
        
        if not advanced:
            mesh["mesh"].select_set(True)
            context.view_layer.objects.active = mesh["mesh"]
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action="INVERT")
            bpy.ops.mesh.remove_doubles(threshold=merge_distance, use_unselected=False)
            
            bpy.ops.object.mode_set(mode='OBJECT')
            mesh["mesh"].select_set(False)

    def modal(self, context: Context, event: Event) -> set[ModalReturnType]:
        """Modal operator execution"""
        try:
            if not self.objects_to_do:
                self.report({'INFO'}, t("Optimization.remove_doubles_completed"))
                logger.info("Finishing modal execution of merge doubles safely")
                return {'FINISHED'}

            mesh = self.objects_to_do[0]
            mesh_data = mesh["mesh"].data
            advanced = context.scene.avatar_toolkit.remove_doubles_advanced
            merge_distance = context.scene.avatar_toolkit.remove_doubles_merge_distance

            if len(mesh['shapekeys']) > 0 and not advanced:
                shapekeyname = mesh['shapekeys'].pop(0)
                mesh["mesh"].active_shape_key_index = mesh_data.shape_keys.key_blocks.find(shapekeyname)
                logger.debug(f"Processing shapekey {shapekeyname}")
                self.modify_mesh(context, mesh)
                
            elif not mesh_data.shape_keys:
                self.process_simple_mesh(context, mesh, merge_distance)
                self.objects_to_do.pop(0)
                
            elif not (mesh["cur_vertex_pass"] > mesh["vertices"]) and advanced:
                if self.modify_mesh_advanced(context, mesh):
                    mesh["cur_vertex_pass"] += 1
                    
            else:
                self.finish_mesh_processing(context, mesh, advanced, merge_distance)
                self.objects_to_do.pop(0)

            return {'RUNNING_MODAL'}
            
        except Exception as e:
            logger.error(f"Error in modal: {str(e)}")
            return {'CANCELLED'}
