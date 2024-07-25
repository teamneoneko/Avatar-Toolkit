import bpy
from ..functions.translations import t, get_languages_list, update_ui
from ..core.register import register_property
from bpy.types import Scene, Object, Material, TextureNode, Context, SceneObjects, PropertyGroup
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, CollectionProperty, StringProperty, FloatVectorProperty, PointerProperty
from bpy.utils import register_class
from ..core.register import register_wrap
from ..core.addon_preferences import get_preference
from ..core.common import SceneMatClass, material_list_bool, get_armatures
    




def register() -> None:
    default_language = get_preference("language", 0)
    bpy.types.Scene.avatar_toolkit_language = bpy.props.EnumProperty(
        name=t("Settings.language.label", "Language"),
        description=t("Settings.language.desc", "Select the language for the addon"),
        items=get_languages_list,
        default=default_language,
        update=update_language
    )
    
    bpy.types.Scene.avatar_toolkit_language_changed = bpy.props.BoolProperty(default=False)

    bpy.types.Scene.selected_armature = bpy.props.EnumProperty(
        items=get_armatures,
        name="Selected Armature",
        description="The currently selected armature for Avatar Toolkit operations"
    )
    
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
    
    register_property((Material, "texture_atlas_albedo", EnumProperty(name="Albedo", description="The texture that will be used for the albedo map atlas", default=0, items=get_texture_node_list)))
    register_property((Material, "texture_atlas_normal", EnumProperty(name="Normal", description="The texture that will be used for the normal map atlas", default=0, items=get_texture_node_list)))
    register_property((Material, "texture_atlas_emission", EnumProperty(name="Emission", description="The texture that will be used for the emission map atlas", default=0, items=get_texture_node_list)))
    register_property((Material, "texture_atlas_ambient_occlusion", EnumProperty(name="Ambient Occlusion", description="The texture that will be used for the ambient occlusion map atlas", default=0, items=get_texture_node_list)))
    register_property((Material, "texture_atlas_height", EnumProperty(name="Height", description="The texture that will be used for the height map atlas", default=0, items=get_texture_node_list)))
    register_property((Material, "texture_atlas_roughness", EnumProperty(name="Roughness", description="The texture that will be used for the roughness map atlas", default=0, items=get_texture_node_list)))
    
    register_property((Scene, "texture_atlas_material_index", IntProperty(default=-1, get=(lambda self : -1), set=(lambda self,context : None))))

    register_property((Scene, "materials", CollectionProperty(type=SceneMatClass)))

    register_property((Scene, "texture_atlas_Has_Mat_List_Shown", BoolProperty(default=False, get=material_list_bool.get_bool, set=material_list_bool.set_bool)))


def unregister():
    if hasattr(bpy.types.Scene, "avatar_toolkit_language"):
        del bpy.types.Scene.avatar_toolkit_language
        
    if hasattr(bpy.types.Scene, "avatar_toolkit_language_changed"):
        del bpy.types.Scene.avatar_toolkit_language_changed

    if hasattr(bpy.types.Scene, "selected_armature"):
        del bpy.types.Scene.selected_armature
    
