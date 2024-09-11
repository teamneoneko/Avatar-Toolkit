import bpy
from ..functions.translations import t, get_languages_list, update_language
from ..core.register import register_property
from bpy.types import Scene, Object, Material, Context
from bpy.props import BoolProperty, EnumProperty, IntProperty, CollectionProperty, StringProperty, FloatVectorProperty, PointerProperty
from ..core.addon_preferences import get_preference
from ..core.common import SceneMatClass, MaterialListBool, get_armatures, get_mesh_items

def register() -> None:
    default_language = get_preference("language", 0)
    register_property((bpy.types.Scene, "avatar_toolkit_language", bpy.props.EnumProperty(
        name=t("Settings.language.label", "Language"),
        description=t("Settings.language.desc", "Select the language for the addon"),
        items=get_languages_list,
        default=default_language,
        update=update_language
    )))

    register_property((bpy.types.Scene, "selected_mesh", bpy.props.EnumProperty(
        items=get_mesh_items,
        name=t("VisemePanel.selected_mesh.label"),
        description=t("VisemePanel.selected_mesh.desc")
    )))
    
    register_property((bpy.types.Scene, "avatar_toolkit_language_changed", bpy.props.BoolProperty(default=False)))

    register_property((bpy.types.Scene, "avatar_toolkit_progress_steps", bpy.props.IntProperty(default=0)))
    register_property((bpy.types.Scene, "avatar_toolkit_progress_current", bpy.props.IntProperty(default=0)))

    register_property((bpy.types.Scene, "avatar_toolkit_mouth_a", bpy.props.StringProperty(
        name=t("VisemePanel.mouth_a.label"),
        description=t("VisemePanel.mouth_a.desc")
    )))
    register_property((bpy.types.Scene, "avatar_toolkit_mouth_o", bpy.props.StringProperty(
        name=t("VisemePanel.mouth_o.label"),
        description=t("VisemePanel.mouth_o.desc")
    )))
    register_property((bpy.types.Scene, "avatar_toolkit_mouth_ch", bpy.props.StringProperty(
        name=t("VisemePanel.mouth_ch.label"),
        description=t("VisemePanel.mouth_ch.desc")
    )))
    register_property((bpy.types.Scene, "avatar_toolkit_shape_intensity", bpy.props.FloatProperty(
        name=t("VisemePanel.shape_intensity"),
        description=t("VisemePanel.shape_intensity_desc"),
        default=1.0,
        min=0.0,
        max=2.0
    )))

    register_property((bpy.types.Scene, "selected_armature", bpy.props.EnumProperty(
        items=get_armatures,
        name="Selected Armature",
        description="The currently selected armature for Avatar Toolkit operations"
    )))
    
    #happy with how compressed this get_texture_node_list method is - @989onan
    def get_texture_node_list(self: Material, context: Context) -> list[set[3]]:
        
        if self.use_nodes:
            
            Object.Enum = [((i.image.name if i.image else i.name+"_image"),(i.image.name if i.image else "node with no image..."),(i.image.name if i.image else i.name),index+1) for index,i in enumerate(self.node_tree.nodes) if i.bl_idname == "ShaderNodeTexImage"]
            if not len(Object.Enum):
                Object.Enum = [(t("TextureAtlas.error.label"), t("TextureAtlas.no_images_error.desc") , t("TextureAtlas.error.label"), 0)]
        else:
            Object.Enum = [(t("TextureAtlas.error.label"), t("TextureAtlas.no_nodes_error.desc"), t("TextureAtlas.error.label"), 0)]
        Object.Enum.append((t("TextureAtlas.none.label"), t("TextureAtlas.none.label"), t("TextureAtlas.none.label"), 0))
        return Object.Enum
    
    register_property((Material, "texture_atlas_albedo", EnumProperty(
        name=t("TextureAtlas.albedo"), 
        description=t("TextureAtlas.texture_use_atlas.desc").format(name=t("TextureAtlas.albedo").lower()), 
        default=0, 
        items=get_texture_node_list)))
    register_property((Material, "texture_atlas_normal", EnumProperty(
        name=t("TextureAtlas.normal"), 
        description=t("TextureAtlas.texture_use_atlas.desc").format(name=t("TextureAtlas.normal").lower()), 
        default=0, 
        items=get_texture_node_list)))
    register_property((Material, "texture_atlas_emission", EnumProperty(
        name=t("TextureAtlas.emission"), 
        description=t("TextureAtlas.texture_use_atlas.desc").format(name=t("TextureAtlas.emission").lower()), 
        default=0, 
        items=get_texture_node_list)))
    register_property((Material, "texture_atlas_ambient_occlusion", EnumProperty(
        name=t("TextureAtlas.ambient_occlusion"), 
        description=t("TextureAtlas.texture_use_atlas.desc").format(name=t("TextureAtlas.ambient_occlusion").lower()), 
        default=0, 
        items=get_texture_node_list)))
    register_property((Material, "texture_atlas_height", EnumProperty(
        name=t("TextureAtlas.height"),
        description=t("TextureAtlas.texture_use_atlas.desc").format(name=t("TextureAtlas.height_map").lower()), 
        default=0, 
        items=get_texture_node_list)))
    register_property((Material, "texture_atlas_roughness", EnumProperty(
        name=t("TextureAtlas.roughness"), 
        description=t("TextureAtlas.texture_use_atlas.desc").format(name=t("TextureAtlas.roughness").lower()), 
        default=0, 
        items=get_texture_node_list)))
    
    register_property((Scene, "texture_atlas_material_index", IntProperty(
        default=-1, 
        get=(lambda self : -1), 
        set=(lambda self,context : None))))

    register_property((Scene, "materials", CollectionProperty(type=SceneMatClass)))

    register_property((Scene, "texture_atlas_Has_Mat_List_Shown", BoolProperty(
        default=False,
        get=MaterialListBool.get_bool, 
        set=MaterialListBool.set_bool)))


def unregister() -> None:
    #if you register properties with register_property then you shouldn't need this function.
    pass
