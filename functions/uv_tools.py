from typing import TypedDict
import bpy
from bpy.types import Operator, Object, Context, Mesh, MeshUVLoopLayer
import bmesh
import numpy as np
import math
from ..core.translations import t

class GenerateLoopTreeResult(TypedDict):
    tree: dict[str, set[str]]
    selected_loops: dict[str,list[int]]
    selected_verts: dict[str,int]


class AvatarToolkit_OT_AlignUVEdgesToTarget(Operator):
    bl_idname = "avatar_toolkit.align_uv_edges_to_target"
    bl_label = t("avatar_toolkit.align_uv_edges_to_target.label")
    bl_description = t("avatar_toolkit.align_uv_edges_to_target.desc")
    bl_options = {'REGISTER', 'UNDO'}



    #all selected objects need to be meshes for this to work - @989onan
    @classmethod
    def poll(cls, context: Context):
        if not ((context.view_layer.objects.active is not None) and (len(context.view_layer.objects.selected) > 0)):
            return False
        if context.mode != "EDIT_MESH":
            return False
        for obj in context.view_layer.objects.selected:
            if obj.type != "MESH":
                return False
        if not context.space_data:
            return False
        if not context.space_data.show_uvedit:
            return False
        if context.scene.tool_settings.use_uv_select_sync:
            return False
        return True

    def execute(self, context: Context):
        
        
        target: str = context.view_layer.objects.active.name #The object which we want to align every other selected object's selected UV vertex line to
        
        sources: list[str] = [i.name for i in context.view_layer.objects.selected] #The objects which we want to align their selected UV lines to the target's UV line
        
        prev_mode: str = bpy.context.object.mode
        bpy.ops.object.mode_set(mode='OBJECT')
        
        
        def generate_loop_tree(obj_name: str) -> GenerateLoopTreeResult:
            print("Finding selected line for: \""+obj_name+"\"!")
            
            
            vert_target_loops: dict[str,list[int]] = {}
            vert_target_verts: dict[str,int] = {}
            
            me: Mesh = bpy.data.objects[obj_name].data
            uv_lay: MeshUVLoopLayer = me.uv_layers.active
            bm: bmesh.types.BMesh = bmesh.new()
            bm.from_mesh(me)
            bm.verts.ensure_lookup_table()

            

            # To explain:
            # So loops in UV maps are X polygons that make up a face (So a MeshLoop represent a face and each vertex on that face is in order)
            # 
            # For some preknowledge:
            # When a mesh is UV unwrapped, if a vertice is shared by two different faces on the model in the viewport and the vertice of both faces are in
            # the same position on the UV map, then it considers it one point and the user can move it 
            # (is why the uv map doesn't split apart when you try to move a vertex because that would be annoying)
            # 
            # The problem:
            # The problem is that the data for whether the uv corners of two faces that share a vertex physically being connected and selected as one vertex on the uv map does not exist
            # Though thankfully, blender forcibly (whether you like it or not) merges vertices of a uv map if the vertex of two different faces are actually shared in the UI,
            # allowing for the moving of vertices of 4 faces connected by a single vertex. Behavior every normal blender user is familiar with. 
            # 
            # The solution
            # We can use this to our advantage, by finding vertices on the uv map that share the same coridinate as another vertex that is also selected.
            # that way we can group each pair shared in a line as the same vertex, and identify the line using these pairs and using the data that says for certain
            # that two vertices share the same face loop, and therefore are connected.

            #hmmm real stupid grimlin hours with this one. Using a string as the index of a dictionary of loop corners that end up on the same coordinate
            
            for k,i in enumerate(uv_lay.vertex_selection): #go through the selected vertices on object.
                if (i.value == True) and (bm.verts[me.loops[k].vertex_index].select == True) and (bm.verts[me.loops[k].vertex_index].hide == False): #filter out vertices that are hidden from UV port
                    key = np.array(uv_lay.uv[k].vector[:])
                    key = key.round(decimals=5) #make a key that is the position of a selected vertex
                    
                    if str(key) not in vert_target_loops:
                        vert_target_loops[str(key)] = [] #if the vertex's position is not a list yet, add it.
                    vert_target_loops[str(key)].append(k) #Basically, group vertices based on their position on a UV map as a list.
                    vert_target_verts[str(key)] = me.loops[k].vertex_index #associate the index of the physical vertex in real space with the coordinate of the uv vertices that share a position (Basically associate UV vert with real vert)
            if len(vert_target_loops) > 4000: #This usually indicates that the user has a bunch of crap selected.
                self.report({'WARNING'}, t("UVTools.align_uv_to_target.warning.too_much"))
                return
            print("Finding connections on line for \""+obj_name+"\"!")
            me.validate()
            
            bm = bmesh.new()
            bm.from_mesh(me)
            
            
            #print(vert_target_loops)
            #print(vert_target_verts)
            tree: dict[str, set[str]] = {}
            selected_verts = np.hstack(list(vert_target_loops.values()))
            #print(selected_verts)
            bm.verts.ensure_lookup_table()
            for uvcoordsstr in vert_target_loops:
                
                uv_lay = me.uv_layers.active
                

                #before this section, each vert_target_loops is just groupings of vertices that share coordinates.
                # Using the data that determines UV face corners (uvloops) that are associated with the real vertex, 
                # and the uv face corners (loops) that are on the same faces as the vertices that share coordinates in 
                # vert_target_loops, we can now identify them
                #TL;DR: pairs of vertices that share cooridinates (chain links) find their buddies (make chain connected) 

                # Someone explain this better than me if you can please - @989onan
                extension_loops = []
                loops = bm.verts[vert_target_verts[uvcoordsstr]].link_loops 
                loops_indexes = [i.index for i in loops]
                for loop in vert_target_loops[uvcoordsstr]:
                    if loop in loops_indexes:
                        loop_obj = loops[loops_indexes.index(loop)]
                        extension_loops.append(loop_obj.link_loop_next.index)
                        extension_loops.append(loop_obj.link_loop_prev.index)
                
                
                
                
                
                #make a tree out of the vertices we identified as sharing faces with the vertices in vert_target_loops, and then link them together in a dictionary.
                #the order of this dictionary is unknown.
                # Someone explain this better than me if you can please - @989onan
                tree[uvcoordsstr] = set()
                
                for i in extension_loops:
                    if i in selected_verts:
                        key = np.array(uv_lay.uv[i].vector[:])
                        key = key.round(decimals=5)
                        tree[uvcoordsstr].add(str(key))
                       
                if uvcoordsstr in tree:
                    if len(tree[uvcoordsstr]) > 2:
                        self.report({'WARNING'}, t("UVTools.align_uv_to_target.warning.need_a_line").format(obj=obj_name))
                        return {'FINISHED'}
            
            uv_lay = me.uv_layers.active
            for uvcoordstr in vert_target_loops:
                for loop in vert_target_loops[uvcoordstr]:
                    uv_lay.vertex_selection[loop].value = True

            
            bm.free()
            me.validate()
            print("found UV line connections for \""+obj_name+"\":")
            #print(tree)
            
            return {"tree":tree,"selected_loops":vert_target_loops,"selected_verts":vert_target_verts}
        
        

        #This function uses the previous point to find the next point based on connected loops and faces.
        def sort_uv_tree(originaltree: dict[str, set[str]], obj_name: str):
            sortedtree: dict[str, set[str]] = originaltree.copy()
            startpoints: list[str] = []
            for i in sortedtree:
                if len(sortedtree[i]) < 2:
                    startpoints.append(i)

            if len(startpoints) != 2:
                self.report({'WARNING'}, t("UVTools.align_uv_to_target.warning.need_a_line").format(obj=obj_name))
                return
            
            a_list1 = startpoints[0].replace(", "," ").replace("[","").replace("]","").split()
            map_object1 = map(float, a_list1)
            uvcoords1 = list(map_object1)
            a_list2 = startpoints[1].replace(", "," ").replace("[","").replace("]","").split()
            map_object2 = map(float, a_list2)
            uvcoords2 = list(map_object2)
            
            cursor = context.space_data.cursor_location
            
            startpoint = None
            if math.sqrt(  (((uvcoords1[0])  -  (cursor[0]))  **2)  +  (((uvcoords1[1])  -  (cursor[1]))  **2)  )    >    math.sqrt(  (((uvcoords2[0])  -  (cursor[0]))  **2)  +  (((uvcoords2[1])  -  (cursor[1]))  **2)  ):
                startpoint = startpoints[0]
            else:
                startpoint = startpoints[1]
            
            #Wew my first actual recursive sort! - @989onan
            def recursive_sort_uv_tree(point: str, sortedfinal: list[str]):
                #print("appending "+point)
                sortedfinal.append(point)
                
                new_point: str = ""
                for i in sortedtree:
                    if point in sortedtree[i]:
                        new_point = i
                        removed_value = sortedtree.pop(i)
                        #print(removed_value)
                        break
                        
                if new_point == "":
                    print("BROKE OUT OF SORTING, FINAL TREE (Should be empty, if not you errored here!):")
                    print(sortedtree)
                    
                    return sortedfinal
                
                return recursive_sort_uv_tree(new_point, sortedfinal)
            
            array = []
            
            sortedtree.pop(startpoint)
            return recursive_sort_uv_tree(startpoint, array)
         
        def lerp(v0, v1, t):
          return v0 + t * (v1 - v0)
                
        
        target_data: GenerateLoopTreeResult = generate_loop_tree(target)
        sorted_target_tree = sort_uv_tree(target_data["tree"], target)
        print("sorted target.")
        #print(sorted_target_tree)
        
        for source in sources:
            if source == target:
                continue
            
            #create our list of points that is a chain. then sort the chain into the correct order based on connections of vertices and the faces that the vertices make up in the UV map.
            try:
                source_data = generate_loop_tree(source)
                sorted_source_tree = sort_uv_tree(source_data["tree"], source)
                print("Sorted source "+source)
                print(sorted_source_tree)
                
                vertex_factor = float(len(sorted_target_tree)-1) / (float(len(sorted_source_tree)-1))
                
                print(str(vertex_factor)+" = "+str(float(len(sorted_target_tree)-1)) + " / " + str((float(len(sorted_source_tree)-1)))+")")
            except Exception as e:
                print(e)
                return {'FINISHED'}
            
            for k,i in enumerate(sorted_source_tree):
                
                try:
                    #find where we are on the target edges, to interpolate the current point we're placing along the target point's line.
                    progress_along_edge = (float(k)*vertex_factor)
                    previous_vertex_index = math.floor(progress_along_edge)
                    next_vertex_index = math.ceil(progress_along_edge)
                    
                    
                    #find the uv coordinates of the previous and next points on the target uv line. 
                    a_list1 = sorted_target_tree[previous_vertex_index].replace(", "," ").replace("[","").replace("]","").split()
                    map_object1 = map(float, a_list1)
                    previous_point = list(map_object1)
                    a_list2 = sorted_target_tree[next_vertex_index].replace(", "," ").replace("[","").replace("]","").split()
                    map_object2 = map(float, a_list2)
                    next_point = list(map_object2)
                    
                    
                    
                    #create a point between these two values that represents a decimal 0-1 going where we are to where we are going between the two current points on the edge we are targeting this whole shebang with.
                    progress_between_points = progress_along_edge - int(progress_along_edge)
                    lerped_point = [lerp(previous_point[0],next_point[0],progress_between_points),lerp(previous_point[1],next_point[1],progress_between_points)]
                    
                    #grab our uv face corners for each uv coord that we saved. 
                    #Since each face is considered separate internally, we have to treat each connected face to a vertex in a uv map as separate entities/vertexes.
                    #basically pretend they are split apart.
                    uv_face_corners = source_data["selected_loops"][i]
                    #print("doing from vertex "+str(previous_vertex_index)+" to "+str(next_vertex_index)+" total progress: "+str(progress_along_edge))
                    
                    
                    
                    me: Mesh = bpy.data.objects[source].data
                    me.validate()
                    bm: bmesh.types.BMesh = bmesh.new()
                    bm.from_mesh(me)
                    uv_lay: MeshUVLoopLayer = me.uv_layers.active
                    bm.verts.ensure_lookup_table()
                    for corner in uv_face_corners:
                        uv_lay.uv[corner].vector = lerped_point #put the vertcies at the point we calculated. 
                except:
                    print("This is probably fine? - @989onan") #TODO: What happened here? The magic of making code so complex you forget if this is even an issue. - @989onan
            
            print("Finished mesh \""+source+"\" for UV's")
                    
                
                 
        bpy.ops.object.mode_set(mode=prev_mode)
        return {'FINISHED'}