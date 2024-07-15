from pathlib import Path

import numpy
import bpy
import re
import os
from typing import List, Tuple, Optional
from mathutils import Vector
from bpy.types import Material, Operator, Context, Object, Image, Mesh, MeshUVLoopLayer, Float2AttributeValue, ShaderNodeTexImage, ShaderNodeBsdfPrincipled, ShaderNodeNormalMap
from ..core.register import register_wrap
from ..core.properties import material_list_bool, SceneMatClass
from ..core.packer.rectangle_packer import MaterialImageList, BinPacker





def scale_images_to_largest(images:list[Image]) -> set:
    print([image.name for image in images])
    x: int=0
    y: int=0
    for image in images:
        x = max(x,image.size[0])
        y = max(y,image.size[1])
        print(x,y)
    
    for image in images:
        image.scale(width=int(x), height=int(y))

    return x,y

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
    mat: SceneMatClass = None
    material_image_list: list[MaterialImageList] = []
    for mat in context.scene.materials:
        new_mat_image_item: MaterialImageList = MaterialImageList()
        try:
            new_mat_image_item.albedo = bpy.data.images[mat.mat.texture_atlas_albedo]
        except Exception as e:
            name: str = mat.mat.name+"_albedo_replacement"
            if name in bpy.data.images:
                bpy.data.images.remove(image=bpy.data.images[name],do_unlink=True)
            new_mat_image_item.albedo = bpy.data.images.new(name=name,width=32,height=32, alpha=True)
        try:
            new_mat_image_item.normal = bpy.data.images[mat.mat.texture_atlas_normal]
        except Exception:
            name: str = mat.mat.name+"_normal_replacement"
            if name in bpy.data.images:
                bpy.data.images.remove(image=bpy.data.images[name],do_unlink=True)
            new_mat_image_item.normal = bpy.data.images.new(name=name,width=32,height=32, alpha=True)
        try:
            new_mat_image_item.emission = bpy.data.images[mat.mat.texture_atlas_emission]
        except Exception:
            name: str = mat.mat.name+"_emission_replacement"
            if name in bpy.data.images:
                bpy.data.images.remove(image=bpy.data.images[name],do_unlink=True)
            new_mat_image_item.emission = bpy.data.images.new(name=name,width=32,height=32, alpha=True)
            new_mat_image_item.emission.pixels[:] = numpy.tile(numpy.array([0.0,0.0,0.0,1.0]), 32*32)

        try:
            new_mat_image_item.ambient_occlusion = bpy.data.images[mat.mat.texture_atlas_ambient_occlusion]
        except Exception:
            name: str = mat.mat.name+"_ambient_occlusion_replacement"
            if name in bpy.data.images:
                bpy.data.images.remove(image=bpy.data.images[name],do_unlink=True)
            new_mat_image_item.ambient_occlusion = bpy.data.images.new(name=name,width=32,height=32, alpha=True)
            new_mat_image_item.ambient_occlusion.pixels[:] = numpy.tile(numpy.array([1.0,1.0,1.0,1.0]), 32*32)
        try:
            new_mat_image_item.height = bpy.data.images[mat.mat.texture_atlas_height]
        except Exception:
            name: str = mat.mat.name+"_height_replacement"
            if name in bpy.data.images:
                bpy.data.images.remove(image=bpy.data.images[name],do_unlink=True)
            new_mat_image_item.height = bpy.data.images.new(name=name,width=32,height=32, alpha=True)
            new_mat_image_item.height.pixels[:] = numpy.tile(numpy.array([0.5,0.5,0.5,1.0]), 32*32)

        try:
            new_mat_image_item.roughness = bpy.data.images[mat.mat.texture_atlas_roughness]
        except Exception:
            name: str = mat.mat.name+"_roughness_replacement"
            if name in bpy.data.images:
                bpy.data.images.remove(image=bpy.data.images[name],do_unlink=True)
            new_mat_image_item.roughness = bpy.data.images.new(name=name,width=32,height=32, alpha=True)
            new_mat_image_item.roughness.pixels[:] = numpy.tile(numpy.array([1.0,1.0,1.0,0.0]), 32*32)
        new_mat_image_item.material = mat.mat
        material_image_list.append(new_mat_image_item)
    return material_image_list


def prep_images_in_scene(context: Context) -> list[MaterialImageList]:
    preped_images: list[MaterialImageList] = get_material_images_from_scene(context)
    for MaterialImageClass in preped_images:
        ImageList: list[Image] = MaterialImageList_to_Image_list(MaterialImageClass)

        MaterialImageClass.w, MaterialImageClass.h = scale_images_to_largest(ImageList)

    

    return preped_images


@register_wrap
class Atlas_Materials(Operator):

    bl_idname = "avatar_toolkit.atlas_materials"
    bl_label = "Atlas Materials"
    bl_description = "Atlas materials to optimize the model"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return context.scene.texture_atlas_Has_Mat_List_Shown
    
    def execute(self, context: Context) -> set:
        try:
            mat_images: list[MaterialImageList] = prep_images_in_scene(context)

            packer: BinPacker = BinPacker(mat_images)

            mat_images = packer.fit()


            size: list[int] = [max([matimg.fit.w + matimg.albedo.size[0] for matimg in mat_images]),
                    max([matimg.fit.h + matimg.albedo.size[1] for matimg in mat_images])]
            print([matimg.fit.w + matimg.albedo.size[1] for matimg in mat_images])
            
            atlased_mat: MaterialImageList = MaterialImageList()

            for mat in mat_images:
                x: int = int(mat.fit.x)
                y: int = int(mat.fit.y)
                w: int = int(mat.albedo.size[0])
                h: int = int(mat.albedo.size[1])

                for obj in bpy.data.objects:
                    mesh: Mesh = obj.data


                    for layer in mesh.polygons:
                        if obj.material_slots[layer.material_index].material:
                            if obj.material_slots[layer.material_index].material == mat.material:
                                for loop_idx in layer.loop_indices:
                                    layer_loops: MeshUVLoopLayer
                                    for layer_loops in mesh.uv_layers:
                                        uv_item: Float2AttributeValue = layer_loops.uv[loop_idx]
                                        uv_item.vector.x = (uv_item.vector.x*(w/size[0]))+(x/size[0])
                                        uv_item.vector.y = (uv_item.vector.y*(h/size[1]))+(y/size[1])

            for type in ["albedo","normal", "emission","ambient_occlusion","height", "roughness"]:
                new_image_name: str= "Atlas_"+type+"_"+context.scene.name+"_"+Path(bpy.data.filepath).stem

                print("Processing "+type+" atlas image")

                if new_image_name in bpy.data.images:
                    bpy.data.images.remove(bpy.data.images[new_image_name])

                canvas: Image = bpy.data.images.new(name=new_image_name, width=int(size[0]),height=int(size[1]), alpha=True)
                c_w = canvas.size[0]
                #c_h = canvas.size[1]
                canvas_pixels: list[float] = list(canvas.pixels[:])
                for mat in mat_images:
                    x: int = int(mat.fit.x)
                    y: int = int(mat.fit.y)
                    w: int = int(mat.albedo.size[0])
                    h: int = int(mat.albedo.size[1])

                    image_var: Image = eval("mat."+type)
                    
                    image_pixels: list[float] = list(image_var.pixels[:])
                    
                    print("writing image \""+image_var.name+"\" to canvas.")
                    print("x: \""+str(x)+"\" "+"y: \""+str(y)+"\" "+"w: \""+str(w)+"\" "+"h: \""+str(h)+"\" ")
                    for k in range(0,h):
                        for i in range(0, w):
                            for channel in range(0,4):
                                canvas_pixels[
                                    int((((k+y)*c_w)
                                         +
                                         (i+x))*4)
                                         +int(channel)
                                         ] = image_pixels[
                                             int((
                                                 (k*w)
                                                 +i)*4)
                                             +int(channel)]

                canvas.pixels[:] = canvas_pixels[:]
                canvas.save(filepath=os.path.join(os.path.dirname(bpy.data.filepath),new_image_name+".png"))
                exec("atlased_mat."+type+" = canvas")


            atlased_mat.material = bpy.data.materials.new(name="Atlas_Final_"+bpy.context.scene.name+"_"+Path(bpy.data.filepath).stem)
            atlased_mat.material.use_nodes = True
            atlased_mat.material.node_tree.nodes.clear()


            #I am sorry for the amount of nodes I'm instanciating here and their values.
            #This is so that the nodes look pretty in the UI, which I think looks kinda nice. - @989onan
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


            for obj in context.scene.objects:
                mesh: Mesh = obj.data
                mesh.materials.clear()
                
                mesh.materials.append(atlased_mat.material)

            return {"FINISHED"}
        except Exception as e:
            raise e
            return {"FINISHED"}
            