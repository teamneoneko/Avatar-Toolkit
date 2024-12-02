from bpy.types import UIList, Panel, UILayout, Object, Context, Material, Operator
import bpy
from math import sqrt
from .main_panel import AvatarToolKit_PT_AvatarToolkitPanel, CATEGORY_NAME
from ..core.common import SceneMatClass, MaterialListBool, get_selected_armature
from ..functions.atlas_materials import AvatarToolKit_OT_AtlasMaterials
from ..core.translations import t

class AvatarToolKit_OT_SelectAllMaterials(Operator):
    bl_idname = 'avatar_toolkit.select_all_materials'
    bl_label = "Select All"
    bl_description = "Select all materials for atlas"

    def execute(self, context):
        for item in context.scene.avatar_toolkit.materials:
            item.mat.avatar_toolkit.include_in_atlas = True
        return {'FINISHED'}

class AvatarToolKit_OT_SelectNoneMaterials(Operator):
    bl_idname = 'avatar_toolkit.select_none_materials'
    bl_label = "Select None"
    bl_description = "Deselect all materials"

    def execute(self, context):
        for item in context.scene.avatar_toolkit.materials:
            item.mat.avatar_toolkit.include_in_atlas = False
        return {'FINISHED'}

class AvatarToolKit_OT_ExpandAllMaterials(Operator):
    bl_idname = 'avatar_toolkit.expand_all_materials'
    bl_label = "Expand All"
    bl_description = "Expand all material settings"

    def execute(self, context):
        for item in context.scene.avatar_toolkit.materials:
            item.mat.avatar_toolkit.material_expanded = True
        return {'FINISHED'}

class AvatarToolKit_OT_CollapseAllMaterials(Operator):
    bl_idname = 'avatar_toolkit.collapse_all_materials'
    bl_label = "Collapse All"
    bl_description = "Collapse all material settings"

    def execute(self, context):
        for item in context.scene.avatar_toolkit.materials:
            item.mat.avatar_toolkit.material_expanded = False
        return {'FINISHED'}

class AvatarToolKit_OT_ExpandSectionMaterials(Operator):
    bl_idname = 'avatar_toolkit.expand_section_materials'
    bl_label = ""
    bl_description = ""

    @classmethod
    def poll(cls, context: Context) -> bool:
        return True
        
    def execute(self, context: Context) -> set:
        if not context.scene.avatar_toolkit.texture_atlas_Has_Mat_List_Shown:
            context.scene.avatar_toolkit.materials.clear()
            newlist: list[Material] = []
            for obj in context.scene.objects:
                if len(obj.material_slots)>0:
                    for mat_slot in obj.material_slots:
                        if mat_slot.material:
                            if mat_slot.material not in newlist:
                                newlist.append(mat_slot.material)
                                newitem: SceneMatClass = context.scene.avatar_toolkit.materials.add()
                                newitem.mat = mat_slot.material
            MaterialListBool.old_list[context.scene.name] = newlist
        else:
            context.scene.avatar_toolkit.texture_atlas_Has_Mat_List_Shown = False
        return {'FINISHED'}

class AvatarToolKit_UL_MaterialTextureAtlasProperties(UIList):
    bl_label = t("TextureAtlas.material_list_label")
    bl_idname = "Material_UL_avatar_toolkit_texture_atlas_mat_list_mat"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'

    def draw_header(self, context):
        layout = self.layout
        row = layout.row(align=True)
        
        row.operator("avatar_toolkit.select_all_materials", text="", icon='CHECKBOX_HLT')
        row.operator("avatar_toolkit.select_none_materials", text="", icon='CHECKBOX_DEHLT')
        row.operator("avatar_toolkit.expand_all_materials", text="", icon='DISCLOSURE_TRI_DOWN')
        row.operator("avatar_toolkit.collapse_all_materials", text="", icon='DISCLOSURE_TRI_RIGHT')
        row.prop(context.scene.avatar_toolkit, "material_search_filter", text="", icon='VIEWZOOM')
        
        box = layout.box()
        row = box.row()
        row.label(text=f"Estimated Atlas Size: {self.calculate_atlas_size(context)}px")

    def draw_item(self, context: Context, layout: UILayout, data: Object, item: SceneMatClass, icon, active_data, active_propname, index):
        if context.scene.avatar_toolkit.texture_atlas_Has_Mat_List_Shown:
            if context.scene.avatar_toolkit.material_search_filter and context.scene.avatar_toolkit.material_search_filter.lower() not in item.mat.name.lower():
                return

            row = layout.row()
            
            row.prop(item.mat.avatar_toolkit, "include_in_atlas", text="", icon='CHECKBOX_HLT' if item.mat.avatar_toolkit.include_in_atlas else 'CHECKBOX_DEHLT')
            
            row.prop(item.mat.avatar_toolkit, "material_expanded", 
                    text=item.mat.name,
                    icon='DOWNARROW_HLT' if item.mat.avatar_toolkit.material_expanded else 'RIGHTARROW',
                    emboss=False)
            
            if item.mat.avatar_toolkit.material_expanded and item.mat.avatar_toolkit.include_in_atlas:
                box = layout.box()
                col = box.column(align=True)
                self.draw_texture_row(col, item.mat.avatar_toolkit, "texture_atlas_albedo", "IMAGE_RGB")
                self.draw_texture_row(col, item.mat.avatar_toolkit, "texture_atlas_normal", "NORMALS_FACE")
                self.draw_texture_row(col, item.mat.avatar_toolkit, "texture_atlas_emission", "LIGHT")
                self.draw_texture_row(col, item.mat.avatar_toolkit, "texture_atlas_ambient_occlusion", "SHADING_SOLID")
                self.draw_texture_row(col, item.mat.avatar_toolkit, "texture_atlas_height", "IMAGE_ZDEPTH")
                self.draw_texture_row(col, item.mat.avatar_toolkit, "texture_atlas_roughness", "MATERIAL")
                
                col.separator(factor=0.5)

    def draw_texture_row(self, layout, material, prop_name, icon):
        row = layout.row()
        row.prop(material, prop_name, icon=icon)
        if getattr(material, prop_name):
            row.label(text="", icon='CHECKMARK')
        else:
            row.label(text="", icon='X')

    def calculate_atlas_size(self, context):
        total_size = 0
        for mat in context.scene.avatar_toolkit.materials:
            if mat.mat.avatar_toolkit.include_in_atlas:
                if mat.mat.avatar_toolkit.texture_atlas_albedo:
                    img = bpy.data.images[mat.mat.avatar_toolkit.texture_atlas_albedo]
                    total_size += img.size[0] * img.size[1]
        return f"{int(sqrt(total_size))}x{int(sqrt(total_size))}"

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
            direction_icon = 'RIGHTARROW' if not context.scene.avatar_toolkit.texture_atlas_Has_Mat_List_Shown else 'DOWNARROW_HLT'
            row.operator(AvatarToolKit_OT_ExpandSectionMaterials.bl_idname, 
                        text=(t("TextureAtlas.reload_list") if not context.scene.avatar_toolkit.texture_atlas_Has_Mat_List_Shown else t("TextureAtlas.loaded_list")), 
                        icon=direction_icon)
            
            if context.scene.avatar_toolkit.texture_atlas_Has_Mat_List_Shown:
                row = box.row()
                row.template_list(AvatarToolKit_UL_MaterialTextureAtlasProperties.bl_idname, 
                                'material_list', 
                                context.scene.avatar_toolkit, 
                                'materials', 
                                context.scene.avatar_toolkit, 
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

