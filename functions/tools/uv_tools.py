from typing import TypedDict, Set, Dict, List, Optional, Any, Tuple
import bpy
from bpy.types import Operator, Object, Context, Mesh, MeshUVLoopLayer
import bmesh
import numpy as np
import math
from ...core.translations import t
from ...core.logging_setup import logger

class GenerateLoopTreeResult(TypedDict):
    tree: Dict[str, Set[str]]
    selected_loops: Dict[str, List[int]]
    selected_verts: Dict[str, int]

class AvatarToolkit_OT_AlignUVEdgesToTarget(Operator):
    """Operator to align selected UV edges to target edge"""
    bl_idname = "avatar_toolkit.align_uv_edges_to_target"
    bl_label = t("UVTools.align_edges")
    bl_description = t("UVTools.align_edges_desc")
    bl_options = {'REGISTER', 'UNDO'}

    #all selected objects need to be meshes for this to work - @989onan
    @classmethod
    def poll(cls, context: Context) -> bool:
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

    def execute(self, context: Context) -> Set[str]:
        target: str = context.view_layer.objects.active.name #The object which we want to align every other selected object's selected UV vertex line to
        sources: List[str] = [i.name for i in context.view_layer.objects.selected] #The objects which we want to align their selected UV lines to the target's UV line

        prev_mode: str = bpy.context.object.mode
        bpy.ops.object.mode_set(mode='OBJECT')

        def generate_loop_tree(obj_name: str) -> GenerateLoopTreeResult:
            logger.debug(f"Finding selected line for: {obj_name}")

            vert_target_loops: Dict[str, List[int]] = {}
            vert_target_verts: Dict[str, int] = {}

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
            for k,i in enumerate(uv_lay.vertex_selection):
                if (i.value == True) and (bm.verts[me.loops[k].vertex_index].select == True) and (bm.verts[me.loops[k].vertex_index].hide == False):
                    key = np.array(uv_lay.uv[k].vector[:])
                    key = key.round(decimals=5)

                    if str(key) not in vert_target_loops:
                        vert_target_loops[str(key)] = []
                    vert_target_loops[str(key)].append(k)
                    vert_target_verts[str(key)] = me.loops[k].vertex_index

            if len(vert_target_loops) > 4000:
                self.report({'WARNING'}, t("UVTools.too_many_vertices"))
                return {"tree": {}, "selected_loops": {}, "selected_verts": {}}

            logger.debug(f"Finding connections on line for {obj_name}")
            me.validate()

            bm = bmesh.new()
            bm.from_mesh(me)

            tree: Dict[str, Set[str]] = {}
            selected_verts = np.hstack(list(vert_target_loops.values()))
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
                        self.report({'WARNING'}, t("UVTools.need_line", obj=obj_name))
                        return {"tree": {}, "selected_loops": {}, "selected_verts": {}}

            uv_lay = me.uv_layers.active
            for uvcoordstr in vert_target_loops:
                for loop in vert_target_loops[uvcoordstr]:
                    uv_lay.vertex_selection[loop].value = True

            bm.free()
            me.validate()
            logger.debug(f"Found UV line connections for {obj_name}")

            return {"tree": tree, "selected_loops": vert_target_loops, "selected_verts": vert_target_verts}

        def sort_uv_tree(originaltree: Dict[str, Set[str]], obj_name: str) -> List[str]:
            sortedtree: Dict[str, Set[str]] = originaltree.copy()
            startpoints: List[str] = []
            for i in sortedtree:
                if len(sortedtree[i]) < 2:
                    startpoints.append(i)

            if len(startpoints) != 2:
                self.report({'WARNING'}, t("UVTools.need_line", obj=obj_name))
                return []

            uvcoords1 = [float(x) for x in startpoints[0].replace("[","").replace("]","").split()]
            uvcoords2 = [float(x) for x in startpoints[1].replace("[","").replace("]","").split()]

            cursor = context.space_data.cursor_location

            startpoint = startpoints[0] if math.sqrt((uvcoords1[0] - cursor[0])**2 + (uvcoords1[1] - cursor[1])**2) > math.sqrt((uvcoords2[0] - cursor[0])**2 + (uvcoords2[1] - cursor[1])**2) else startpoints[1]

            #Wew my first actual recursive sort! - @989onan
            def recursive_sort_uv_tree(point: str, sortedfinal: List[str]) -> List[str]:
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
                    logger.debug("Sorting complete, remaining tree:")
                    logger.debug(sortedtree)
                    return sortedfinal

                return recursive_sort_uv_tree(new_point, sortedfinal)

            sortedtree.pop(startpoint)
            return recursive_sort_uv_tree(startpoint, [])

        def lerp(v0: float, v1: float, t: float) -> float:
            return v0 + t * (v1 - v0)

        target_data = generate_loop_tree(target)
        sorted_target_tree = sort_uv_tree(target_data["tree"], target)
        logger.debug("Sorted target tree")

        for source in sources:
            if source == target:
                continue

            try:
                source_data = generate_loop_tree(source)
                sorted_source_tree = sort_uv_tree(source_data["tree"], source)
                logger.debug(f"Sorted source {source}")

                vertex_factor = float(len(sorted_target_tree)-1) / float(len(sorted_source_tree)-1)
                logger.debug(f"Vertex factor: {vertex_factor}")

                for k, i in enumerate(sorted_source_tree):
                    try:
                        #find where we are on the target edges, to interpolate the current point we're placing along the target point's line.
                        progress_along_edge = float(k) * vertex_factor
                        previous_vertex_index = math.floor(progress_along_edge)
                        next_vertex_index = math.ceil(progress_along_edge)

                        #find the uv coordinates of the previous and next points on the target uv line. 
                        previous_point = [float(x) for x in sorted_target_tree[previous_vertex_index].replace("[","").replace("]","").split()]
                        next_point = [float(x) for x in sorted_target_tree[next_vertex_index].replace("[","").replace("]","").split()]

                        #create a point between these two values that represents a decimal 0-1 going where we are to where we are going between the two current points on the edge we are targeting this whole shebang with.
                        progress_between_points = progress_along_edge - int(progress_along_edge)
                        lerped_point = [
                            lerp(previous_point[0], next_point[0], progress_between_points),
                            lerp(previous_point[1], next_point[1], progress_between_points)
                        ]

                        #grab our uv face corners for each uv coord that we saved. 
                        #Since each face is considered separate internally, we have to treat each connected face to a vertex in a uv map as separate entities/vertexes.
                        #basically pretend they are split apart.
                        uv_face_corners = source_data["selected_loops"][i]

                        me = bpy.data.objects[source].data
                        me.validate()
                        bm = bmesh.new()
                        bm.from_mesh(me)
                        uv_lay = me.uv_layers.active
                        bm.verts.ensure_lookup_table()
                        
                        for corner in uv_face_corners:
                            uv_lay.uv[corner].vector = lerped_point

                    except:
                        #This is probably fine? - @989onan
                        #TODO: What happened here? The magic of making code so complex you forget if this is even an issue. - @989onan
                        pass

                logger.info(f"Finished mesh {source} for UV's")

            except Exception as e:
                logger.error(f"Error processing source {source}: {str(e)}")
                return {'CANCELLED'}

        bpy.ops.object.mode_set(mode=prev_mode)
        return {'FINISHED'}
