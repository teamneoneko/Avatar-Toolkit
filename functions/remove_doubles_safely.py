import bpy
from typing import List, TypedDict, Any
from bpy.types import Operator, Context, Object
from ..core.common import get_selected_armature, is_valid_armature, select_current_armature, get_all_meshes
from ..core.translations import t

class meshEntry(TypedDict):
    mesh: Object
    shapekeys: list[str]
    vertices: int
    cur_vertex_pass: int


class AvatarToolKit_OT_RemoveDoublesSafelyAdvanced(Operator):
    bl_idname = "avatar_toolkit.remove_doubles_safely_advanced"
    bl_label = t("Optimization.remove_doubles_safely_advanced.label")
    bl_description = t("Optimization.remove_doubles_safely_advanced.desc")
    bl_options = {'REGISTER', 'UNDO'}

    merge_distance: bpy.props.FloatProperty(default=0.0001)

    @classmethod
    def poll(cls, context: Context) -> bool:
        armature = get_selected_armature(context)
        return armature is not None and is_valid_armature(armature)

    def draw(self, context):
        layout = self.layout
        layout.label(text="This process may take a long time.")
        layout.label(text="Blender may seem unresponsive during this operation.")
        layout.label(text="Please be patient and wait for it to complete.")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context: Context):
        bpy.ops.avatar_toolkit.remove_doubles_safely('INVOKE_DEFAULT', advanced=True, merge_distance=self.merge_distance)
        return {'RUNNING_MODAL'}



class AvatarToolKit_OT_RemoveDoublesSafely(Operator):
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
                mesh_shapekeys = {"mesh":mesh,"shapekeys":[],"vertices":0,"cur_vertex_pass":0}
                mesh_data: bpy.types.Mesh = mesh.data
                shape: bpy.types.ShapeKey = None
                mesh_shapekeys["vertices"] = len(mesh_data.vertices)
                bpy.ops.object.mode_set(mode='OBJECT')
                mesh_data.vertices.foreach_set("select",[False]*len(mesh_data.vertices))
                
                if mesh_data.shape_keys:
                    for shape in mesh_data.shape_keys.key_blocks:
                        mesh_shapekeys["shapekeys"].append(shape.name)
                        if self.advanced:
                            bpy.ops.object.mode_set(mode='OBJECT')
                            bpy.ops.object.select_all(action='DESELECT')
                            context.view_layer.objects.active = mesh
                            bpy.ops.object.select_all(action='DESELECT')
                print("queued data for "+mesh.name+" is: ")
                print(mesh_shapekeys)
                self.objects_to_do.append(mesh_shapekeys)
        
        return {'FINISHED'}
        
    def invoke(self, context: Context, event: bpy.types.Event) -> set:
        print("==================")
        print("==================")
        print("==================")
        print("==================")
        print("starting modal execution of merge doubles safely.")
        print("==================")
        print("==================")
        print("==================")
        print("==================")
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
                print("shapekey has a moved vertex at index \""+str(index)+"\", excluding from simple double merging!")
        bpy.ops.object.mode_set(mode='EDIT')
        
        bpy.ops.object.mode_set(mode='OBJECT')
        mesh["mesh"].select_set(False)
        print("finished shapekey basic.")

    def modify_mesh_advanced(self, context: Context, mesh_entry: meshEntry):
        
        final_merged_vertex_group: list[int] = []
        initialized_final: bool = False

        for shapekey_name in mesh_entry["shapekeys"]:
            mesh = mesh_entry["mesh"]

            

            #make a copy to do double merge testing on for the current vertex
            context.view_layer.objects.active = mesh
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            context.view_layer.objects.active = mesh
            mesh_data: bpy.types.Mesh = mesh.data
            vertices_original: dict[int,Any] = {}
            original_count: int  = len(mesh_data.vertices)
            mesh.select_set(True)
            mesh.active_shape_key_index = mesh_data.shape_keys.key_blocks.find(shapekey_name)
            bpy.ops.object.duplicate()
            bpy.ops.object.shape_key_move(type='TOP')
                            
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.object.mode_set(mode='OBJECT')

            bpy.ops.object.shape_key_remove(all=True, apply_mix=False)
            
            mesh = context.view_layer.objects.active
            mesh.name = shapekey_name+"_object_is_"+mesh.name
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')

            mesh.select_set(True)
            context.view_layer.objects.active = mesh
            mesh_data: bpy.types.Mesh = mesh.data
            bpy.ops.object.mode_set(mode='EDIT')

            

            bpy.ops.object.mode_set(mode='OBJECT')
            for index, merged_point in enumerate(mesh_data.vertices):
                vertices_original[index] = merged_point.co.xyz
                
                
            bpy.ops.object.mode_set(mode='OBJECT')
            mesh_data.vertices.foreach_set("select",[False]*len(mesh_data.vertices))
            
            select_target_vertex = [False]*len(mesh_data.vertices)
            try:
                select_target_vertex[mesh_entry["cur_vertex_pass"]] = True
            except:
                bpy.ops.object.delete() #remove our double merge testing object for this shapekey, since we merged doubles on it, it will be useless.
                return True
            
            
            bpy.ops.object.mode_set(mode='OBJECT')
            mesh_data.vertices.foreach_set("select",select_target_vertex)
            bpy.ops.object.mode_set(mode='EDIT')
            for i in range(0,20): #for some reason, if using merge to unselected on a vertex, the vertex will only merge to 1 other vertex. so we gotta spam it to fix it.
                bpy.ops.mesh.remove_doubles(threshold=self.merge_distance, use_unselected=True, use_sharp_edge_from_normals=False)
            bpy.ops.object.mode_set(mode='OBJECT')

            merged_vertices: list[int] = []
            mesh_data_vertices: dict[int,Any] = {}
            for idx,vertex in enumerate(mesh_data.vertices):
                mesh_data_vertices[idx] = vertex.co.xyz
            
            #I'm loosing my mind with indices because I cannot keep so many numbers in my head. I will have to use 2 pointers 
            # yes this can be simplified more, but the mountains of errors with using a normal for statement are making me
            # loose my mind. This is hard. - @989onan
            #Below is the magic that determines whether or not vertices were merged and then puts the vertices
            #that were merged into a list. - @989onan

            i = 0
            j = 0
            while(i<len(vertices_original)):
                if j+1 > len(mesh_data.vertices):
                    merged_vertices.append(i)
                    j = j-1
                elif mesh_data.vertices[j].co.xyz != vertices_original[i]:
                    merged_vertices.append(i)
                    j = j-1
                elif vertices_original[i] == vertices_original[mesh_entry["cur_vertex_pass"]]:
                    merged_vertices.append(i)

                i = i+1
                j = j+1

            

            #give our final set of points some inital data. we're looking for points that are merged on every shape key (and therefore appear in every version of merged_vertices). 
            # If we initialize the array with points from the first version of merged_vertices, then we can remove the vertices from final that don't get merged from
            #every future version of merged_vertices with the "if merged_point not in merged_vertices:" code.
            if initialized_final == False:
                for point in merged_vertices:
                    final_merged_vertex_group.append(point)
                initialized_final = True
            #iterate through a copy of final vertex groups to prevent crash. If a vertex was merged before, but didn't merge in this vertex,
            #  then the vertex shouldn't be merged because it moves away from the vertex we are double merging now (ex: bottom of mouth moving away from top when opening on a shapekey) - @989onan
            for merged_point in final_merged_vertex_group[:]:
                if merged_point not in merged_vertices:
                    final_merged_vertex_group.remove(merged_point)
                
                    

            bpy.ops.object.mode_set(mode='OBJECT')
            mesh_data.vertices.foreach_set("select",[False]*len(mesh_data.vertices))
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.delete() #remove our double merge testing object for this shapekey, since we merged doubles on it, it will be useless.
        context.view_layer.objects.active = mesh_entry["mesh"]
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        context.view_layer.objects.active = mesh_entry["mesh"]
        mesh_entry["mesh"].select_set(True)

        original_mesh_data: bpy.types.Mesh = mesh_entry["mesh"].data
        select_target_group = [False]*len(original_mesh_data.vertices)


        for vertex_index in final_merged_vertex_group:
            select_target_group[vertex_index] = True
        
        bpy.ops.object.mode_set(mode='OBJECT')
        original_mesh_data.vertices.foreach_set("select",select_target_group)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.remove_doubles(threshold=self.merge_distance, use_unselected=False, use_sharp_edge_from_normals=False)
        bpy.ops.object.mode_set(mode='OBJECT')
        original_mesh_data.vertices.foreach_set("select",[False]*len(original_mesh_data.vertices))
        print("finished advanced merge doubles for single vertex at index: "+str(mesh_entry["cur_vertex_pass"]))
        return not (len(final_merged_vertex_group) > 1)

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

                self.objects_to_do.pop(0)

                    


        else:
            self.report({'INFO'}, t("Optimization.remove_doubles_completed"))
            print("finishing modal execution of merge doubles safely.")
            return {'FINISHED'}
        
        return {'RUNNING_MODAL'}
