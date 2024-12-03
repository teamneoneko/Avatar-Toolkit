import numpy as np
import bpy
from typing import List, Optional, Set
from bpy.types import Operator, Context, Object
from ..core.common import fix_uv_coordinates, get_selected_armature, get_all_meshes, is_valid_armature, apply_shapekey_to_basis, has_shapekeys, select_current_armature, init_progress, update_progress, finish_progress
from ..core.translations import t


class AvatarToolkit_OT_RemoveUnusedShapekeys(bpy.types.Operator):
    tolerance: bpy.props.FloatProperty(name=t("Tools.remove_unused_shapekeys.tolerance.label"), default=0.001, description=t("Tools.remove_unused_shapekeys.tolerance.desc"))
    bl_idname = "avatar_toolkit.remove_unused_shapekeys"
    bl_label = t("Tools.remove_unused_shapekeys.label")
    bl_description = t("Tools.remove_unused_shapekeys.desc")
    bl_options = {'REGISTER', 'UNDO'}
    

    @classmethod
    def poll(cls, context: Context) -> bool:
        armature = get_selected_armature(context)
        return armature is not None and is_valid_armature(armature) and (len(get_all_meshes(context)) > 0) and (context.mode == "OBJECT")

    def execute(self, context: Context) -> set[str]:
        #Shamefully taken from: https://blender.stackexchange.com/a/237611
        #at least I am crediting them - @989onan
        for ob in get_all_meshes(context):
            if not ob.data.shape_keys: continue
            if not ob.data.shape_keys.use_relative: continue

            kbs = ob.data.shape_keys.key_blocks
            nverts = len(ob.data.vertices)
            to_delete = []

            # Cache locs for rel keys since many keys have the same rel key
            cache = {}

            locs = np.empty(3*nverts, dtype=np.float32)

            for kb in kbs:
                if kb == kb.relative_key: continue

                kb.data.foreach_get("co", locs)

                if kb.relative_key.name not in cache:
                    rel_locs = np.empty(3*nverts, dtype=np.float32)
                    kb.relative_key.data.foreach_get("co", rel_locs)
                    cache[kb.relative_key.name] = rel_locs
                rel_locs = cache[kb.relative_key.name]

                locs -= rel_locs
                if (np.abs(locs) < self.tolerance).all():
                    to_delete.append(kb.name)

            for kb_name in to_delete:
                if ("-" in kb_name) or ("=" in kb_name) or ("~" in kb_name): 
                    continue
                ob.shape_key_remove(ob.data.shape_keys.key_blocks[kb_name])
                
        return {'FINISHED'}


class AvatarToolkit_OT_ApplyShapeKey(bpy.types.Operator):
    bl_idname = "avatar_toolkit.apply_shape_key"
    bl_label = t("Tools.apply_shape_key.label")
    bl_description = t("Tools.apply_shape_key.desc")
    bl_options = {'REGISTER', 'UNDO'}
    

    @classmethod
    def poll(cls, context: Context) -> bool:
        armature = get_selected_armature(context)
        return armature is not None and is_valid_armature(armature) and (len(get_all_meshes(context)) > 0) and (context.mode == "OBJECT") and context.view_layer.objects.active is not None and has_shapekeys(context.view_layer.objects.active)

    def execute(self, context: Context) -> set[str]:
        obj: bpy.types.Object = context.view_layer.objects.active

        
        if (apply_shapekey_to_basis(context,obj,obj.active_shape_key.name,False)):
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, t("Tools.apply_shape_key.error"))
            return {'FINISHED'}


class AvatarToolKit_OT_JoinAllMeshes(Operator):
    bl_idname = "avatar_toolkit.join_all_meshes"
    bl_label = t("Optimization.join_all_meshes.label")
    bl_description = t("Optimization.join_all_meshes.desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        armature = get_selected_armature(context)
        return armature is not None and is_valid_armature(armature)

    def execute(self, context: Context) -> Set[str]:
        try:
            self.join_all_meshes(context)
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"{t('Optimization.join_error')}: {str(e)}")
            return {'CANCELLED'}

    def join_all_meshes(self, context: Context) -> None:
        if not select_current_armature(context):
            raise ValueError(t("Optimization.no_armature_selected"))

        armature = get_selected_armature(context)
        
        bpy.ops.object.mode_set(mode='OBJECT')
        
        bpy.ops.object.select_all(action='DESELECT')

        meshes: List[Object] = get_all_meshes(context)
        
        if not meshes:
            raise ValueError(t("Optimization.no_meshes_found"))

        init_progress(context, 5)  # 5 steps in total

        update_progress(self, context, t("Optimization.selecting_meshes"))
        for mesh in meshes:
            mesh.select_set(True)

        if bpy.context.selected_objects:
            bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]
            
            update_progress(self, context, t("Optimization.joining_meshes"))
            try:
                bpy.ops.object.join()
            except RuntimeError as e:
                raise RuntimeError(f"{t('Optimization.join_operation_failed')}: {str(e)}")

            update_progress(self, context, t("Optimization.applying_transforms"))
            try:
                bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            except RuntimeError as e:
                raise RuntimeError(f"{t('Optimization.transform_apply_failed')}: {str(e)}")

            update_progress(self, context, t("Optimization.fixing_uv_coordinates"))
            bpy.ops.object.mode_set(mode='OBJECT')
            fix_uv_coordinates(context)
            
            update_progress(self, context, t("Optimization.finalizing"))
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            self.report({'INFO'}, t("Optimization.meshes_joined"))
        else:
            raise ValueError(t("Optimization.no_mesh_selected"))

        context.view_layer.objects.active = armature
        finish_progress(context)



class AvatarToolKit_OT_JoinSelectedMeshes(Operator):
    bl_idname = "avatar_toolkit.join_selected_meshes"
    bl_label = t("Optimization.join_selected_meshes.label")
    bl_description = t("Optimization.join_selected_meshes.desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return context.mode == 'OBJECT' and len([obj for obj in context.selected_objects if obj.type == 'MESH']) > 1

    def execute(self, context: Context) -> Set[str]:
        try:
            self.join_selected_meshes(context)
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"{t('Optimization.join_error')}: {str(e)}")
            return {'CANCELLED'}

    def join_selected_meshes(self, context: Context) -> None:
        selected_objects: List[Object] = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']

        if len(selected_objects) < 2:
            raise ValueError(t("Optimization.select_at_least_two_meshes"))

        init_progress(context, 5)  # 5 steps in total

        update_progress(self, context, t("Optimization.preparing_meshes"))
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')

        update_progress(self, context, t("Optimization.selecting_meshes"))
        for obj in selected_objects:
            obj.select_set(True)

        if bpy.context.selected_objects:
            bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]
            
            update_progress(self, context, t("Optimization.joining_meshes"))
            try:
                bpy.ops.object.join()
            except RuntimeError as e:
                raise RuntimeError(f"{t('Optimization.join_operation_failed')}: {str(e)}")

            update_progress(self, context, t("Optimization.applying_transforms"))
            try:
                bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            except RuntimeError as e:
                raise RuntimeError(f"{t('Optimization.transform_apply_failed')}: {str(e)}")

            update_progress(self, context, t("Optimization.fixing_uv_coordinates"))
            fix_uv_coordinates(context)
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            self.report({'INFO'}, t("Optimization.selected_meshes_joined"))
        else:
            raise ValueError(t("Optimization.no_mesh_selected"))

        finish_progress(context)