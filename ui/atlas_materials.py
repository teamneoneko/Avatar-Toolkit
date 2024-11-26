from bpy.types import UIList, Panel, UILayout, Object, Context,Material, Operator
import bpy
from ..core.register import register_wrap
from .panel import AvatarToolKit_PT_AvatarToolkitPanel, CATEGORY_NAME
from ..core.common import SceneMatClass, MaterialListBool, get_selected_armature
from ..functions.atlas_materials import AvatarToolKit_OT_AtlasMaterials
from ..functions.translations import t

@register_wrap
class AvatarToolKit_OT_ExpandSectionMaterials(Operator):
    bl_idname = 'avatar_toolkit.expand_section_materials'
    bl_label = ""
    bl_description = ""

    @classmethod
    def poll(cls, context: Context) -> bool:
        return True
        
    def execute(self, context: Context) -> set:
        if not context.scene.texture_atlas_Has_Mat_List_Shown:
            context.scene.materials.clear()
            newlist: list[Material] = []
            for obj in bpy.context.scene.objects:
                if len(obj.material_slots)>0:
                    for mat_slot in obj.material_slots:
                        if mat_slot.material:
                            if mat_slot.material not in newlist:
                                newlist.append(mat_slot.material)
                                newitem: SceneMatClass = context.scene.materials.add()
                                newitem.mat = mat_slot.material
            MaterialListBool.old_list[context.scene.name] = newlist
        else:
            context.scene.texture_atlas_Has_Mat_List_Shown = False
        return {'FINISHED'}

@register_wrap
class AvatarToolKit_UL_MaterialTextureAtlasProperties(UIList):
    bl_label = t("TextureAtlas.material_list_label")
    bl_idname = "Material_UL_avatar_toolkit_texture_atlas_mat_list_mat"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'

    def draw_item(self, context: Context, layout: UILayout, data: Object, item: SceneMatClass, icon, active_data, active_propname, index):
        if context.scene.texture_atlas_Has_Mat_List_Shown:
            box = layout.box()
            row = box.row()
            
            # Draw material entry
            row.prop(item.mat, "material_expanded", 
                    text=item.mat.name,
                    icon='DOWNARROW_HLT' if item.mat.material_expanded else 'RIGHTARROW',
                    emboss=False)
            row.prop(item.mat, "include_in_atlas", text="")
            
            if item.mat.material_expanded and item.mat.include_in_atlas:
                col = box.column(align=True)
                col.prop(item.mat, "texture_atlas_albedo")
                col.prop(item.mat, "texture_atlas_normal")
                col.prop(item.mat, "texture_atlas_emission")
                col.prop(item.mat, "texture_atlas_ambient_occlusion")
                col.prop(item.mat, "texture_atlas_height")
                col.prop(item.mat, "texture_atlas_roughness")

@register_wrap
class AvatarToolKit_PT_TextureAtlasPanel(Panel):
    bl_label = t("TextureAtlas.label")
    bl_idname = "OBJECT_PT_avatar_toolkit_texture_atlas"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY_NAME
    bl_parent_id = AvatarToolKit_PT_AvatarToolkitPanel.bl_idname
    bl_order = 6

    def draw(self, context: Context):
        layout = self.layout
        armature = get_selected_armature(context)
        
        if armature:
            layout.label(text=t("TextureAtlas.label"), icon='TEXTURE')
            layout.separator(factor=0.5)
            
            box = layout.box()
            row = box.row()
            direction_icon = 'RIGHTARROW' if not context.scene.texture_atlas_Has_Mat_List_Shown else 'DOWNARROW_HLT'
            row.operator(AvatarToolKit_OT_ExpandSectionMaterials.bl_idname, 
                        text=(t("TextureAtlas.reload_list") if not context.scene.texture_atlas_Has_Mat_List_Shown else t("TextureAtlas.loaded_list")), 
                        icon=direction_icon)
            
            if context.scene.texture_atlas_Has_Mat_List_Shown:
                row = box.row()
                row.template_list(AvatarToolKit_UL_MaterialTextureAtlasProperties.bl_idname, 
                                'material_list', 
                                context.scene, 
                                'materials', 
                                context.scene, 
                                'texture_atlas_material_index', 
                                rows=12, 
                                type='DEFAULT')
            
            layout.separator(factor=1.0)
            
            row = layout.row()
            row.scale_y = 1.5
            row.operator(AvatarToolKit_OT_AtlasMaterials.bl_idname, 
                        text=t("TextureAtlas.atlas_materials"), 
                        icon='NODE_TEXTURE')
        else:
            layout.label(text=t("Tools.select_armature"), icon='ERROR')

