import bpy
from typing import Set
from bpy.types import Panel, Context, UILayout, Operator
from .main_panel import AvatarToolKit_PT_AvatarToolkitPanel, CATEGORY_NAME
from ..core.translations import t
from ..core.common import (
    get_active_armature,
    get_all_meshes,
    validate_armature,
    get_armature_list
)

class AvatarToolkit_OT_SearchMergeArmatureInto(Operator):
    bl_idname = "avatar_toolkit.search_merge_armature_into"
    bl_label = ""
    bl_description = t('MergeArmature.into_search_desc')
    bl_property = "search_merge_armature_into_enum"

    search_merge_armature_into_enum: bpy.props.EnumProperty(
        name=t('MergeArmature.into'),
        description=t('MergeArmature.into_desc'),
        items=get_armature_list
    )

    def execute(self, context):
        context.scene.avatar_toolkit.merge_armature_into = self.search_merge_armature_into_enum
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.invoke_search_popup(self)
        return {'FINISHED'}

class AvatarToolkit_OT_SearchMergeArmature(Operator):
    bl_idname = "avatar_toolkit.search_merge_armature"
    bl_label = ""
    bl_description = t('MergeArmature.from_search_desc')
    bl_property = "search_merge_armature_enum"

    search_merge_armature_enum: bpy.props.EnumProperty(
        name=t('MergeArmature.from'),
        description=t('MergeArmature.from_desc'),
        items=get_armature_list
    )

    def execute(self, context):
        context.scene.avatar_toolkit.merge_armature = self.search_merge_armature_enum
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.invoke_search_popup(self)
        return {'FINISHED'}

class AvatarToolkit_OT_SearchAttachMesh(Operator):
    bl_idname = "avatar_toolkit.search_attach_mesh"
    bl_label = ""
    bl_description = t('AttachMesh.search_desc')
    bl_property = "search_attach_mesh_enum"

    search_attach_mesh_enum: bpy.props.EnumProperty(
        name=t('AttachMesh.select'),
        description=t('AttachMesh.select_desc'),
        items=lambda self, context: [
            (obj.name, obj.name, "")
            for obj in bpy.data.objects 
            if obj.type == 'MESH' 
            and not any(mod.type == 'ARMATURE' for mod in obj.modifiers)
        ]
    )

    def execute(self, context):
        context.scene.avatar_toolkit.attach_mesh = self.search_attach_mesh_enum
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.invoke_search_popup(self)
        return {'FINISHED'}

class AvatarToolkit_OT_SearchAttachBone(Operator):
    bl_idname = "avatar_toolkit.search_attach_bone"
    bl_label = ""
    bl_description = t('AttachBone.search_desc')
    bl_property = "search_attach_bone_enum"

    search_attach_bone_enum: bpy.props.EnumProperty(
        name=t('AttachBone.select'),
        description=t('AttachBone.select_desc'),
        items=lambda self, context: [
            (bone.name, bone.name, "")
            for bone in get_active_armature(context).data.bones
        ] if get_active_armature(context) else []
    )

    def execute(self, context):
        context.scene.avatar_toolkit.attach_bone = self.search_attach_bone_enum
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.invoke_search_popup(self)
        return {'FINISHED'}

class AvatarToolKit_PT_CustomPanel(Panel):
    """Panel containing tools for custom avatar creation and merging"""
    bl_label = t('CustomPanel.label')
    bl_idname = "VIEW3D_PT_avatar_toolkit_custom"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY_NAME
    bl_parent_id = AvatarToolKit_PT_AvatarToolkitPanel.bl_idname
    bl_order = 4
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context: Context) -> None:
        layout: UILayout = self.layout
        toolkit = context.scene.avatar_toolkit

        # Mode Selection Box
        mode_box: UILayout = layout.box()
        col: UILayout = mode_box.column(align=True)
        col.label(text=t('CustomPanel.merge_mode'), icon='TOOL_SETTINGS')
        col.separator(factor=0.5)

        row: UILayout = col.row(align=True)
        row.scale_y = 1.5
        row.prop(toolkit, "merge_mode", expand=True)
        
        if toolkit.merge_mode == 'ARMATURE':
            self.draw_armature_tools(layout, context)
        else:
            self.draw_mesh_tools(layout, context)

    def draw_armature_tools(self, layout: UILayout, context: Context) -> None:
        toolkit = context.scene.avatar_toolkit
        
        # Merge Settings Box
        settings_box: UILayout = layout.box()
        col: UILayout = settings_box.column(align=True)
        col.label(text=t('MergeArmature.label'), icon='ARMATURE_DATA')
        col.separator(factor=0.5)
        
        if len(get_armature_list(context)) <= 1:
            col.label(text=t('MergeArmature.warn_two'), icon='INFO')
            return

        # Options Box with better spacing
        options_box: UILayout = layout.box()
        col: UILayout = options_box.column(align=True)
        col.label(text=t('MergeArmature.options'), icon='SETTINGS')
        col.separator(factor=0.5)
        
        # Group related options together
        transform_col = col.column(align=True)
        transform_col.prop(toolkit, "merge_all_bones")
        transform_col.prop(toolkit, "apply_transforms")
        
        col.separator(factor=0.5)
        
        cleanup_col = col.column(align=True)
        cleanup_col.prop(toolkit, "join_meshes")
        cleanup_col.prop(toolkit, "remove_zero_weights")
        cleanup_col.prop(toolkit, "cleanup_shape_keys")

        # Selection Box with consistent styling
        selection_box: UILayout = layout.box()
        col: UILayout = selection_box.column(align=True)
        col.label(text=t('CustomPanel.select_armature'), icon='BONE_DATA')
        col.separator(factor=0.5)
        
        # Armature selection with better alignment
        row: UILayout = col.row(align=True)
        row.label(text=t('MergeArmature.into'), icon='ARMATURE_DATA')
        row.operator("avatar_toolkit.search_merge_armature_into",
                    text=toolkit.merge_armature_into)

        row: UILayout = col.row(align=True)
        row.label(text=t('MergeArmature.from'), icon='ARMATURE_DATA')
        row.operator("avatar_toolkit.search_merge_armature",
                    text=toolkit.merge_armature)

        # Merge button with emphasis
        merge_box: UILayout = layout.box()
        col = merge_box.column(align=True)
        row = col.row(align=True)
        row.scale_y = 1.5
        row.operator("avatar_toolkit.merge_armatures", icon='ARMATURE_DATA')

    def draw_mesh_tools(self, layout: UILayout, context: Context) -> None:
        toolkit = context.scene.avatar_toolkit
        
        # Mesh Tools Box
        tools_box: UILayout = layout.box()
        col: UILayout = tools_box.column(align=True)
        col.label(text=t('AttachMesh.label'), icon='MESH_DATA')
        col.separator(factor=0.5)

        if not get_active_armature(context) or not get_all_meshes(context):
            col.label(text=t('AttachMesh.warn_no_armature'), icon='INFO')
            return

        # Selection Box with consistent styling
        selection_box: UILayout = layout.box()
        col: UILayout = selection_box.column(align=True)
        col.label(text=t('CustomPanel.mesh_selection'), icon='OBJECT_DATA')
        col.separator(factor=0.5)

        # Selection rows with icons and better alignment
        row: UILayout = col.row(align=True)
        row.label(text=t('CustomPanel.select_armature'), icon='ARMATURE_DATA')
        row.operator("avatar_toolkit.search_merge_armature_into",
                    text=toolkit.merge_armature_into)

        row: UILayout = col.row(align=True)
        row.label(text=t('CustomPanel.select_mesh'), icon='MESH_DATA')
        row.operator("avatar_toolkit.search_attach_mesh",
                    text=toolkit.attach_mesh)

        row: UILayout = col.row(align=True)
        row.label(text=t('CustomPanel.select_bone'), icon='BONE_DATA')
        row.operator("avatar_toolkit.search_attach_bone",
                    text=toolkit.attach_bone)

        # Attach button with emphasis
        attach_box: UILayout = layout.box()
        col = attach_box.column(align=True)
        row = col.row(align=True)
        row.scale_y = 1.5
        row.operator("avatar_toolkit.attach_mesh", icon='ARMATURE_DATA')

