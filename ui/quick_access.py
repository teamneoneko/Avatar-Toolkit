import bpy
from ..core.register import register_wrap
from .panel import AvatarToolKit_PT_AvatarToolkitPanel, CATEGORY_NAME
from ..core.resonite_utils import AvatarToolKit_OT_ExportResonite
from bpy.types import Context, Mesh, Panel, Operator
from ..functions.translations import t

from ..core.import_pmx import import_pmx
from ..core.import_pmd import import_pmd
from ..functions.import_anything import AvatarToolKit_OT_ImportAnyModel
from ..functions.armature_modifying import AvatarToolkit_OT_StartPoseMode, AvatarToolkit_OT_StopPoseMode, AvatarToolkit_OT_ApplyPoseAsRest, AvatarToolkit_OT_ApplyPoseAsShapekey
from ..core.common import get_selected_armature, set_selected_armature, get_all_meshes

@register_wrap
class AvatarToolkitQuickAccessPanel(Panel):
    bl_label = t("Quick_Access.label")
    bl_idname = "OBJECT_PT_avatar_toolkit_quick_access"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY_NAME
    bl_parent_id = AvatarToolKit_PT_AvatarToolkitPanel.bl_idname
    bl_order = 1

    def draw(self, context: Context):
        layout = self.layout
        layout.label(text=t("Quick_Access.options"), icon='TOOL_SETTINGS')

        layout.separator(factor=1.0)

        layout.label(text=t("Quick_Access.select_armature"), icon='ARMATURE_DATA')
        layout.prop(context.scene, "selected_armature", text="")

        layout.separator(factor=1.0)

        layout.label(text=t("Quick_Access.import_export.label"), icon='IMPORT')
        
        row = layout.row(align=True)
        row.scale_y = 1.5
        row.operator(AvatarToolKit_OT_ImportAnyModel.bl_idname, text=t("Quick_Access.import"), icon='IMPORT')
        row.operator(AVATAR_TOOLKIT_OT_ExportMenu.bl_idname, text=t("Quick_Access.export"), icon='EXPORT')

        layout.separator(factor=1.0)

        if get_selected_armature(context) != None:
            if(context.mode == "POSE"):
                col = layout.column(align=True)
                col.scale_y = 1.2
                col.operator(AvatarToolkit_OT_StopPoseMode.bl_idname, text=t("Quick_Access.stop_pose_mode.label"), icon='POSE_HLT')

                layout.separator(factor=0.5)

                col = layout.column(align=True)
                col.scale_y = 1.2
                col.operator(AvatarToolkit_OT_ApplyPoseAsRest.bl_idname, text=t("Quick_Access.apply_pose_as_rest.label"), icon='MOD_ARMATURE')
                col.operator(AvatarToolkit_OT_ApplyPoseAsShapekey.bl_idname, text=t("Quick_Access.apply_pose_as_shapekey.label"), icon='MOD_ARMATURE')
            else:
                row = layout.row()
                row.scale_y = 1.2
                row.operator(AvatarToolkit_OT_StartPoseMode.bl_idname, text=t("Quick_Access.start_pose_mode.label"), icon='POSE_HLT')


@register_wrap
class AVATAR_TOOLKIT_OT_ExportMenu(bpy.types.Operator):
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
        layout.operator(AvatarToolKit_OT_ExportResonite.bl_idname, text=t("Quick_Access.select_export_resonite.label"), icon='SCENE_DATA')
        layout.operator(AVATAR_TOOLKIT_OT_ExportFbx.bl_idname, text=t("Quick_Access.export_fbx.label"), icon='OBJECT_DATA')

@register_wrap
class AVATAR_TOOLKIT_OT_ExportFbx(bpy.types.Operator):
    bl_idname = 'avatar_toolkit.export_fbx'
    bl_label = t("Quick_Access.export_fbx.label")
    bl_description = t("Quick_Access.export_fbx.desc")
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context) -> set[str]:
        bpy.ops.export_scene.fbx('INVOKE_DEFAULT')
        return {'FINISHED'}
