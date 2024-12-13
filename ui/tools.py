import bpy
from ..core.register import register_wrap
from .panel import AvatarToolKit_PT_AvatarToolkitPanel, CATEGORY_NAME
from bpy.types import Context
from ..functions.digitigrade_legs import AvatarToolKit_OT_CreateDigitigradeLegs
from ..core.resonite_utils import AvatarToolKit_OT_ConvertToResonite
from ..functions.translations import t
from ..core.common import get_selected_armature
from ..functions.mesh_tools import AvatarToolkit_OT_RemoveUnusedShapekeys
from ..functions.additional_tools import AvatarToolKit_OT_ApplyTransforms, AvatarToolKit_OT_ConnectBones, AvatarToolKit_OT_DeleteBoneConstraints, AvatarToolKit_OT_SeparateByMaterials, AvatarToolKit_OT_SeparateByLooseParts
from ..functions.armature_modifying import AvatarToolkit_OT_RemoveZeroWeightBones, AvatarToolkit_OT_MergeBonesToActive, AvatarToolkit_OT_MergeBonesToParents
from ..functions.rigify_functions import AvatarToolKit_OT_ConvertRigifyToUnity

@register_wrap
class AvatarToolkit_PT_ToolsPanel(bpy.types.Panel):
    bl_label = t("Tools.label")
    bl_idname = "OBJECT_PT_avatar_toolkit_tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY_NAME
    bl_parent_id = AvatarToolKit_PT_AvatarToolkitPanel.bl_idname
    bl_order = 3

    def draw(self, context: Context):
        layout = self.layout
        armature = get_selected_armature(context)
        
        if armature:
            layout.label(text=t("Tools.tools_title.label"), icon='TOOL_SETTINGS')
            layout.separator(factor=0.5)

            row = layout.row(align=True)
            row.scale_y = 1.5  
            row.operator(AvatarToolKit_OT_ConvertToResonite.bl_idname, text=t("Tools.convert_to_resonite.label"), icon='SCENE_DATA')
            
            row = layout.row(align=True)
            row.scale_y = 1.5
            row.operator(AvatarToolKit_OT_ConvertRigifyToUnity.bl_idname, text=t("Tools.convert_rigify_to_unity.label"), icon='ARMATURE_DATA')
            
            layout.separator(factor=1.0)
            
            layout.label(text=t("Tools.separate_by.label"), icon='MESH_DATA')
            row = layout.row(align=True)
            row.operator(AvatarToolKit_OT_SeparateByMaterials.bl_idname, text=t("Tools.separate_by_materials.label"), icon='MATERIAL')
            row.operator(AvatarToolKit_OT_SeparateByLooseParts.bl_idname, text=t("Tools.separate_by_loose_parts.label"), icon='OUTLINER_OB_MESH')
            
            layout.separator(factor=1.0)
            
            layout.label(text=t("Tools.bone_tools.label"), icon='BONE_DATA')
            row = layout.row(align=True)
            row.operator(AvatarToolKit_OT_CreateDigitigradeLegs.bl_idname, text=t("Tools.create_digitigrade_legs.label"), icon='BONE_DATA')
            
            row = layout.row(align=True)
            row.operator(AvatarToolkit_OT_RemoveZeroWeightBones.bl_idname, text=t("Tools.remove_zero_weight_bones.label"), icon='BONE_DATA')
            
            row = layout.row(align=True)
            row.operator(AvatarToolkit_OT_MergeBonesToActive.bl_idname, text=t("Tools.merge_bones_to_active.label"), icon='BONE_DATA')
            row.operator(AvatarToolkit_OT_MergeBonesToParents.bl_idname, text=t("Tools.merge_bones_to_parents.label"), icon='BONE_DATA')
            
            row = layout.row(align=True)
            row.operator(AvatarToolKit_OT_ConnectBones.bl_idname, text=t("Tools.connect_bones.label"), icon='BONE_DATA')
            row.operator(AvatarToolKit_OT_DeleteBoneConstraints.bl_idname, text=t("Tools.delete_bone_constraints.label"), icon='CONSTRAINT_BONE')
            
            row = layout.row()
            row.prop(context.scene, "merge_twist_bones")
            
            layout.separator(factor=1.0)
            
            layout.label(text=t("Tools.additional_tools.label"), icon='TOOL_SETTINGS')
            row = layout.row(align=True)
            row.operator(AvatarToolKit_OT_ApplyTransforms.bl_idname, text=t("Tools.apply_transforms.label"), icon='OBJECT_ORIGIN')
            row.operator(AvatarToolkit_OT_RemoveUnusedShapekeys.bl_idname, text=t("Tools.remove_unused_shapekeys.label"), icon='SHAPEKEY_DATA')
            
            layout.separator(factor=1.0) 
        else:
            layout.label(text=t("Tools.select_armature"), icon='ERROR')
