from pathlib import Path
import bpy
import re
import os
from typing import List, Tuple, Optional
from bpy.types import Material, Operator, Context, Object, Image
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

        try:
            new_mat_image_item.ambient_occlusion = bpy.data.images[mat.mat.texture_atlas_ambient_occlusion]
        except Exception:
            name: str = mat.mat.name+"_ambient_occlusion_replacement"
            if name in bpy.data.images:
                bpy.data.images.remove(image=bpy.data.images[name],do_unlink=True)
            new_mat_image_item.ambient_occlusion = bpy.data.images.new(name=name,width=32,height=32, alpha=True)
        try:
            new_mat_image_item.height = bpy.data.images[mat.mat.texture_atlas_height]
        except Exception:
            name: str = mat.mat.name+"_height_replacement"
            if name in bpy.data.images:
                bpy.data.images.remove(image=bpy.data.images[name],do_unlink=True)
            new_mat_image_item.height = bpy.data.images.new(name=name,width=32,height=32, alpha=True)
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
            
            for type in ["albedo","normal", "emission","ambient_occlusion","height"]:
                new_image_name: str= "Atlas_"+type+"_"+bpy.context.scene.name+"_"+Path(bpy.data.filepath).stem

                print("Processing "+type+" atlas image")

                if new_image_name in bpy.data.images:
                    bpy.data.images.remove(bpy.data.images[new_image_name])

                canvas: Image = bpy.data.images.new(name=new_image_name, width=int(size[0]),height=int(size[1]), alpha=True)
                c_w = canvas.size[0]
                c_h = canvas.size[1]
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
            return {"FINISHED"}
        except Exception as e:
            raise e
            return {"FINISHED"}
            