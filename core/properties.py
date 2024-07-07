from bpy.types import Scene, PropertyGroup, Object, Material, TextureNode
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, CollectionProperty, StringProperty, FloatVectorProperty, PointerProperty
from bpy.utils import register_class



def register_properties():
    class Material_Texture_Atlas_PropertyGroup(PropertyGroup):
        normal: PointerProperty(type=TextureNode)
        albedo: PointerProperty(type=TextureNode)
        emission: PointerProperty(type=TextureNode)
        ambient_occlusion: PointerProperty(type=TextureNode)
        height: PointerProperty(type=TextureNode)
        

    register_class(Material_Texture_Atlas_PropertyGroup)
    Material.texture_atlas = PointerProperty(type=Material_Texture_Atlas_PropertyGroup)

    class Texture_Atlas_PropertyGroup(PropertyGroup):
        materials: CollectionProperty(type=Material)

    Scene.texture_atlas_properties = PointerProperty(type=Texture_Atlas_PropertyGroup)


    