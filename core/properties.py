import bpy
from bpy.types import Scene, PropertyGroup, Object, Material, TextureNode, Context
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, CollectionProperty, StringProperty, FloatVectorProperty, PointerProperty
from bpy.utils import register_class



def register_properties():

    #happy with how compressed this get_texture_node_list method is - @989onan
    def get_texture_node_list(self: Material, context: Context) -> list[set[3]]:
        if self.use_nodes:
            Object.Enum = [(i.name+"_image",(i.image.name if i.image else "node with no image..."),i.name,index+1) for index,i in enumerate(self.node_tree.nodes) if i.bl_idname == "ShaderNodeTexImage"]
            if not len(Object.Enum):
                Object.Enum = [("ERROR", "THIS MATERIAL HAS NO IMAGES!", "ERROR", 0)]
        else:
            Object.Enum = [("ERROR", "THIS MATERIAL DOES NOT USE NODES!", "ERROR", 0)]
        Object.Enum.append(("None", "None", "None", 0))
        return Object.Enum

        
    Material.texture_atlas_normal = EnumProperty(name="Normal", description="The texture that will be used for the normal map atlas", default=0, items=get_texture_node_list)
    Material.texture_atlas_albedo = EnumProperty(name="Albedo", description="The texture that will be used for the albedo map atlas", default=0, items=get_texture_node_list)
    Material.texture_atlas_emission = EnumProperty(name="Emission", description="The texture that will be used for the emission map atlas", default=0, items=get_texture_node_list)
    Material.texture_atlas_ambient_occlusion = EnumProperty(name="Ambient Occlusion", description="The texture that will be used for the ambient occlusion map atlas", default=0, items=get_texture_node_list)
    Material.texture_atlas_height = EnumProperty(name="Height", description="The texture that will be used for the height map atlas", default=0, items=get_texture_node_list)
    
    Scene.texture_atlas_material_index = IntProperty()#default=-1, get=(lambda self : -1), set=(lambda self,context : None)

    #class Texture_Atlas_PropertyGroup(PropertyGroup):
    #    materials: CollectionProperty(type=Material)
    #register_class(Texture_Atlas_PropertyGroup)

    #Scene.texture_atlas_properties = PointerProperty(type=Texture_Atlas_PropertyGroup)


    