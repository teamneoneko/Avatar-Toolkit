# MMD Tools disabled for the time being unto it can be fixed.

# import bpy
# from typing import Set
# from bpy.types import Panel, Context, UILayout
# from .main_panel import AvatarToolKit_PT_AvatarToolkitPanel, CATEGORY_NAME
# from ..core.translations import t

# class AvatarToolKit_PT_MMDPanel(Panel):
#   """Panel containing MMD bone standardization and cleanup tools"""
#    bl_label = t("MMD.label")
#    bl_idname = "OBJECT_PT_avatar_toolkit_mmd"
#    bl_space_type = 'VIEW_3D'
#    bl_region_type = 'UI'
#    bl_category = CATEGORY_NAME
#    bl_parent_id = AvatarToolKit_PT_AvatarToolkitPanel.bl_idname
#    bl_order = 3
#    bl_options = {'DEFAULT_CLOSED'}

#    def draw(self, context: Context) -> None:
#        layout: UILayout = self.layout
#        toolkit = context.scene.avatar_toolkit
        
        # Bone Settings Box
#        bone_box: UILayout = layout.box()
#        col: UILayout = bone_box.column(align=True)
#        col.label(text=t("MMD.bone_settings"), icon='BONE_DATA')
#        col.separator(factor=0.5)
#        col.prop(toolkit, "keep_twist_bones")
#        col.prop(toolkit, "keep_upper_chest")
#        col.operator("avatar_toolkit.standardize_mmd", icon='BONE_DATA')
        
        # Mesh Tools Box
#        mesh_box: UILayout = layout.box()
#        col = mesh_box.column(align=True)
#        col.label(text=t("MMD.mesh_tools"), icon='MESH_DATA')
#        col.separator(factor=0.5)
#        row: UILayout = col.row(align=True)
#        row.operator("avatar_toolkit.fix_meshes", icon='MODIFIER')
#        row.operator("avatar_toolkit.validate_meshes", icon='CHECKMARK')
        
        # Cleanup Box
#        cleanup_box: UILayout = layout.box()
#        col = cleanup_box.column(align=True)
#        col.label(text=t("MMD.cleanup"), icon='BRUSH_DATA')
#        col.separator(factor=0.5)
#        col.operator("avatar_toolkit.cleanup_mmd", icon='SHADERFX')
#        col.operator("avatar_toolkit.convert_mmd_morphs", icon='SHAPEKEY_DATA')
#        col.operator("avatar_toolkit.reparent_meshes", icon='OUTLINER_OB_ARMATURE')
