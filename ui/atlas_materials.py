from bpy.types import UIList, Panel, UILayout, Object, Context,Material, Operator
import bpy
from ..core.register import register_wrap
from .panel import AvatarToolkitPanel
from ..core.properties import SceneMatClass, material_list_bool


@register_wrap
class ExpandSection_Materials(Operator):
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
            material_list_bool.old_list = newlist
        else:
            context.scene.texture_atlas_Has_Mat_List_Shown = False
        return {'FINISHED'}

@register_wrap
class MaterialTextureAtlasProperties(UIList):
    bl_label = "Texture Atlas Material List Material"
    bl_idname = "Material_UL_avatar_toolkit_texture_atlas_mat_list_mat"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'


    def draw_item(self , context: Context, layout: UILayout, data: bpy.types.Object, item:SceneMatClass, icon, active_data, active_propname, index):
        
        if context.scene.texture_atlas_Has_Mat_List_Shown:
            box = layout.box()
            row = box.row()
            row.label(text=item.mat.name, icon = "MATERIAL")
            col = box.row()
            col.prop(item.mat, "texture_atlas_albedo")
            col = box.row()
            col.prop(item.mat, "texture_atlas_normal")
            col = box.row()
            col.prop(item.mat, "texture_atlas_emission")
            col = box.row()
            col.prop(item.mat, "texture_atlas_ambient_occlusion")
            col = box.row()
            col.prop(item.mat, "texture_atlas_height")
            
                
        

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
        direction_icon = 'RIGHTARROW' if not context.scene.texture_atlas_Has_Mat_List_Shown else 'DOWNARROW_HLT'
        row = boxoutter.row()
        row.operator(ExpandSection_Materials.bl_idname, text=("Reload Texture Atlas Material List" if not context.scene.texture_atlas_Has_Mat_List_Shown else "Loaded Texture Atlas Material List"), icon=direction_icon)
        if context.scene.texture_atlas_Has_Mat_List_Shown:
            
            #get_texture_node_list(bpy.context)

            row = boxoutter.row()
            row.template_list(MaterialTextureAtlasProperties.bl_idname, 'material_list', context.scene, 'materials',
                            context.scene, 'texture_atlas_material_index', rows=12, type='DEFAULT')
        