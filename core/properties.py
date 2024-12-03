import bpy
from .translations import t, get_languages_list, update_language
from bpy.types import PropertyGroup, Material, Scene, Object, Context
from bpy.props import (StringProperty, BoolProperty, EnumProperty, 
                      IntProperty, FloatProperty, CollectionProperty,
                      PointerProperty)
from .addon_preferences import get_preference
from .common import SceneMatClass, MaterialListBool, get_armatures, get_mesh_items, get_armatures_that_are_not_selected
from .updater import get_version_list

class AvatarToolkitSceneProperties(PropertyGroup):
    language: EnumProperty(
        name="Language",
        description="Select the language for the addon",
        items=get_languages_list,
        update=update_language
    )
    
    selected_mesh: EnumProperty(
        items=get_mesh_items,
        name="Selected Mesh",
        description="Select mesh to modify"
    )

    material_search_filter: StringProperty(
        name="Search Materials",
        description="Filter materials by name",
        default=""
    )

    merge_armature_apply_transforms: BoolProperty(
        default=False,
        name="Apply Transforms",
        description="Apply transforms when merging armatures"
    )

    merge_armature_align_bones: BoolProperty(
        default=False,
        name="Align Bones",
        description="Align bones when merging armatures"
    )

    progress_steps: IntProperty(default=0)
    progress_current: IntProperty(default=0)
    language_changed: BoolProperty(default=False)

    mouth_a: StringProperty(
        name="Mouth A",
        description="Shape key for A sound"
    )

    mouth_o: StringProperty(
        name="Mouth O",
        description="Shape key for O sound"
    )

    mouth_ch: StringProperty(
        name="Mouth CH",
        description="Shape key for CH sound"
    )

    shape_intensity: FloatProperty(
        name="Shape Intensity",
        description="Intensity of shape key modifications",
        default=1.0,
        min=0.0,
        max=2.0
    )

    merge_twist_bones: BoolProperty(
        name="Merge Twist Bones",
        description="Merge twist bones during processing",
        default=True
    )

    selected_armature: EnumProperty(
        items=get_armatures,
        name="Selected Armature",
        description="Select the armature to work with"
    )

    merge_armature_source: EnumProperty(
        items=get_armatures_that_are_not_selected,
        name="Source Armature",
        description="Select the source armature for merging"
    )

    texture_atlas_material_index: IntProperty(
        default=-1,
        get=lambda self: -1,
        set=lambda self, context: None
    )

    materials: CollectionProperty(type=SceneMatClass)
    
    texture_atlas_Has_Mat_List_Shown: BoolProperty(
        default=False,
        get=MaterialListBool.get_bool,
        set=MaterialListBool.set_bool
    )

    avatar_toolkit_updater_version_list: EnumProperty(
        items=get_version_list,
        name="Version List",
        description="List of available versions"
    )


class AvatarToolkitMaterialProperties(PropertyGroup):
    material_expanded: BoolProperty(
        name="Expand Material",
        description="Show/hide material properties",
        default=False
    )

    include_in_atlas: BoolProperty(
        name="Include in Atlas",
        description="Include this material in texture atlas",
        default=True
    )

    def get_texture_node_list(self, context):
        # Access the material through the property group's id_data
        material = self.id_data
        if material and material.use_nodes:
            nodes = [(i.image.name if i.image else i.name+"_image",
                    i.image.name if i.image else "node with no image...",
                    i.image.name if i.image else i.name, index+1)
                    for index, i in enumerate(material.node_tree.nodes)
                    if i.bl_idname == "ShaderNodeTexImage"]
            if not nodes:
                nodes = [("Error", "No images found", "Error", 0)]
        else:
            nodes = [("Error", "No node tree found", "Error", 0)]
        nodes.append(("None", "None", "None", 0))
        return nodes

    texture_atlas_albedo: EnumProperty(
        name="Albedo",
        description="Albedo texture for atlas",
        items=get_texture_node_list
    )

    texture_atlas_normal: EnumProperty(
        name="Normal",
        description="Normal map for atlas",
        items=get_texture_node_list
    )

    texture_atlas_emission: EnumProperty(
        name="Emission",
        description="Emission texture for atlas",
        items=get_texture_node_list
    )

    texture_atlas_ambient_occlusion: EnumProperty(
        name="Ambient Occlusion",
        description="AO texture for atlas",
        items=get_texture_node_list
    )

    texture_atlas_height: EnumProperty(
        name="Height",
        description="Height map for atlas",
        items=get_texture_node_list
    )

    texture_atlas_roughness: EnumProperty(
        name="Roughness",
        description="Roughness map for atlas",
        items=get_texture_node_list
    )

class AvatarToolkitObjectProperties(PropertyGroup):
    material_group_expanded: BoolProperty(
        name="Expand Material Group",
        description="Show/hide materials for this mesh",
        default=False
    )

def register():
    bpy.types.Scene.avatar_toolkit = PointerProperty(type=AvatarToolkitSceneProperties)
    bpy.types.Material.avatar_toolkit = PointerProperty(type=AvatarToolkitMaterialProperties)
    bpy.types.Object.avatar_toolkit = PointerProperty(type=AvatarToolkitObjectProperties)

def unregister():
    del bpy.types.Scene.avatar_toolkit
    del bpy.types.Material.avatar_toolkit
    del bpy.types.Object.avatar_toolkit
