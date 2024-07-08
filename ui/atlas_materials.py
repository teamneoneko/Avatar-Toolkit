from bpy.types import UIList, Panel, UILayout, Object,Context,MaterialSlot
import bpy
from ..core.register import register_wrap
from .panel import AvatarToolkitPanel

@register_wrap
class MaterialTextureAtlasProperties(UIList):
    bl_label = "Texture Atlas Material List Material"
    bl_idname = "Material_UL_avatar_toolkit_texture_atlas_mat_list_mat"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'


    def draw_item(self, context: Context, layout: UILayout, data: bpy.types.Object, item:MaterialSlot, icon, active_data, active_propname, index):
        
        if item.material:
            box = layout.box()
            col = box.row()
            col.label(text="Material: \""+item.material.name+"\"")
            if data.active_material_index == index:
                col = box.row()
                col.prop(item.material, "texture_atlas_albedo")
                col = box.row()
                col.prop(item.material, "texture_atlas_normal")
                col = box.row()
                col.prop(item.material, "texture_atlas_emission")
                col = box.row()
                col.prop(item.material, "texture_atlas_ambient_occlusion")
                col = box.row()
                col.prop(item.material, "texture_atlas_height")
        else:
            box = layout.box()
            col = box.row()
            col.label(text="Empty Material Slot.")

@register_wrap
class MaterialListPanel(UIList):
    bl_label = "Texture Atlas Material List"
    bl_idname = "Material_UL_avatar_toolkit_texture_atlas_mat_list"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    
    def draw_item(self, context: Context, layout: UILayout, data, item:Object, icon, active_data, active_propname, index):
        custom_icon = "OBJECT_DATAMODE"
        box = layout.box()
        row = box.row()
        row.label(text=item.name, icon = custom_icon)
        if context.scene.texture_atlas_material_index == index:
            row = box.row()
            box = row.box()
            
            box.template_list("Material_UL_avatar_toolkit_texture_atlas_mat_list_mat", "The_Texture_Atlas_List_mat_"+item.name, item, "material_slots", item, "active_material_index")


@register_wrap
class TextureAtlasPanel(Panel):
    bl_label = "Texture Atlasing"
    bl_idname = "OBJECT_PT_avatar_toolkit_texture_atlas"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Avatar Toolkit"
    bl_parent_id = "OBJECT_PT_avatar_toolkit"

    def draw(self, context: Context):
        layout = self.layout
        row = layout.row()
        boxoutter = row.box()
        row = boxoutter.row()
        row.label(text=MaterialListPanel.bl_label)
        row = boxoutter.row()
        row.template_list("Material_UL_avatar_toolkit_texture_atlas_mat_list", "The_Texture_Atlas_List", context.scene, "objects", context.scene, "texture_atlas_material_index")
