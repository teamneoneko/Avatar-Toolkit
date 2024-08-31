from ast import Dict
from itertools import count
import bpy
import re
from typing import List, Tuple, Optional, TypedDict, Any
from bpy.types import Material, Operator, Context, Object
from ..core.register import register_wrap
from ..core.common import get_selected_armature, is_valid_armature, select_current_armature, get_all_meshes
from ..functions.translations import t

class meshEntry(TypedDict):
    mesh: Object
    shapekeys: list[str]
    vertices: int
    cur_vertex_pass: int
    mesh_shapekeys: dict[str, Object]

@register_wrap
class RemoveDoublesSafely(Operator):
    bl_idname = "avatar_toolkit.remove_doubles_safely"
    bl_label = t("Optimization.remove_doubles_safely.label")
    bl_description = t("Optimization.remove_doubles_safely.desc")
    bl_options = {'REGISTER', 'UNDO'}
    objects_to_do: list[meshEntry] = []
    merge_distance: bpy.props.FloatProperty(default=0.0001)
    advanced: bpy.props.BoolProperty(default=False)

    @classmethod
    def poll(cls, context: Context) -> bool:
        armature = get_selected_armature(context)
        return armature is not None and is_valid_armature(armature)

    def execute(self, context: Context) -> set:
        if not select_current_armature(context):
            self.report({'WARNING'}, t("Optimization.no_armature_selected"))
            return {'CANCELLED'}

        armature = get_selected_armature(context)
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        objects: List[Object] = get_all_meshes(context)
        self.objects_to_do = []

        for mesh in objects:
            if mesh.data.name not in [stored_object["mesh"].data.name for stored_object in self.objects_to_do]:
                print("setting up data for object" + mesh.name)
                mesh_shapekeys = {"mesh":mesh,"shapekeys":[],"vertices":0,"cur_vertex_pass":0,"mesh_shapekeys":{}}
                mesh_data: bpy.types.Mesh = mesh.data
                shape: bpy.types.ShapeKey = None
                mesh_shapekeys["vertices"] = len(mesh_data.vertices)
                bpy.ops.object.mode_set(mode='EDIT')
                mesh_data.vertices.foreach_set("select",[False]*len(mesh_data.vertices))
                bpy.ops.object.mode_set(mode='OBJECT')
                
                if mesh_data.shape_keys:
                    for shape in mesh_data.shape_keys.key_blocks:
                        mesh_shapekeys["shapekeys"].append(shape.name)
                        if self.advanced:
                            bpy.ops.object.mode_set(mode='OBJECT')
                            bpy.ops.object.select_all(action='DESELECT')
                            context.view_layer.objects.active = mesh
                            mesh.select_set(True)
                            mesh.active_shape_key_index = mesh_data.shape_keys.key_blocks.find(shape.name)
                            bpy.ops.object.duplicate()
                            newobj = context.view_layer.objects.active
                            bpy.ops.object.shape_key_move(type='TOP')
                            
                            bpy.ops.object.mode_set(mode='EDIT')
                            bpy.ops.object.mode_set(mode='OBJECT')

                            bpy.ops.object.shape_key_remove(all=True, apply_mix=False)
                            newobj.name = shape.name+"_object_is_"+mesh.name
                            mesh_shapekeys["mesh_shapekeys"][shape.name] = newobj

                            context.view_layer.objects.active = mesh
                            bpy.ops.object.select_all(action='DESELECT')
                print("queued data for "+mesh.name+" is: ")
                print(mesh_shapekeys)
                self.objects_to_do.append(mesh_shapekeys)
        
        return {'FINISHED'}
        
    def invoke(self, context: Context, event: bpy.types.Event) -> set:
        print("starting modal execution of merge doubles safely.")
        self.execute(context)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}
    
    def modify_mesh(self, context: Context, mesh: meshEntry):
        mesh["mesh"].select_set(True)
        context.view_layer.objects.active = mesh["mesh"]
        mesh_data: bpy.types.Mesh = mesh["mesh"].data
        bpy.ops.object.mode_set(mode='EDIT')
        
        bpy.ops.object.mode_set(mode='OBJECT')
        for index, point in enumerate(mesh["mesh"].active_shape_key.points):
            if point.co.xyz != mesh_data.shape_keys.key_blocks[0].points[index].co.xyz:
                mesh_data.vertices[index].select = True
                print("shapekey has a moved vertex at index \""+str(index)+"\", excluding from double merging!")
        bpy.ops.object.mode_set(mode='EDIT')
        
        bpy.ops.object.mode_set(mode='OBJECT')
        mesh["mesh"].select_set(False)
        print("finished shapekey basic.")

    def modify_mesh_advanced(self, context: Context, mesh_entry: meshEntry):
        
        final_merged_vertex_group: list[int] = []
        

        for shapekey_name in mesh_entry["shapekeys"]:
            mesh = mesh_entry["mesh_shapekeys"][shapekey_name]

            

            #make a copy to do double merge testing on for the current vertex
            context.view_layer.objects.active = mesh
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            context.view_layer.objects.active = mesh
            mesh_data: bpy.types.Mesh = mesh.data
            vertices_original: dict[int,Any] = {}
            original_count: int  = len(mesh_data.vertices)
            mesh.select_set(True)
            bpy.ops.object.duplicate()
            mesh = context.view_layer.objects.active
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')

            mesh.select_set(True)
            context.view_layer.objects.active = mesh
            mesh_data: bpy.types.Mesh = mesh.data
            bpy.ops.object.mode_set(mode='EDIT')

            

            bpy.ops.object.mode_set(mode='OBJECT')
            for index, merged_point in enumerate(mesh_data.vertices):
                vertices_original[index] = merged_point.co.xyz
                
                
                #if point.co.xyz != original_mesh_data.shape_keys.key_blocks[0].points[index].co.xyz:
                #    mesh_data.vertices[index].select = True
                #    break
            print("vertex indices and their positions.")
            print(vertices_original)
            print("vertex positions end.")
            bpy.ops.object.mode_set(mode='EDIT')
            mesh_data.vertices.foreach_set("select",[False]*len(mesh_data.vertices))
            bpy.ops.object.mode_set(mode='OBJECT')
            
            select_target_vertex = [False]*len(mesh_data.vertices)
            try:
                select_target_vertex[mesh_entry["cur_vertex_pass"]] = True
            except:
                bpy.ops.object.delete() #remove our double merge testing object for this shapekey, since we merged doubles on it, it will be useless.
                return True
            print("vertex select list:")
            print(select_target_vertex)
            
            
            bpy.ops.object.mode_set(mode='EDIT')
            mesh_data.vertices.foreach_set("select",select_target_vertex)
            bpy.ops.mesh.remove_doubles(threshold=self.merge_distance, use_unselected=True, use_sharp_edge_from_normals=False)
            bpy.ops.object.mode_set(mode='OBJECT')
            #this doesn't keep in mind vertices that are exactly in the same place in the shapekey positional wise that also appear right after one another in the array
            #Based on my internal thoughts and theories, this will cause problems. I don't know the solution to this, so it's fine for now.
            # besides, the chance of this happening should be very very slim, and will require user input to fix. - @989onan
            # {
            # "1":"0,0,0"
            # "2":"0,0,0"  
            # "3":"1,0,0"
            # }

            merged_vertices: list[int] = []

            for i in range(0,original_count):
                if mesh_data.vertices[i+len(merged_vertices)].co.xyz != vertices_original[i]:
                    merged_vertices.append(i)

            #iterate through a copy of final vertex groups to prevent crash. If a vertex was merged before, but didn't merge in this vertex,
            #  then the vertex shouldn't be merged because it moves away from the vertex we are double merging now (ex: bottom of mouth moving away from top when opening on a shapekey) - @989onan
            for merged_point in final_merged_vertex_group[:]:
                if merged_point not in merged_vertices:
                    final_merged_vertex_group.remove(merged_point)
                else:
                    final_merged_vertex_group.append(merged_point)

            bpy.ops.object.mode_set(mode='EDIT')
            mesh_data.vertices.foreach_set("select",[False]*len(mesh_data.vertices))
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.delete() #remove our double merge testing object for this shapekey, since we merged doubles on it, it will be useless.
        context.view_layer.objects.active = mesh_entry["mesh"]
        bpy.ops.object.mode_set(mode='EDIT')
        original_mesh_data: bpy.types.Mesh = mesh_entry["mesh"].data
        select_target_group = [False]*len(mesh_data.vertices)
        for vertex_index in final_merged_vertex_group:
            select_target_group[vertex_index] = True
        original_mesh_data.vertices.foreach_set("select",select_target_group)
        bpy.ops.mesh.remove_doubles(threshold=self.merge_distance, use_unselected=False, use_sharp_edge_from_normals=False)
        mesh_data.vertices.foreach_set("select",[False]*len(mesh_data.vertices))
        bpy.ops.object.mode_set(mode='OBJECT')
        print("finished shapekey advanced.")
        return not (len(final_merged_vertex_group) > 0)

    def modal(self, context: Context, event: bpy.types.Event) -> set:
        if len(self.objects_to_do) > 0:
            bpy.ops.object.select_all(action='DESELECT')
            mesh: meshEntry = self.objects_to_do[0]
            mesh_data: bpy.types.Mesh = mesh["mesh"].data
            if (len(mesh['shapekeys']) > 0) and (not self.advanced):
                shapekeyname: str = mesh['shapekeys'].pop(0)
                
                target_shapekey: int = mesh_data.shape_keys.key_blocks.find(shapekeyname)
                mesh["mesh"].active_shape_key_index = target_shapekey
                print("doing shapekey \""+shapekeyname+"\" on mesh \""+mesh['mesh'].name+"\".")
                self.modify_mesh(context, mesh)
            elif not (mesh_data.shape_keys):
                print("doing mesh with no shapekeys named \""+mesh['mesh'].name+"\".")
                mesh["mesh"].select_set(True)
                context.view_layer.objects.active = mesh["mesh"]
                bpy.ops.object.mode_set(mode='EDIT')
                mesh_data.vertices.foreach_set("select",[False]*len(mesh_data.vertices))
    
                bpy.ops.mesh.select_all(action="INVERT")
                bpy.ops.mesh.remove_doubles(threshold=self.merge_distance,use_unselected=False)

                bpy.ops.object.mode_set(mode='OBJECT')
                mesh["mesh"].select_set(False)
                self.objects_to_do.pop(0)
            elif (not (mesh["cur_vertex_pass"] > mesh["vertices"])) and self.advanced:
                
                print("doing a merge by single vertex index at index "+str(mesh["cur_vertex_pass"]))
                
                if self.modify_mesh_advanced(context, mesh):
                    mesh["cur_vertex_pass"] = mesh["cur_vertex_pass"]+1
            else:
                print("finishing double merge object.")
                if not self.advanced:
                    mesh["mesh"].select_set(True)
                    context.view_layer.objects.active = mesh["mesh"]
                    bpy.ops.object.mode_set(mode='EDIT')

                    bpy.ops.mesh.select_all(action="INVERT")
                    bpy.ops.mesh.remove_doubles(threshold=self.merge_distance,use_unselected=False)
                    
                    bpy.ops.object.mode_set(mode='OBJECT')
                    mesh["mesh"].select_set(False)
                else:
                    mesh["mesh"].select_set(True)
                    context.view_layer.objects.active = mesh["mesh"]
                    bpy.ops.object.mode_set(mode='OBJECT')
                    bpy.ops.object.select_all(action='DESELECT')
                    for obj in mesh["mesh_shapekeys"].values():
                        obj.select_set(True)
                    bpy.ops.object.delete() #delete all objects that were shapekey types.

                self.objects_to_do.pop(0)

                    


        else:
            self.report({'INFO'}, t("Optimization.remove_doubles_completed"))
            print("finishing modal execution of merge doubles safely.")
            return {'FINISHED'}
        
        return {'RUNNING_MODAL'}
