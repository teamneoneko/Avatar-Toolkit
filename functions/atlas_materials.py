from pathlib import Path

import numpy
import bpy
import os
from typing import List, Tuple, Optional
from bpy.types import Material, Operator, Context, Object, Image, Mesh, MeshUVLoopLayer, Float2AttributeValue, ShaderNodeTexImage, ShaderNodeBsdfPrincipled, ShaderNodeNormalMap
from ..core.common import SceneMatClass, MaterialListBool
from ..core.packer.rectangle_packer import MaterialImageList, BinPacker
from ..core.translations import t

class MaterialImageList:
    def __init__(self):
        self.albedo: Image = None
        self.normal: Image = None
        self.emission: Image = None
        self.ambient_occlusion: Image = None
        self.height: Image = None
        self.roughness: Image = None
        self.material: Material = None
        self.parent_mesh: Object = None
        self.w: int = 0
        self.h: int = 0
        self.fit = None

def scale_images_to_largest(images: list[Image]) -> tuple[int, int]:
    try:
        valid_images = []
        for img in images:
            if img and hasattr(img, 'name'):
                image_data = bpy.data.images.get(img.name)
                if image_data and image_data.has_data:
                    valid_images.append(image_data)
    
        if not valid_images:
            return 1, 1
            
        max_width = max(img.size[0] for img in valid_images)
        max_height = max(img.size[1] for img in valid_images)
        
        return max_width, max_height
    except:
        return 1, 1

def MaterialImageList_to_Image_list(classitem: MaterialImageList) -> list[Image]:
    list_of_images: list[Image] = []

    list_of_images.append(classitem.albedo)
    list_of_images.append(classitem.normal)
    list_of_images.append(classitem.emission)
    list_of_images.append(classitem.ambient_occlusion)
    list_of_images.append(classitem.height)
    list_of_images.append(classitem.roughness)

    return list_of_images


def get_material_images_from_scene(context: Context) -> list[MaterialImageList]:
    material_image_list: list[MaterialImageList] = []
    
    for obj in context.scene.objects:
        if obj.type == 'MESH':
            for mat_slot in obj.material_slots:
                # Only process materials that are selected for atlas
                if mat_slot.material and mat_slot.material.avatar_toolkit.include_in_atlas:
                    new_mat_image_item = MaterialImageList()
                    
                    def get_or_create_image(image_name, replacement_name, default_color):
                        if image_name and image_name in bpy.data.images:
                            image = bpy.data.images[image_name]
                        else:
                            # Create a new image with the replacement name if it doesn't exist
                            if replacement_name in bpy.data.images:
                                image = bpy.data.images[replacement_name]
                            else:
                                image = bpy.data.images.new(
                                    name=replacement_name, width=32, height=32, alpha=True
                                )
                                # Set the pixel data to the default color
                                num_pixels = 32 * 32
                                pixel_data = numpy.tile(numpy.array(default_color), num_pixels)
                                image.pixels[:] = pixel_data
                            # Set use_fake_user to True to prevent Blender from removing the image
                            image.use_fake_user = True
                        return image
                    
                    # Albedo
                    albedo_name = getattr(mat_slot.material, 'texture_atlas_albedo', '')
                    new_mat_image_item.albedo = get_or_create_image(
                        albedo_name,
                        mat_slot.material.name + "_albedo_replacement",
                        [0.0, 0.0, 0.0, 1.0]
                    )
                    
                    # Normal
                    normal_name = getattr(mat_slot.material, 'texture_atlas_normal', '')
                    new_mat_image_item.normal = get_or_create_image(
                        normal_name,
                        mat_slot.material.name + "_normal_replacement",
                        [0.5, 0.5, 1.0, 1.0]
                    )
                    
                    # Emission
                    emission_name = getattr(mat_slot.material, 'texture_atlas_emission', '')
                    new_mat_image_item.emission = get_or_create_image(
                        emission_name,
                        mat_slot.material.name + "_emission_replacement",
                        [0.0, 0.0, 0.0, 1.0]
                    )
                    
                    # Ambient Occlusion
                    ao_name = getattr(mat_slot.material, 'texture_atlas_ambient_occlusion', '')
                    new_mat_image_item.ambient_occlusion = get_or_create_image(
                        ao_name,
                        mat_slot.material.name + "_ambient_occlusion_replacement",
                        [1.0, 1.0, 1.0, 1.0]
                    )
                    
                    # Height
                    height_name = getattr(mat_slot.material, 'texture_atlas_height', '')
                    new_mat_image_item.height = get_or_create_image(
                        height_name,
                        mat_slot.material.name + "_height_replacement",
                        [0.5, 0.5, 0.5, 1.0]
                    )
                    
                    # Roughness
                    roughness_name = getattr(mat_slot.material, 'texture_atlas_roughness', '')
                    new_mat_image_item.roughness = get_or_create_image(
                        roughness_name,
                        mat_slot.material.name + "_roughness_replacement",
                        [1.0, 1.0, 1.0, 0.0]
                    )
                    
                    new_mat_image_item.material = mat_slot.material
                    new_mat_image_item.parent_mesh = obj
                    material_image_list.append(new_mat_image_item)
    
    return material_image_list



def prep_images_in_scene(context: Context) -> list[MaterialImageList]:
    preped_images: list[MaterialImageList] = get_material_images_from_scene(context)
    for MaterialImageClass in preped_images:
        ImageList: list[Image] = MaterialImageList_to_Image_list(MaterialImageClass)

        MaterialImageClass.w, MaterialImageClass.h = scale_images_to_largest(ImageList)

    

    return preped_images




class AvatarToolKit_OT_AtlasMaterials(Operator):
    bl_idname = "avatar_toolkit.atlas_materials"
    bl_label = t("TextureAtlas.atlas_materials")
    bl_description = t("TextureAtlas.atlas_materials_desc")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return context.scene.avatar_toolkit.texture_atlas_Has_Mat_List_Shown
    
    def execute(self, context: Context) -> set:
        try:
            # Get only materials that are explicitly marked for inclusion
            selected_materials = [m for m in prep_images_in_scene(context) 
                                if m.material and m.material.avatar_toolkit.include_in_atlas is True]
            
            if not selected_materials:
                self.report({'WARNING'}, t("TextureAtlas.no_materials_selected"))
                return {'CANCELLED'}

            packer: BinPacker = BinPacker(selected_materials)
            mat_images = packer.fit()

            size: list[int] = [
                max([
                    matimg.fit.w + matimg.albedo.size[0]
                    for matimg in mat_images
                    if matimg.albedo and matimg.albedo.has_data
                ] or [1]),
                max([
                    matimg.fit.h + matimg.albedo.size[1]
                    for matimg in mat_images
                    if matimg.albedo and matimg.albedo.has_data
                ] or [1])
            ]
            print([matimg.fit.w + matimg.albedo.size[0] for matimg in mat_images if matimg.albedo and matimg.albedo.has_data])
            
            atlased_mat: MaterialImageList = MaterialImageList()

            for mat in mat_images:
                if mat.albedo and mat.albedo.has_data:
                    x: int = int(mat.fit.x)
                    y: int = int(mat.fit.y)
                    w: int = int(mat.albedo.size[0])
                    h: int = int(mat.albedo.size[1])

                    for obj in bpy.data.objects:
                        if obj.type == 'MESH':
                            mesh: Mesh = obj.data
                            for layer in mesh.polygons:
                                if obj.material_slots[layer.material_index].material:
                                    if obj.material_slots[layer.material_index].material == mat.material:
                                        for loop_idx in layer.loop_indices:
                                            layer_loops: MeshUVLoopLayer
                                            for layer_loops in mesh.uv_layers:
                                                uv_item: Float2AttributeValue = layer_loops.uv[loop_idx]
                                                uv_item.vector.x = (uv_item.vector.x * (w / size[0])) + (x / size[0])
                                                uv_item.vector.y = (uv_item.vector.y * (h / size[1])) + (y / size[1])

            for texture_type in ["albedo", "normal", "emission", "ambient_occlusion", "height", "roughness"]:
                new_image_name: str = f"Atlas_{texture_type}_{context.scene.name}_{Path(bpy.data.filepath).stem}"

                print(f"Processing {texture_type} atlas image")

                if new_image_name in bpy.data.images:
                    bpy.data.images.remove(bpy.data.images[new_image_name])

                canvas: Image = bpy.data.images.new(name=new_image_name, width=int(size[0]), height=int(size[1]), alpha=True)
                c_w = canvas.size[0]
                canvas_pixels: list[float] = list(canvas.pixels[:])
                for mat in mat_images:
                    image_var: Image = getattr(mat, texture_type, None)
                    if image_var and image_var.has_data:
                        x: int = int(mat.fit.x)
                        y: int = int(mat.fit.y)
                        w: int = int(image_var.size[0])
                        h: int = int(image_var.size[1])

                        image_pixels: list[float] = list(image_var.pixels[:])

                        print(f"Writing image \"{image_var.name}\" to canvas.")
                        print(f"x: \"{x}\" y: \"{y}\" w: \"{w}\" h: \"{h}\"")
                        for k in range(0, h):
                            for i in range(0, w):
                                for channel in range(0, 4):
                                    canvas_index = (((k + y) * c_w) + (i + x)) * 4 + channel
                                    image_index = ((k * w) + i) * 4 + channel
                                    canvas_pixels[int(canvas_index)] = image_pixels[int(image_index)]

                canvas.pixels[:] = canvas_pixels[:]
                canvas.save(filepath=os.path.join(os.path.dirname(bpy.data.filepath), new_image_name + ".png"))
                setattr(atlased_mat, texture_type, canvas)

            #I am sorry for the amount of nodes I'm instanciating here and their values.
            #This is so that the nodes look pretty in the UI, which I think looks kinda nice. - @989onan
            atlased_mat.material = bpy.data.materials.new(name="Atlas_Final_"+bpy.context.scene.name+"_"+Path(bpy.data.filepath).stem)
            atlased_mat.material.use_nodes = True
            atlased_mat.material.node_tree.nodes.clear()

            principled_node: ShaderNodeBsdfPrincipled = atlased_mat.material.node_tree.nodes.new(type="ShaderNodeBsdfPrincipled")
            principled_node.location.x = 7.29706335067749
            principled_node.location.y = 298.918212890625

            output_node: ShaderNodeTexImage = atlased_mat.material.node_tree.nodes.new(type="ShaderNodeOutputMaterial")
            output_node.location.x = 297.29705810546875
            output_node.location.y = 298.918212890625

            albedo_node: ShaderNodeTexImage = atlased_mat.material.node_tree.nodes.new(type="ShaderNodeTexImage")
            albedo_node.location.x = -588.6177978515625
            albedo_node.location.y = 414.1948547363281
            albedo_node.image = atlased_mat.albedo

            emission_node: ShaderNodeTexImage = atlased_mat.material.node_tree.nodes.new(type="ShaderNodeTexImage")
            emission_node.location.x = -588.6177978515625
            emission_node.location.y = -173.9259033203125
            emission_node.image = atlased_mat.emission

            normal_node: ShaderNodeTexImage = atlased_mat.material.node_tree.nodes.new(type="ShaderNodeTexImage")
            normal_node.location.x = -941.4189453125
            normal_node.location.y = -20.8391780853271
            normal_node.image = atlased_mat.normal

            normal_map_node: ShaderNodeNormalMap = atlased_mat.material.node_tree.nodes.new(type="ShaderNodeNormalMap")
            normal_map_node.location.x = -545.550537109375
            normal_map_node.location.y = -0.7543716430664062

            roughness_node: ShaderNodeTexImage = atlased_mat.material.node_tree.nodes.new(type="ShaderNodeTexImage")
            roughness_node.location.x = -592.1703491210938
            roughness_node.location.y = 206.74075317382812
            roughness_node.image = atlased_mat.roughness

            ambient_occlusion_node: ShaderNodeTexImage = atlased_mat.material.node_tree.nodes.new(type="ShaderNodeTexImage")
            ambient_occlusion_node.location.x = -906.4371337890625
            ambient_occlusion_node.location.y = -389.9602355957031
            ambient_occlusion_node.image = atlased_mat.ambient_occlusion

            height_node: ShaderNodeTexImage = atlased_mat.material.node_tree.nodes.new(type="ShaderNodeTexImage")
            height_node.location.x = -1222.383056640625
            height_node.location.y = -375.48406982421875
            height_node.image = atlased_mat.height

            atlased_mat.material.node_tree.links.new(principled_node.inputs["Base Color"], albedo_node.outputs["Color"])
            atlased_mat.material.node_tree.links.new(principled_node.inputs["Metallic"], roughness_node.outputs["Alpha"])
            atlased_mat.material.node_tree.links.new(principled_node.inputs["Roughness"], roughness_node.outputs["Color"])
            atlased_mat.material.node_tree.links.new(principled_node.inputs["Alpha"], albedo_node.outputs["Alpha"])
            atlased_mat.material.node_tree.links.new(principled_node.inputs["Normal"], normal_map_node.outputs["Normal"])
            atlased_mat.material.node_tree.links.new(principled_node.inputs["Emission Color"], emission_node.outputs["Color"])
            atlased_mat.material.node_tree.links.new(output_node.inputs["Surface"], principled_node.outputs["BSDF"])
            atlased_mat.material.node_tree.links.new(normal_map_node.inputs["Color"], normal_node.outputs["Color"])

            # Only update selected materials for meshes
            for obj in context.scene.objects:
                if obj.type == 'MESH':
                    mesh: Mesh = obj.data
                    for i, mat_slot in enumerate(obj.material_slots):
                        if mat_slot.material and mat_slot.material.avatar_toolkit.include_in_atlas is True:
                            mesh.materials[i] = atlased_mat.material

            self.report({'INFO'}, t("TextureAtlas.atlas_completed"))
            return {"FINISHED"}
        except Exception as e:
            self.report({'ERROR'}, t("TextureAtlas.atlas_error"))
            raise e
        return {"FINISHED"}
         