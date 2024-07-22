import bpy
from ..functions.translations import t, get_languages_list, update_ui
from ..core.register import register_property
from typing import Tuple
from bpy.types import Scene, PropertyGroup, Object, Material, TextureNode, Context, SceneObjects
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, CollectionProperty, StringProperty, FloatVectorProperty, PointerProperty
from bpy.utils import register_class


class material_list_bool:
    #For the love that is holy do not ever touch these. If this was java I would make these private
    #They should only be accessed via context.scene.texture_atlas_Has_Mat_List_Shown
    #This is so we know if the materials are up to date. messing with these variables directly will make the thing blow up.
    
    #The only exception to this is the ExpandSection_Materials operator which populates this with new data once the materials have changed and need reloading.
    old_list: dict[str,list[Material]] = {}
    bool_material_list_expand: dict[str,bool] = {}

    def set_bool(self, value: bool) -> None:
        material_list_bool.bool_material_list_expand[bpy.context.scene.name] = value
        if value == False:
            material_list_bool.old_list[bpy.context.scene.name] = []

    def get_bool(self) -> bool:
            newlist: list[Material] = []
            for obj in bpy.context.scene.objects:
                if len(obj.material_slots)>0:
                    for mat_slot in obj.material_slots:
                        if mat_slot.material:
                            if mat_slot.material not in newlist:
                                newlist.append(mat_slot.material)
            
            still_the_same: bool = True
            if bpy.context.scene.name in material_list_bool.old_list:
                for item in newlist:
                    if item not in material_list_bool.old_list[bpy.context.scene.name]:
                        still_the_same = False
                        break
                for item in material_list_bool.old_list[bpy.context.scene.name]:
                    if item not in newlist:
                        still_the_same = False
                        break
            else:
                still_the_same = False
            material_list_bool.bool_material_list_expand[bpy.context.scene.name] = still_the_same
            
            return material_list_bool.bool_material_list_expand[bpy.context.scene.name]

class SceneMatClass(PropertyGroup):
    mat: PointerProperty(type=Material)

def register() -> None:
    register_property((Scene, "language", bpy.props.EnumProperty(
        name=t("Settings.language.label"),
        description=t("Settings.language.desc"),
        items=get_languages_list,
        update=update_ui
    )))
    
    register_class(SceneMatClass)

    #happy with how compressed this get_texture_node_list method is - @989onan
    def get_texture_node_list(self: Material, context: Context) -> list[set[3]]:
        if self.use_nodes:
            Object.Enum = [((i.image.name if i.image else i.name+"_image"),(i.image.name if i.image else "node with no image..."),(i.image.name if i.image else i.name),index+1) for index,i in enumerate(self.node_tree.nodes) if i.bl_idname == "ShaderNodeTexImage"]
            if not len(Object.Enum):
                Object.Enum = [("ERROR", "THIS MATERIAL HAS NO IMAGES!", "ERROR", 0)]
        else:
            Object.Enum = [("ERROR", "THIS MATERIAL DOES NOT USE NODES!", "ERROR", 0)]
        Object.Enum.append(("None", "None", "None", 0))
        return Object.Enum

        
    
    register_property(Material, "texture_atlas_albedo", EnumProperty(name="Albedo", description="The texture that will be used for the albedo map atlas", default=0, items=get_texture_node_list))
    register_property(Material, "texture_atlas_normal", EnumProperty(name="Normal", description="The texture that will be used for the normal map atlas", default=0, items=get_texture_node_list))
    register_property(Material, "texture_atlas_emission", EnumProperty(name="Emission", description="The texture that will be used for the emission map atlas", default=0, items=get_texture_node_list))
    register_property(Material, "texture_atlas_ambient_occlusion", EnumProperty(name="Ambient Occlusion", description="The texture that will be used for the ambient occlusion map atlas", default=0, items=get_texture_node_list))
    register_property(Material, "texture_atlas_height", EnumProperty(name="Height", description="The texture that will be used for the height map atlas", default=0, items=get_texture_node_list))
    register_property(Material, "texture_atlas_roughness", EnumProperty(name="Roughness", description="The texture that will be used for the roughness map atlas", default=0, items=get_texture_node_list))
    
    register_property(Scene, "texture_atlas_material_index", IntProperty(default=-1, get=(lambda self : -1), set=(lambda self,context : None)))

    


    register_property(Scene, "materials", CollectionProperty(type=SceneMatClass))

    register_property(Scene, "texture_atlas_Has_Mat_List_Shown", BoolProperty(default=False, get=material_list_bool.get_bool, set=material_list_bool.set_bool))

def unregister() -> None:
    pass
