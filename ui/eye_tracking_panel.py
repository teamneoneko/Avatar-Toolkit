import bpy
from typing import Set
from bpy.types import Panel, Context, UILayout, Operator, Event, WindowManager
from .main_panel import AvatarToolKit_PT_AvatarToolkitPanel, CATEGORY_NAME
from ..core.translations import t
from ..core.common import get_active_armature, get_all_meshes
from ..functions.eye_tracking import (
    CreateEyesAV3Button,
    CreateEyesSDK2Button,
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
    bl_label: str = t("EyeTracking.label")
    bl_idname: str = "VIEW3D_PT_avatar_toolkit_eye_tracking"
    bl_space_type: str = 'VIEW_3D'
    bl_region_type: str = 'UI'
    bl_category: str = CATEGORY_NAME
    bl_parent_id: str = AvatarToolKit_PT_AvatarToolkitPanel.bl_idname
    bl_order: int = 6
    bl_options: Set[str] = {'DEFAULT_CLOSED'}

    def draw(self, context: Context) -> None:
        """Draw the eye tracking panel interface"""
        layout: UILayout = self.layout
        toolkit = context.scene.avatar_toolkit

        # SDK Version Selection Box
        sdk_box: UILayout = layout.box()
        col: UILayout = sdk_box.column(align=True)
        col.label(text=t("EyeTracking.sdk_version"), icon='PRESET')
        col.separator(factor=0.5)
        row: UILayout = col.row(align=True)
        row.prop(toolkit, "eye_tracking_type", expand=True)

        if toolkit.eye_tracking_type == 'SDK2':
            # Mode Selection Box
            mode_box: UILayout = layout.box()
            col: UILayout = mode_box.column(align=True)
            col.label(text=t("EyeTracking.setup"), icon='TOOL_SETTINGS')
            col.separator(factor=0.5)
            col.prop(toolkit, "eye_mode", expand=True)

            if toolkit.eye_mode == 'CREATION':
                self.draw_creation_mode(context, layout)
            else:
                self.draw_testing_mode(context, layout)
        else:
            # AV3 bone setup only
            self.draw_av3_setup(context, layout)

    def draw_av3_setup(self, context: Context, layout: UILayout) -> None:
        """Draw the AV3 eye tracking setup interface"""
        toolkit = context.scene.avatar_toolkit

        # Bone Setup Box
        bone_box: UILayout = layout.box()
        col: UILayout = bone_box.column(align=True)
        col.label(text=t("EyeTracking.bone_setup"), icon='BONE_DATA')
        col.separator(factor=0.5)

        armature = get_active_armature(context)
        if armature:
            col.prop_search(toolkit, "head", armature.data, "bones", text=t("EyeTracking.head_bone"))
            col.prop_search(toolkit, "eye_left", armature.data, "bones", text=t("EyeTracking.eye_left"))
            col.prop_search(toolkit, "eye_right", armature.data, "bones", text=t("EyeTracking.eye_right"))
        else:
            col.label(text=t("EyeTracking.no_armature"), icon='ERROR')

        # Create Button
        row: UILayout = layout.row(align=True)
        row.scale_y = 1.5
        row.operator(CreateEyesAV3Button.bl_idname, icon='PLAY')

    def draw_creation_mode(self, context: Context, layout: UILayout) -> None:
        """Draw the eye tracking creation mode interface"""
        toolkit = context.scene.avatar_toolkit

        # Bone Setup Box
        bone_box: UILayout = layout.box()
        col: UILayout = bone_box.column(align=True)
        col.label(text=t("EyeTracking.bone_setup"), icon='BONE_DATA')
        col.separator(factor=0.5)

        armature = get_active_armature(context)
        if armature:
            col.prop_search(toolkit, "head", armature.data, "bones", text=t("EyeTracking.head_bone"))
            col.prop_search(toolkit, "eye_left", armature.data, "bones", text=t("EyeTracking.eye_left"))
            col.prop_search(toolkit, "eye_right", armature.data, "bones", text=t("EyeTracking.eye_right"))
        else:
            col.label(text=t("EyeTracking.no_armature"), icon='ERROR')

        # Mesh Setup Box
        mesh_box: UILayout = layout.box()
        col: UILayout = mesh_box.column(align=True)
        col.label(text=t("EyeTracking.mesh_setup"), icon='MESH_DATA')
        col.separator(factor=0.5)
        col.prop_search(toolkit, "mesh_name_eye", bpy.data, "objects", text="")

        # Shape Key Setup Box
        shape_box: UILayout = layout.box()
        col: UILayout = shape_box.column(align=True)
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
        options_box: UILayout = layout.box()
        col: UILayout = options_box.column(align=True)
        col.label(text=t("EyeTracking.options"), icon='SETTINGS')
        col.separator(factor=0.5)
        col.prop(toolkit, "disable_eye_blinking")
        col.prop(toolkit, "disable_eye_movement")
        if not toolkit.disable_eye_movement:
            col.prop(toolkit, "eye_distance")

        # Create Button
        row: UILayout = layout.row(align=True)
        row.scale_y = 1.5
        row.operator(CreateEyesSDK2Button.bl_idname, icon='PLAY')

    def draw_testing_mode(self, context: Context, layout: UILayout) -> None:
        """Draw the eye tracking testing mode interface"""
        toolkit = context.scene.avatar_toolkit

        if context.mode != 'POSE':
            # Testing Start Box
            test_box: UILayout = layout.box()
            col: UILayout = test_box.column(align=True)
            col.label(text=t("EyeTracking.testing"), icon='PLAY')
            col.separator(factor=0.5)
            row: UILayout = col.row(align=True)
            row.scale_y = 1.5
            row.operator(StartTestingButton.bl_idname, icon='PLAY')
        else:
            # Eye Rotation Box
            rotation_box: UILayout = layout.box()
            col: UILayout = rotation_box.column(align=True)
            col.label(text=t("EyeTracking.rotation_controls"), icon='DRIVER_ROTATIONAL_DIFFERENCE')
            col.separator(factor=0.5)
            col.prop(toolkit, "eye_rotation_x", text=t("EyeTracking.rotation.x"))
            col.prop(toolkit, "eye_rotation_y", text=t("EyeTracking.rotation.y"))
            col.operator(ResetRotationButton.bl_idname, icon='LOOP_BACK')

            # Eye Adjustment Box
            adjust_box: UILayout = layout.box()
            col: UILayout = adjust_box.column(align=True)
            col.label(text=t("EyeTracking.adjustments"), icon='MODIFIER')
            col.separator(factor=0.5)
            col.prop(toolkit, "eye_distance")
            col.operator(AdjustEyesButton.bl_idname, icon='CON_TRACKTO')

            # Blinking Test Box
            blink_box: UILayout = layout.box()
            col: UILayout = blink_box.column(align=True)
            col.label(text=t("EyeTracking.blink_testing"), icon='HIDE_OFF')
            col.separator(factor=0.5)
            row: UILayout = col.row(align=True)
            row.prop(toolkit, "eye_blink_shape")
            row.operator(TestBlinking.bl_idname, icon='RESTRICT_VIEW_OFF')
            row: UILayout = col.row(align=True)
            row.prop(toolkit, "eye_lowerlid_shape")
            row.operator(TestLowerlid.bl_idname, icon='RESTRICT_VIEW_OFF')
            col.operator(ResetBlinkTest.bl_idname, icon='LOOP_BACK')

            # Stop Testing Button
            row: UILayout = layout.row(align=True)
            row.scale_y = 1.5
            row.operator(StopTestingButton.bl_idname, icon='PAUSE')

        # Reset Button
        row: UILayout = layout.row(align=True)
        row.operator(ResetEyeTrackingButton.bl_idname, icon='FILE_REFRESH')
