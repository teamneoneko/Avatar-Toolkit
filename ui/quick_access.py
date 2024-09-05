import bpy
from ..core.register import register_wrap
from .panel import AvatarToolkitPanel
from bpy.types import Context, Mesh, Panel, Operator
from ..functions.translations import t

from ..core.import_pmx import import_pmx
from ..core.import_pmd import import_pmd
from ..functions.import_anything import ImportAnyModel
from ..core.common import get_selected_armature, set_selected_armature, get_all_meshes

@register_wrap
@register_wrap
class AvatarToolkitQuickAccessPanel(Panel):
    bl_label = t("Quick_Access.label")
    bl_idname = "OBJECT_PT_avatar_toolkit_quick_access"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Avatar Toolkit"
    bl_parent_id = "OBJECT_PT_avatar_toolkit"
    bl_order = 1

    def draw(self, context: Context):
        layout = self.layout
        layout.label(text=t("Quick_Access.options"), icon='TOOL_SETTINGS')

        layout.label(text=t("Quick_Access.select_armature"), icon='ARMATURE_DATA')

        layout.prop(context.scene, "selected_armature", text="")

        row = layout.row()
        row.label(text=t("Quick_Access.import_export.label"), icon='IMPORT')
        
        layout.separator(factor=0.5)

        row = layout.row(align=True)
        row.scale_y = 1.5  
        row.operator(ImportAnyModel.bl_idname, text=t("Quick_Access.import"), icon='IMPORT')
        row.operator(AVATAR_TOOLKIT_OT_export_menu.bl_idname, text=t("Quick_Access.export"), icon='EXPORT')
        
        if get_selected_armature(context) != None:
            if(context.mode == "POSE"):
                row = layout.row(align=True)
                row.operator(AvatarToolkit_OT_StopPoseMode.bl_idname, text=t("Quick_Access.stop_pose_mode.label"), icon='POSE_HLT')
                row = layout.row(align=True)
                row.operator(AvatarToolkit_OT_ApplyPoseAsRest.bl_idname, text=t("Quick_Access.apply_pose_as_rest.label"), icon='MOD_ARMATURE')
                row = layout.row(align=True)
                row.operator(AvatarToolkit_OT_ApplyPoseAsShapekey.bl_idname, text=t("Quick_Access.apply_pose_as_shapekey.label"), icon='MOD_ARMATURE')
            else:
                row = layout.row(align=True)
                row.operator(AvatarToolkit_OT_StartPoseMode.bl_idname, text=t("Quick_Access.start_pose_mode.label"), icon='POSE_HLT')

@register_wrap
class AvatarToolkit_OT_StartPoseMode(Operator):
    bl_idname = 'avatar_toolkit.start_pose_mode'
    bl_label = t("Quick_Access.start_pose_mode.label")
    bl_description = t("Quick_Access.start_pose_mode.desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return get_selected_armature(context) != None and context.mode != "POSE"
    
    def execute(self, context: Context) -> set[str]:
        
        #give an active object so the next line doesn't throw an error.
        context.view_layer.objects.active = get_selected_armature(context)

        bpy.ops.object.mode_set(mode='OBJECT')

        #deselect everything and select just our armature, then go into pose on just our selected armature. - @989onan
        bpy.ops.object.select_all(action='DESELECT')
        context.view_layer.objects.active = get_selected_armature(context)
        context.view_layer.objects.active.select_set(True)
        bpy.ops.object.mode_set(mode='POSE')

        return {'FINISHED'}

@register_wrap
class AvatarToolkit_OT_StopPoseMode(Operator):
    bl_idname = 'avatar_toolkit.stop_pose_mode'
    bl_label = t("Quick_Access.stop_pose_mode.label")
    bl_description = t("Quick_Access.stop_pose_mode.desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return get_selected_armature(context) != None and context.mode == "POSE"
    
    def execute(self, context: Context) -> set[str]:
        #this is done so that transforms are cleared but user selection is respected. - @989onan
        bpy.ops.pose.transforms_clear()
        bpy.ops.pose.select_all(action="INVERT")
        bpy.ops.pose.transforms_clear()
        bpy.ops.pose.select_all(action="INVERT")

        bpy.ops.object.mode_set(mode='OBJECT')

        return {'FINISHED'}

@register_wrap
class AvatarToolkit_OT_ApplyPoseAsShapekey(Operator):
    bl_idname = 'avatar_toolkit.apply_pose_as_shapekey'
    bl_label = t("Quick_Access.apply_pose_as_shapekey.label")
    bl_description = t("Quick_Access.apply_pose_as_shapekey.desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return get_selected_armature(context) != None and context.mode == "POSE"
    
    def execute(self, context: Context):
        bpy.ops.object.mode_set(mode="OBJECT")
        for obj in get_all_meshes(context):

            modifier_armature_name: str = ""
            context.view_layer.objects.active = obj
                    
            bpy.ops.object.mode_set(mode="OBJECT")
            bpy.ops.object.select_all(action="DESELECT")
            context.view_layer.objects.active = obj
            obj.select_set(True)
            for modifier in obj.modifiers:
                if modifier.type == "ARMATURE":
                    arm_modifier: bpy.types.ArmatureModifier = modifier
                    modifier_armature_name = arm_modifier.object.name
            bpy.ops.object.modifier_apply_as_shapekey(modifier=modifier_armature_name,keep_modifier=True,report=True)
        
        return {'FINISHED'}

@register_wrap
class AvatarToolkit_OT_ApplyPoseAsRest(Operator):
    bl_idname = 'avatar_toolkit.apply_pose_as_rest'
    bl_label = t("Quick_Access.apply_pose_as_rest.label")
    bl_description = t("Quick_Access.apply_pose_as_rest.desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return get_selected_armature(context) != None and context.mode == "POSE"
    
    def execute(self, context: Context):
        for obj in get_all_meshes(context):
            mesh_data: Mesh = obj.data



            if mesh_data.shape_keys:
                shape_key_obj_list: list[bpy.types.Object] = []
                modifier_armature_name: str = ""

                for modifier in obj.modifiers:
                    if modifier.type == "ARMATURE":
                        arm_modifier: bpy.types.ArmatureModifier = modifier
                        modifier_armature_name = arm_modifier.object.name
                for idx,shape in enumerate(mesh_data.shape_keys.key_blocks):
                    if idx == 0:
                        continue
                    context.view_layer.objects.active = obj
                    
                    bpy.ops.object.mode_set(mode="OBJECT")
                    bpy.ops.object.select_all(action="DESELECT")
                    context.view_layer.objects.active = obj
                    obj.select_set(True)

                    #create duplicate of object
                    bpy.ops.object.duplicate()

                    shape_obj = context.view_layer.objects.active

                    #make current shapekey a separate object
                    shape_obj.active_shape_key_index = idx
                    shape_obj.name = shape.name
                    
                    bpy.ops.object.shape_key_move(type="TOP")

                    bpy.ops.object.mode_set(mode="EDIT")
                    bpy.ops.object.mode_set(mode="OBJECT")

                    bpy.ops.object.shape_key_remove(all=True)

                    bpy.ops.object.modifier_apply(modifier=modifier_armature_name)

                    #for modifier_name in [i.name for i in shape_obj.modifiers]:
                    #    bpy.ops.object.modifier_remove(modifier=modifier_name)

                    shape_key_obj_list.append(shape_obj) #add to a list of shape key objects
                context.view_layer.objects.active = obj
                    
                bpy.ops.object.mode_set(mode="OBJECT")
                context.view_layer.objects.active.select_set(True)
                bpy.ops.object.shape_key_remove(all=True)
                bpy.ops.object.modifier_apply(modifier=modifier_armature_name)
                bpy.ops.object.select_all(action="DESELECT")

                for shapekey_obj in shape_key_obj_list:
                    shapekey_obj.select_set(True)
                context.view_layer.objects.active = obj
                context.view_layer.objects.active.select_set(True)

                try:
                    bpy.ops.object.join_shapes()
                except:
                    self.report({'ERROR'}, t("Quick_Access.apply_armature_failed"))
                    #delete shapekey objects to not leave ourselves in a bad exit state - @989onan
                    context.view_layer.objects.active = shape_key_obj_list[0]
                    obj.select_set(False)
                    bpy.ops.object.delete(confirm=False)
                    return {'CANCELLED'}
                context.view_layer.objects.active = shape_key_obj_list[0]
                obj.select_set(False)
                bpy.ops.object.delete(confirm=False)
            else:
                modifier_armature_name: str = ""

                for modifier in obj.modifiers:
                    if modifier.type == "ARMATURE":
                        arm_modifier: bpy.types.ArmatureModifier = modifier
                        modifier_armature_name = arm_modifier.object.name
                context.view_layer.objects.active = obj
                bpy.ops.object.mode_set(mode="OBJECT")
                bpy.ops.object.select_all(action="DESELECT")
                context.view_layer.objects.active.select_set(True)
                bpy.ops.object.modifier_apply(modifier=modifier_armature_name)

            armature_obj: bpy.types.Object = get_selected_armature(context)
            
            context.view_layer.objects.active = armature_obj
            armature_obj.select_set(True)
            bpy.ops.object.mode_set(mode="OBJECT")
            bpy.ops.object.mode_set(mode="POSE")

            bpy.ops.pose.armature_apply(selected=False)

        return {'FINISHED'}

@register_wrap
class AVATAR_TOOLKIT_OT_export_menu(Operator):
    bl_idname = "avatar_toolkit.export_menu"
    bl_label = t("Quick_Access.export_menu.label")
    bl_description = t("Quick_Access.export_menu.desc")

    @classmethod
    def poll(cls, context):
        return any(obj.type == 'MESH' for obj in context.scene.objects)

    def execute(self, context: Context) -> set[str]:
        return {'FINISHED'}

    def invoke(self, context: Context, event):
        wm = context.window_manager
        return wm.invoke_popup(self, width=200)

    def draw(self, context: Context):
        layout = self.layout
        layout.label(text=t("Quick_Access.select_export.label"), icon='EXPORT')
        layout.operator("avatar_toolkit.export_resonite", text=t("Quick_Access.select_export_resonite.label"), icon='SCENE_DATA')
        layout.operator("avatar_toolkit.export_fbx", text=t("Quick_Access.export_fbx.label"), icon='OBJECT_DATA')

@register_wrap
class AVATAR_TOOLKIT_OT_export_fbx(Operator):
    bl_idname = 'avatar_toolkit.export_fbx'
    bl_label = t("Quick_Access.export_fbx.label")
    bl_description = t("Quick_Access.export_fbx.desc")
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context) -> set[str]:
        bpy.ops.export_scene.fbx('INVOKE_DEFAULT')
        return {'FINISHED'}
