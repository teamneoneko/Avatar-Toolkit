from pathlib import Path
import numpy
import bpy
import os
from typing import List, Optional
from bpy.types import Material, Operator, Context, Object, Image, Mesh, MeshUVLoopLayer, Float2AttributeValue, ShaderNodeTexImage, ShaderNodeBsdfPrincipled, ShaderNodeNormalMap
from ..core.common import SceneMatClass, MaterialListBool, ProgressTracker
from ..core.packer.rectangle_packer import MaterialImageList, BinPacker
from ..core.translations import t
from ..core.logging_setup import logger

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

def scale_images_to_largest(images: List[Image]) -> tuple[int, int]:
    x: int = 0
    y: int = 0
    
    valid_images = [img for img in images if img and img.has_data]
    
    if not valid_images:
        return 0, 0
        
    for image in valid_images:
        x = max(x, image.size[0])
        y = max(y, image.size[1])
    
    for image in valid_images:
        image.scale(width=int(x), height=int(y))

    return x, y

def MaterialImageList_to_Image_list(classitem: MaterialImageList) -> List[Image]:
    return [
        classitem.albedo,
        classitem.normal,
        classitem.emission,
        classitem.ambient_occlusion,
        classitem.height,
        classitem.roughness
    ]

def get_material_images_from_scene(context: Context) -> list[MaterialImageList]:
    material_image_list: list[MaterialImageList] = []
    
    with ProgressTracker(context, len(context.scene.objects), "Processing Materials") as progress:
        for obj in context.scene.objects:
            if obj.type == 'MESH':
                for mat_slot in obj.material_slots:
                    # Only process materials that are selected for atlas
                    if mat_slot.material and mat_slot.material.include_in_atlas is True:
                        new_mat_image_item = MaterialImageList()
                        try:
                            new_mat_image_item.albedo = bpy.data.images[mat_slot.material.texture_atlas_albedo]
                        except Exception:
                            name = mat_slot.material.name + "_albedo_replacement"
                            if name in bpy.data.images:
                                bpy.data.images.remove(image=bpy.data.images[name], do_unlink=True)
                            new_mat_image_item.albedo = bpy.data.images.new(name=name, width=32, height=32, alpha=True)
                            new_mat_image_item.albedo.pixels[:] = numpy.tile(numpy.array([0.0,0.0,0.0,1.0]), 32*32)
                        try:
                            new_mat_image_item.normal = bpy.data.images[mat_slot.material.texture_atlas_normal]
                        except Exception:
                            name = mat_slot.material.name + "_normal_replacement"
                            if name in bpy.data.images:
                                bpy.data.images.remove(image=bpy.data.images[name], do_unlink=True)
                            new_mat_image_item.normal = bpy.data.images.new(name=name, width=32, height=32, alpha=True)
                            new_mat_image_item.normal.pixels[:] = numpy.tile(numpy.array([0.5,0.5,1.0,1.0]), 32*32)
                        try:
                            new_mat_image_item.emission = bpy.data.images[mat_slot.material.texture_atlas_emission]
                        except Exception:
                            name = mat_slot.material.name + "_emission_replacement"
                            if name in bpy.data.images:
                                bpy.data.images.remove(image=bpy.data.images[name], do_unlink=True)
                            new_mat_image_item.emission = bpy.data.images.new(name=name, width=32, height=32, alpha=True)
                            new_mat_image_item.emission.pixels[:] = numpy.tile(numpy.array([0.0,0.0,0.0,1.0]), 32*32)
                        try:
                            new_mat_image_item.ambient_occlusion = bpy.data.images[mat_slot.material.texture_atlas_ambient_occlusion]
                        except Exception:
                            name = mat_slot.material.name + "_ambient_occlusion_replacement"
                            if name in bpy.data.images:
                                bpy.data.images.remove(image=bpy.data.images[name], do_unlink=True)
                            new_mat_image_item.ambient_occlusion = bpy.data.images.new(name=name, width=32, height=32, alpha=True)
                            new_mat_image_item.ambient_occlusion.pixels[:] = numpy.tile(numpy.array([1.0,1.0,1.0,1.0]), 32*32)
                        try:
                            new_mat_image_item.height = bpy.data.images[mat_slot.material.texture_atlas_height]
                        except Exception:
                            name = mat_slot.material.name + "_height_replacement"
                            if name in bpy.data.images:
                                bpy.data.images.remove(image=bpy.data.images[name], do_unlink=True)
                            new_mat_image_item.height = bpy.data.images.new(name=name, width=32, height=32, alpha=True)
                            new_mat_image_item.height.pixels[:] = numpy.tile(numpy.array([0.5,0.5,0.5,1.0]), 32*32)
                        try:
                            new_mat_image_item.roughness = bpy.data.images[mat_slot.material.texture_atlas_roughness]
                        except Exception:
                            name = mat_slot.material.name + "_roughness_replacement"
                            if name in bpy.data.images:
                                bpy.data.images.remove(image=bpy.data.images[name], do_unlink=True)
                            new_mat_image_item.roughness = bpy.data.images.new(name=name, width=32, height=32, alpha=True)
                            new_mat_image_item.roughness.pixels[:] = numpy.tile(numpy.array([1.0,1.0,1.0,0.0]), 32*32)
                        
                        new_mat_image_item.material = mat_slot.material
                        new_mat_image_item.parent_mesh = obj
                        material_image_list.append(new_mat_image_item)
                
                progress.step(f"Processed {obj.name}")
    
    return material_image_list

def prep_images_in_scene(context: Context) -> List[MaterialImageList]:
    preped_images = get_material_images_from_scene(context)
    
    with ProgressTracker(context, len(preped_images), "Preparing Images") as progress:
        for MaterialImageClass in preped_images:
            ImageList = MaterialImageList_to_Image_list(MaterialImageClass)
            MaterialImageClass.w, MaterialImageClass.h = scale_images_to_largest(ImageList)
            progress.step(f"Scaled images for {MaterialImageClass.material.name}")

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
            selected_materials = [m for m in prep_images_in_scene(context) 
                                if m.material and m.material.include_in_atlas]
            
            if not selected_materials:
                self.report({'WARNING'}, t("TextureAtlas.no_materials_selected"))
                return {'CANCELLED'}

            logger.info("Starting material atlas creation")
            
            packer = BinPacker(selected_materials)
            mat_images = packer.fit()

            size = [
                max([matimg.fit.w + matimg.albedo.size[0] for matimg in mat_images]),
                max([matimg.fit.h + matimg.albedo.size[1] for matimg in mat_images])
            ]
            
            atlased_mat = MaterialImageList()

            # UV Remapping
            with ProgressTracker(context, len(bpy.data.objects), "Remapping UVs") as progress:
                for mat in mat_images:
                    x, y = int(mat.fit.x), int(mat.fit.y)
                    w, h = int(mat.albedo.size[0]), int(mat.albedo.size[1])

                    for obj in bpy.data.objects:
                        if obj.type == 'MESH':
                            mesh = obj.data
                            for layer in mesh.polygons:
                                if (obj.material_slots[layer.material_index].material and 
                                    obj.material_slots[layer.material_index].material == mat.material):
                                    for loop_idx in layer.loop_indices:
                                        for layer_loops in mesh.uv_layers:
                                            uv_item = layer_loops.uv[loop_idx]
                                            uv_item.vector.x = (uv_item.vector.x*(w/size[0]))+(x/size[0])
                                            uv_item.vector.y = (uv_item.vector.y*(h/size[1]))+(y/size[1])
                        progress.step(f"Processed UVs for {obj.name}")

            # Create atlas textures
            texture_types = ["albedo", "normal", "emission", "ambient_occlusion", "height", "roughness"]
            
            with ProgressTracker(context, len(texture_types), "Creating Atlas Textures") as progress:
                for type_name in texture_types:
                    new_image_name = f"Atlas_{type_name}_{context.scene.name}_{Path(bpy.data.filepath).stem}"
                    logger.debug(f"Processing {type_name} atlas image")

                    if new_image_name in bpy.data.images:
                        bpy.data.images.remove(bpy.data.images[new_image_name])

                    canvas = bpy.data.images.new(name=new_image_name, width=int(size[0]), 
                                               height=int(size[1]), alpha=True)
                    c_w = canvas.size[0]
                    canvas_pixels = list(canvas.pixels[:])
                    
                    for mat in mat_images:
                        x, y = int(mat.fit.x), int(mat.fit.y)
                        w, h = int(mat.albedo.size[0]), int(mat.albedo.size[1])
                        image_var = getattr(mat, type_name)
                        image_pixels = list(image_var.pixels[:])
                        
                        for k in range(h):
                            for i in range(w):
                                for channel in range(4):
                                    canvas_pixels[int((((k+y)*c_w)+(i+x))*4)+channel] = \
                                        image_pixels[int(((k*w)+i)*4)+channel]

                    canvas.pixels[:] = canvas_pixels[:]
                    canvas.save(filepath=os.path.join(os.path.dirname(bpy.data.filepath),
                                                    new_image_name+".png"))
                    setattr(atlased_mat, type_name, canvas)
                    progress.step(f"Created {type_name} atlas")

            # Create material nodes
            atlased_mat.material = bpy.data.materials.new(
                name=f"Atlas_Final_{context.scene.name}_{Path(bpy.data.filepath).stem}")
            atlased_mat.material.use_nodes = True
            atlased_mat.material.node_tree.nodes.clear()

            principled_node = atlased_mat.material.node_tree.nodes.new(type="ShaderNodeBsdfPrincipled")
            principled_node.location.x = 7.29706335067749
            principled_node.location.y = 298.918212890625

            output_node = atlased_mat.material.node_tree.nodes.new(type="ShaderNodeOutputMaterial")
            output_node.location.x = 297.29705810546875
            output_node.location.y = 298.918212890625

            albedo_node = atlased_mat.material.node_tree.nodes.new(type="ShaderNodeTexImage")
            albedo_node.location.x = -588.6177978515625
            albedo_node.location.y = 414.1948547363281
            albedo_node.image = atlased_mat.albedo

            emission_node = atlased_mat.material.node_tree.nodes.new(type="ShaderNodeTexImage")
            emission_node.location.x = -588.6177978515625
            emission_node.location.y = -173.9259033203125
            emission_node.image = atlased_mat.emission

            normal_node = atlased_mat.material.node_tree.nodes.new(type="ShaderNodeTexImage")
            normal_node.location.x = -941.4189453125
            normal_node.location.y = -20.8391780853271
            normal_node.image = atlased_mat.normal

            normal_map_node = atlased_mat.material.node_tree.nodes.new(type="ShaderNodeNormalMap")
            normal_map_node.location.x = -545.550537109375
            normal_map_node.location.y = -0.7543716430664062

            roughness_node = atlased_mat.material.node_tree.nodes.new(type="ShaderNodeTexImage")
            roughness_node.location.x = -592.1703491210938
            roughness_node.location.y = 206.74075317382812
            roughness_node.image = atlased_mat.roughness

            ambient_occlusion_node = atlased_mat.material.node_tree.nodes.new(type="ShaderNodeTexImage")
            ambient_occlusion_node.location.x = -906.4371337890625
            ambient_occlusion_node.location.y = -389.9602355957031
            ambient_occlusion_node.image = atlased_mat.ambient_occlusion

            height_node = atlased_mat.material.node_tree.nodes.new(type="ShaderNodeTexImage")
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

            # Update materials
            with ProgressTracker(context, len(context.scene.objects), "Updating Materials") as progress:
                for obj in context.scene.objects:
                    if obj.type == 'MESH':
                        mesh = obj.data
                        for i, mat_slot in enumerate(obj.material_slots):
                            if mat_slot.material and mat_slot.material.include_in_atlas:
                                mesh.materials[i] = atlased_mat.material
                        progress.step(f"Updated materials for {obj.name}")

            logger.info("Material atlas creation completed successfully")
            self.report({'INFO'}, t("TextureAtlas.atlas_completed"))
            return {"FINISHED"}
            
        except Exception as e:
            logger.error(f"Error creating material atlas: {str(e)}", exc_info=True)
            self.report({'ERROR'}, t("TextureAtlas.atlas_error"))
            raise e
