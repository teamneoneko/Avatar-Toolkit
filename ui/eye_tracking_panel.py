import bpy
from typing import Set
from bpy.types import Panel, Context, UILayout, Operator
from .main_panel import AvatarToolKit_PT_AvatarToolkitPanel, CATEGORY_NAME
from ..core.translations import t
from ..core.common import get_active_armature, get_all_meshes
from ..functions.eye_tracking import (
    CreateEyesButton,
    StartTestingButton,
    StopTestingButton,
    ResetRotationButton,
    AdjustEyesButton,
    TestBlinking,
    TestLowerlid,
    ResetBlinkTest,
    ResetEyeTrackingButton,
    RotateEyeBonesForAv3Button
)

class AvatarToolKit_PT_EyeTrackingPanel(Panel):
    """Panel containing eye tracking setup and testing tools"""
    bl_label = t("EyeTracking.label")
    bl_idname = "VIEW3D_PT_avatar_toolkit_eye_tracking"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY_NAME
    bl_parent_id = AvatarToolKit_PT_AvatarToolkitPanel.bl_idname
    bl_order = 3
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context: Context) -> None:
        """Draw the eye tracking panel interface"""
        layout = self.layout
        toolkit = context.scene.avatar_toolkit

        # Mode Selection Box
        mode_box = layout.box()
        col = mode_box.column(align=True)
        col.label(text=t("EyeTracking.mode_select"), icon='TOOL_SETTINGS')
        col.separator(factor=0.5)
        col.prop(toolkit, "eye_mode", expand=True)

        if toolkit.eye_mode == 'CREATION':
            # Mesh Setup Box
            mesh_box = layout.box()
            col = mesh_box.column(align=True)
            col.label(text=t("EyeTracking.mesh_setup"), icon='MESH_DATA')
            col.separator(factor=0.5)
            col.prop(toolkit, "mesh_name_eye", text="")

            # Bone Setup Box
            bone_box = layout.box()
            col = bone_box.column(align=True)
            col.label(text=t("EyeTracking.bone_setup"), icon='BONE_DATA')
            col.separator(factor=0.5)

            armature = get_active_armature(context)
            if armature:
                col.prop_search(toolkit, "head", armature.data, "bones", text=t("EyeTracking.head_bone"))
                col.prop_search(toolkit, "eye_left", armature.data, "bones", text=t("EyeTracking.eye_left"))
                col.prop_search(toolkit, "eye_right", armature.data, "bones", text=t("EyeTracking.eye_right"))
            else:
                col.label(text=t("EyeTracking.no_armature"), icon='ERROR')

            # Shapekey Setup Box
            shape_box = layout.box()
            col = shape_box.column(align=True)
            col.label(text=t("EyeTracking.shapekey_setup"), icon='SHAPEKEY_DATA')
            col.separator(factor=0.5)

            mesh = bpy.data.objects.get(toolkit.mesh_name_eye)
            if mesh and mesh.data.shape_keys:
                col.prop_search(toolkit, "wink_left", mesh.data.shape_keys, "key_blocks", text=t("EyeTracking.wink_left"))
                col.prop_search(toolkit, "wink_right", mesh.data.shape_keys, "key_blocks", text=t("EyeTracking.wink_right"))
                col.prop_search(toolkit, "lowerlid_left", mesh.data.shape_keys, "key_blocks", text=t("EyeTracking.lowerlid_left"))
                col.prop_search(toolkit, "lowerlid_right", mesh.data.shape_keys, "key_blocks", text=t("EyeTracking.lowerlid_right"))
            else:
                col.label(text=t("EyeTracking.no_shapekeys"), icon='ERROR')

            # Options Box
            options_box = layout.box()
            col = options_box.column(align=True)
            col.label(text=t("EyeTracking.options"), icon='SETTINGS')
            col.separator(factor=0.5)
            col.prop(toolkit, "disable_eye_blinking")
            col.prop(toolkit, "disable_eye_movement")
            if not toolkit.disable_eye_movement:
                col.prop(toolkit, "eye_distance")

            # Create Button
            row = layout.row(align=True)
            row.scale_y = 1.5
            row.operator(CreateEyesButton.bl_idname, icon='PLAY')

        else:
            if context.mode != 'POSE':
                # Testing Start Box
                test_box = layout.box()
                col = test_box.column(align=True)
                col.label(text=t("EyeTracking.testing"), icon='PLAY')
                col.separator(factor=0.5)
                row = col.row(align=True)
                row.scale_y = 1.5
                row.operator(StartTestingButton.bl_idname, icon='PLAY')
            else:
                # Eye Rotation Box
                rotation_box = layout.box()
                col = rotation_box.column(align=True)
                col.label(text=t("EyeTracking.rotation_controls"), icon='DRIVER_ROTATIONAL_DIFFERENCE')
                col.separator(factor=0.5)
                col.prop(toolkit, "eye_rotation_x", text=t("EyeTracking.rotation.x"))
                col.prop(toolkit, "eye_rotation_y", text=t("EyeTracking.rotation.y"))
                col.operator(ResetRotationButton.bl_idname, icon='LOOP_BACK')

                # Eye Adjustment Box
                adjust_box = layout.box()
                col = adjust_box.column(align=True)
                col.label(text=t("EyeTracking.adjustments"), icon='MODIFIER')
                col.separator(factor=0.5)
                col.prop(toolkit, "eye_distance")
                col.operator(AdjustEyesButton.bl_idname, icon='CON_TRACKTO')

                # Blinking Test Box
                blink_box = layout.box()
                col = blink_box.column(align=True)
                col.label(text=t("EyeTracking.blink_testing"), icon='HIDE_OFF')
                col.separator(factor=0.5)
                row = col.row(align=True)
                row.prop(toolkit, "eye_blink_shape")
                row.operator(TestBlinking.bl_idname, icon='RESTRICT_VIEW_OFF')
                row = col.row(align=True)
                row.prop(toolkit, "eye_lowerlid_shape")
                row.operator(TestLowerlid.bl_idname, icon='RESTRICT_VIEW_OFF')
                col.operator(ResetBlinkTest.bl_idname, icon='LOOP_BACK')

                # Stop Testing Button
                row = layout.row(align=True)
                row.scale_y = 1.5
                row.operator(StopTestingButton.bl_idname, icon='PAUSE')

        # Reset Button
        row = layout.row(align=True)
        row.operator(ResetEyeTrackingButton.bl_idname, icon='FILE_REFRESH')
