import bpy
from bpy.types import Operator, Context
from ...core.translations import t
from ...core.common import get_active_armature, validate_armature

class AvatarToolKit_OT_SeparateByMaterials(Operator):
    """Operator to separate mesh by materials"""
    bl_idname = "avatar_toolkit.separate_materials"
    bl_label = t("Tools.separate_materials")
    bl_description = t("Tools.separate_materials_desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        """Check if operator can be executed"""
        armature = get_active_armature(context)
        if not armature:
            return False
        is_valid, _ = validate_armature(armature)
        return (context.active_object and 
                context.active_object.type == 'MESH' and 
                is_valid)

    def execute(self, context: Context) -> set[str]:
        """Execute the separation operation"""
        try:
            obj = context.active_object
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.separate(type='MATERIAL')
            bpy.ops.object.mode_set(mode='OBJECT')
            self.report({'INFO'}, t("Tools.separate_materials_success"))
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

class AvatarToolKit_OT_SeparateByLooseParts(Operator):
    """Operator to separate mesh by loose parts"""
    bl_idname = "avatar_toolkit.separate_loose"
    bl_label = t("Tools.separate_loose")
    bl_description = t("Tools.separate_loose_desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        """Check if operator can be executed"""
        armature = get_active_armature(context)
        if not armature:
            return False
        is_valid, _ = validate_armature(armature)
        return (context.active_object and 
                context.active_object.type == 'MESH' and 
                is_valid)

    def execute(self, context: Context) -> set[str]:
        """Execute the separation operation"""
        try:
            obj = context.active_object
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.separate(type='LOOSE')
            bpy.ops.object.mode_set(mode='OBJECT')
            self.report({'INFO'}, t("Tools.separate_loose_success"))
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
