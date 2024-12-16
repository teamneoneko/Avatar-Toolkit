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
    bl_description = t('CustomPanel.search_merge_into_desc')
    bl_property = "search_merge_armature_into_enum"

    # Define the enum property within the operator class
    search_merge_armature_into_enum: bpy.props.EnumProperty(
        name=t('CustomPanel.merge_into'),
        description=t('CustomPanel.merge_into_desc'),
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
    bl_description = t('CustomPanel.search_merge_desc')
    bl_property = "search_merge_armature_enum"

    search_merge_armature_enum: bpy.props.EnumProperty(
        name=t('CustomPanel.merge_from'),
        description=t('CustomPanel.merge_from_desc'),
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
    bl_description = t('CustomPanel.search_mesh_desc')
    bl_property = "search_attach_mesh_enum"

    search_attach_mesh_enum: bpy.props.EnumProperty(
        name=t('CustomPanel.attach_mesh'),
        description=t('CustomPanel.attach_mesh_desc'),
        items=lambda self, context: [
            (obj.name, obj.name, "")
            for obj in get_all_meshes(context)
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
    bl_description = t('CustomPanel.search_bone_desc')
    bl_property = "search_attach_bone_enum"

    search_attach_bone_enum: bpy.props.EnumProperty(
        name=t('CustomPanel.attach_bone'),
        description=t('CustomPanel.attach_bone_desc'),
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
    bl_order = 3
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context: Context) -> None:
        """Draw the custom avatar tools panel interface"""
        layout: UILayout = self.layout
        toolkit = context.scene.avatar_toolkit

        # Mode Selection Box
        mode_box: UILayout = layout.box()
        col: UILayout = mode_box.column(align=True)
        col.label(text=t('CustomPanel.merge_mode'), icon='TOOL_SETTINGS')
        col.separator(factor=0.5)

        # Create a row for the mode buttons with increased scale
        row: UILayout = col.row(align=True)
        row.scale_y = 1.5
        row.prop(toolkit, "merge_mode", expand=True)
        
        # Armature Merging Tools
        if toolkit.merge_mode == 'ARMATURE':
            self.draw_armature_tools(layout, context)
        # Mesh Attachment Tools    
        else:
            self.draw_mesh_tools(layout, context)

    def draw_armature_tools(self, layout: UILayout, context: Context) -> None:
        """Draw the armature merging tools section"""
        toolkit = context.scene.avatar_toolkit
        
        # Merge Settings Box
        settings_box: UILayout = layout.box()
        col: UILayout = settings_box.column(align=True)
        col.label(text=t('CustomPanel.mergeArmatures'), icon='ARMATURE_DATA')
        col.separator(factor=0.5)
        
        if len(get_armature_list(context)) <= 1:
            col.label(text=t('CustomPanel.warn.twoArmatures'), icon='INFO')
            return

        # Merge Options
        options_box: UILayout = layout.box()
        col: UILayout = options_box.column(align=True)
        col.label(text=t('Tools.merge_title'), icon='SETTINGS')
        col.separator(factor=0.5)
        col.prop(toolkit, "merge_all_bones")
        col.prop(toolkit, "apply_transforms")
        col.prop(toolkit, "join_meshes")
        col.prop(toolkit, "remove_zero_weights")
        col.prop(toolkit, "cleanup_shape_keys")

        # Armature Selection Box
        selection_box: UILayout = layout.box()
        col: UILayout = selection_box.column(align=True)
        col.label(text=t('QuickAccess.select_armature'), icon='BONE_DATA')
        col.separator(factor=0.5)
        
        row: UILayout = col.row(align=True)
        row.label(text=t('CustomPanel.mergeInto'))
        row.operator("avatar_toolkit.search_merge_armature_into",
                    text=toolkit.merge_armature_into,
                    icon='ARMATURE_DATA')

        row: UILayout = col.row(align=True)
        row.label(text=t('CustomPanel.toMerge'))
        row.operator("avatar_toolkit.search_merge_armature",
                    text=toolkit.merge_armature,
                    icon='ARMATURE_DATA')

        # Merge Button
        merge_col: UILayout = layout.column(align=True)
        merge_col.scale_y = 1.2
        merge_col.operator("avatar_toolkit.merge_armatures", icon='ARMATURE_DATA')

    def draw_mesh_tools(self, layout: UILayout, context: Context) -> None:
        """Draw the mesh attachment tools section"""
        toolkit = context.scene.avatar_toolkit
        
        # Mesh Tools Box
        tools_box: UILayout = layout.box()
        col: UILayout = tools_box.column(align=True)
        col.label(text=t('CustomPanel.attachMesh1'), icon='MESH_DATA')
        col.separator(factor=0.5)

        if not get_active_armature(context) or not get_all_meshes(context):
            col.label(text=t('CustomPanel.warn.noArmOrMesh1'), icon='INFO')
            col.label(text=t('CustomPanel.warn.noArmOrMesh2'))
            return

        # Mesh Options Box
        options_box: UILayout = layout.box()
        col: UILayout = options_box.column(align=True)
        col.label(text=t('Tools.merge_title'), icon='SETTINGS')
        col.separator(factor=0.5)
        col.prop(toolkit, "join_meshes")

        # Selection Box
        selection_box: UILayout = layout.box()
        col: UILayout = selection_box.column(align=True)
        col.label(text=t('Tools.merge_title'), icon='OBJECT_DATA')
        col.separator(factor=0.5)

        row: UILayout = col.row(align=True)
        row.label(text=t('CustomPanel.mergeInto'))
        row.operator("avatar_toolkit.search_merge_armature_into",
                    text=toolkit.merge_armature_into,
                    icon='ARMATURE_DATA')

        row: UILayout = col.row(align=True)
        row.label(text=t('CustomPanel.attachMesh2'))
        row.operator("avatar_toolkit.search_attach_mesh",
                    text=toolkit.attach_mesh,
                    icon='MESH_DATA')

        row: UILayout = col.row(align=True)
        row.label(text=t('CustomPanel.attachToBone'))
        row.operator("avatar_toolkit.search_attach_bone",
                    text=toolkit.attach_bone,
                    icon='BONE_DATA')

        # Attach Button
        attach_col: UILayout = layout.column(align=True)
        attach_col.scale_y = 1.2
        attach_col.operator("avatar_toolkit.attach_mesh", icon='ARMATURE_DATA')
