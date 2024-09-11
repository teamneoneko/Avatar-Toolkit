import bpy
from ..core.register import register_wrap
from .panel import AvatarToolkitPanel
from bpy.types import Context, Mesh, Panel, Operator
from ..functions.translations import t

from ..core.import_pmx import import_pmx
from ..core.import_pmd import import_pmd
from ..functions.import_anything import ImportAnyModel
from ..functions.armature_modifying import AvatarToolkit_OT_StartPoseMode, AvatarToolkit_OT_StopPoseMode, AvatarToolkit_OT_ApplyPoseAsRest, AvatarToolkit_OT_ApplyPoseAsShapekey
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
