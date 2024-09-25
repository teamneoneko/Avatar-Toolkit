import bpy
import numpy as np
import re
from bpy.types import Operator, Context, Material, ShaderNodeTexImage, ShaderNodeGroup, Object
from ..core.register import register_wrap
from ..functions.translations import t
from ..core.common import get_selected_armature, is_valid_armature, get_all_meshes, init_progress, update_progress, finish_progress
from ..functions.additional_tools import AvatarToolKit_OT_ConnectBones, AvatarToolKit_OT_DeleteBoneConstraints
from ..functions.armature_modifying import AvatarToolkit_OT_RemoveZeroWeightBones, AvatarToolkit_OT_MergeBonesToParents

@register_wrap
class AvatarToolKit_OT_CleanupMesh(Operator):
    bl_idname = "avatar_toolkit.cleanup_mesh"
    bl_label = t("MMDOptions.cleanup_mesh.label")
    bl_description = t("MMDOptions.cleanup_mesh.desc")
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context: Context) -> set[str]:
        init_progress(context, 4)
        
        update_progress(self, context, t("MMDOptions.removing_empty_objects"))
        bpy.ops.object.select_all(action='DESELECT')
        for obj in context.scene.objects:
            if obj.type == 'EMPTY':
                obj.select_set(True)
        bpy.ops.object.delete()

        update_progress(self, context, t("MMDOptions.removing_unused_vertex_groups"))
        for obj in get_all_meshes(context):
            self.remove_unused_vertex_groups(obj)

        update_progress(self, context, t("MMDOptions.removing_unused_vertices"))
        for obj in get_all_meshes(context):
            self.remove_unused_vertices(obj)

        update_progress(self, context, t("MMDOptions.removing_empty_shape_keys"))
        for obj in get_all_meshes(context):
            self.remove_empty_shape_keys(obj)

        finish_progress(context)
        return {'FINISHED'}

    def remove_unused_vertex_groups(self, obj):
        vgroups = obj.vertex_groups
        for vgroup in vgroups:
            if not any(vgroup.index in [g.group for g in v.groups] for v in obj.data.vertices):
                vgroups.remove(vgroup)

    def remove_unused_vertices(self, obj):
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.delete_loose()
        bpy.ops.object.mode_set(mode='OBJECT')

    def remove_empty_shape_keys(self, obj):
        if obj.data.shape_keys:
            for key in obj.data.shape_keys.key_blocks:
                if key.name != 'Basis' and all(abs(key.data[i].co[j] - obj.data.shape_keys.reference_key.data[i].co[j]) < 0.0001 for i in range(len(key.data)) for j in range(3)):
                    obj.shape_key_remove(key)

@register_wrap
class AvatarToolKit_OT_OptimizeWeights(Operator):
    bl_idname = "avatar_toolkit.optimize_weights"
    bl_label = t("MMDOptions.optimize_weights.label")
    bl_description = t("MMDOptions.optimize_weights.desc")
    bl_options = {'REGISTER', 'UNDO'}

    max_weights: bpy.props.IntProperty(
        name=t("MMDOptions.max_weights.label"),
        description=t("MMDOptions.max_weights.desc"),
        default=4,
        min=1,
        max=8
    )

    def execute(self, context: Context) -> set[str]:
        armature = get_selected_armature(context)
        if not armature:
            self.report({'ERROR'}, t("MMDOptions.no_armature_selected"))
            return {'CANCELLED'}

        init_progress(context, 4)

        update_progress(self, context, t("MMDOptions.merging_weights"))
        for obj in get_all_meshes(context):
            for modifier in obj.modifiers:
                if modifier.type == 'ARMATURE' and modifier.object != armature:
                    bpy.ops.object.modifier_apply(modifier=modifier.name)

        update_progress(self, context, t("MMDOptions.removing_zero_weight_bones"))
        bpy.ops.avatar_toolkit.remove_zero_weight_bones('EXEC_DEFAULT')

        update_progress(self, context, t("MMDOptions.limiting_vertex_weights"))
        for obj in get_all_meshes(context):
            self.limit_vertex_weights(obj)

        update_progress(self, context, t("MMDOptions.weight_optimization_complete"))
        finish_progress(context)
        return {'FINISHED'}

    def limit_vertex_weights(self, obj):
        for v in obj.data.vertices:
            if len(v.groups) > self.max_weights:
                sorted_groups = sorted(v.groups, key=lambda g: g.weight, reverse=True)
                for g in sorted_groups[self.max_weights:]:
                    obj.vertex_groups[g.group].remove([v.index])

@register_wrap
class AvatarToolKit_OT_OptimizeArmature(Operator):
    bl_idname = "avatar_toolkit.optimize_armature"
    bl_label = t("MMDOptions.optimize_armature.label")
    bl_description = t("MMDOptions.optimize_armature.desc")
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context: Context) -> set[str]:
        armature = get_selected_armature(context)
        if not armature:
            self.report({'ERROR'}, t("MMDOptions.no_armature_selected"))
            return {'CANCELLED'}

        init_progress(context, 9)

        update_progress(self, context, t("MMDOptions.fixing_bone_rolls"))
        bpy.ops.object.mode_set(mode='EDIT')
        for bone in armature.data.edit_bones:
            bone.roll = 0

        update_progress(self, context, t("MMDOptions.aligning_bones"))
        for bone in armature.data.edit_bones:
            if bone.parent:
                bone.head = bone.parent.tail

        update_progress(self, context, t("MMDOptions.connecting_bones"))
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.avatar_toolkit.connect_bones('EXEC_DEFAULT')

        update_progress(self, context, t("MMDOptions.deleting_bone_constraints"))
        bpy.ops.avatar_toolkit.delete_bone_constraints('EXEC_DEFAULT')

        update_progress(self, context, t("MMDOptions.merging_bones_to_parents"))
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        armature.select_set(True)
        context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode='EDIT')
        try:
            bpy.ops.avatar_toolkit.merge_bones_to_parents('EXEC_DEFAULT')
        except RuntimeError as e:
            self.report({'WARNING'}, f"Failed to merge bones to parents: {str(e)}")

        update_progress(self, context, t("MMDOptions.reordering_bones"))
        self.reorder_bones(context, armature)

        update_progress(self, context, t("MMDOptions.fixing_armature_names"))
        self.fix_armature_names(armature)

        update_progress(self, context, t("MMDOptions.renaming_bones"))
        self.rename_bones(armature)

        update_progress(self, context, t("MMDOptions.armature_optimization_complete"))
        finish_progress(context)
        return {'FINISHED'}

    def reorder_bones(self, context: Context, armature: bpy.types.Object):
        def sort_bones(bone):
            children = sorted(bone.children, key=lambda b: b.name)
            for child in children:
                sort_bones(child)

        bpy.ops.object.mode_set(mode='EDIT')
        root_bones = [bone for bone in armature.data.edit_bones if not bone.parent]
        for root_bone in sorted(root_bones, key=lambda b: b.name):
            sort_bones(root_bone)

    def fix_armature_names(self, armature):
        for bone in armature.data.bones:
            fixed_name = self.get_fixed_bone_name(bone.name)
            if fixed_name != bone.name:
                bone.name = fixed_name

    def get_fixed_bone_name(self, name):
        name = name.replace(' ', '_')
        name = re.sub(r'[^\w]', '', name)
        return name

    def rename_bones(self, armature):
        for bone in armature.data.bones:
            new_name = self.get_standardized_bone_name(bone.name)
            if new_name != bone.name:
                bone.name = new_name

    def get_standardized_bone_name(self, name):
        if 'left' in name.lower():
            return f"Left_{name}"
        elif 'right' in name.lower():
            return f"Right_{name}"
        return name

def bake_mmd_colors(node_base_tex: ShaderNodeTexImage, node_mmd_shader: ShaderNodeGroup):
    ambient_color_input = node_mmd_shader.inputs.get("Ambient Color")
    diffuse_color_input = node_mmd_shader.inputs.get("Diffuse Color")
    
    if not ambient_color_input or not diffuse_color_input:
        return node_base_tex, None

    ambient_color = np.array(ambient_color_input.default_value[:3])
    diffuse_color = np.array(diffuse_color_input.default_value[:3])
    mmd_color = np.clip(ambient_color + diffuse_color * 0.6, 0, 1)

    if not node_base_tex or not node_base_tex.image:
        principled_base_color = np.append(mmd_color, 1)
        return None, principled_base_color

    base_tex_image = node_base_tex.image
    if not base_tex_image.pixels:
        return node_base_tex, None

    if base_tex_image.colorspace_settings.name == 'sRGB':
        is_small_mask = mmd_color < 0.0031308
        mmd_color[is_small_mask] = np.where(mmd_color[is_small_mask] < 0.0, 0, mmd_color[is_small_mask] * 12.92)
        is_large_mask = np.invert(is_small_mask)
        mmd_color[is_large_mask] = (mmd_color[is_large_mask] ** (1.0 / 2.4)) * 1.055 - 0.055

    pixels = np.array(base_tex_image.pixels).reshape((-1, 4))
    pixels[:, :3] *= mmd_color

    baked_image = bpy.data.images.new(base_tex_image.name + "MMDCatsBaked",
                                      width=base_tex_image.size[0],
                                      height=base_tex_image.size[1],
                                      alpha=True)
    baked_image.filepath = bpy.path.abspath("//" + base_tex_image.name + ".png")
    baked_image.file_format = 'PNG'
    baked_image.colorspace_settings.name = base_tex_image.colorspace_settings.name

    baked_image.pixels = pixels.flatten()
    node_base_tex.image = baked_image

    if bpy.data.is_saved:
        baked_image.save()

    return node_base_tex, None

def add_principled_shader(material: Material, bake_mmd=True):
    node_tree = material.node_tree
    nodes = node_tree.nodes
    links = node_tree.links

    principled_shader = nodes.new(type="ShaderNodeBsdfPrincipled")
    principled_shader.label = "Cats Export Shader"
    principled_shader.location = (501, -500)

    output_shader = nodes.new(type="ShaderNodeOutputMaterial")
    output_shader.label = "Cats Export"
    output_shader.location = (801, -500)

    links.new(principled_shader.outputs["BSDF"], output_shader.inputs["Surface"])

    node_base_tex = nodes.get("mmd_base_tex") or next((n for n in nodes if n.type == 'TEX_IMAGE'), None)
    node_mmd_shader = nodes.get("mmd_shader")

    if node_mmd_shader and bake_mmd:
        node_base_tex, principled_base_color = bake_mmd_colors(node_base_tex, node_mmd_shader)
    else:
        principled_base_color = None

    if node_base_tex and node_base_tex.image:
        links.new(node_base_tex.outputs["Color"], principled_shader.inputs["Base Color"])
        links.new(node_base_tex.outputs["Alpha"], principled_shader.inputs["Alpha"])
    elif principled_base_color is not None:
        principled_shader.inputs["Base Color"].default_value = principled_base_color

    principled_shader.inputs["Specular IOR Level"].default_value = 0
    principled_shader.inputs["Roughness"].default_value = 0.9
    principled_shader.inputs["Sheen Tint"].default_value = (1.0, 1.0, 1.0, 1.0)
    principled_shader.inputs["Coat Roughness"].default_value = 0
    principled_shader.inputs["IOR"].default_value = 1.45

    # Handle transparency
    if material.blend_method != 'OPAQUE':
        principled_shader.inputs["Alpha"].default_value = material.alpha_threshold
        material.blend_method = 'CLIP'
        material.shadow_method = 'CLIP'

def fix_mmd_shader(material: Material):
    mmd_shader_node = material.node_tree.nodes.get("mmd_shader")
    if mmd_shader_node:
        reflect_input = mmd_shader_node.inputs.get("Reflect")
        if reflect_input:
            reflect_input.default_value = 1

def fix_vrm_shader(material: Material):
    nodes = material.node_tree.nodes
    is_vrm_mat = False
    for node in nodes:
        if hasattr(node, 'node_tree') and 'MToon_unversioned' in node.node_tree.name:
            node.location[0] = 200
            node.inputs['ReceiveShadow_Texture_alpha'].default_value = -10000
            node.inputs['ShadeTexture'].default_value = (1.0, 1.0, 1.0, 1.0)
            node.inputs['Emission_Texture'].default_value = (0.0, 0.0, 0.0, 0.0)
            node.inputs['SphereAddTexture'].default_value = (0.0, 0.0, 0.0, 0.0)
            node_input = node.inputs.get('NomalmapTexture') or node.inputs.get('NormalmapTexture')
            node_input.default_value = (1.0, 1.0, 1.0, 1.0)
            is_vrm_mat = True
            break
    
    if is_vrm_mat:
        nodes_to_keep = ['DiffuseColor', 'MainTexture', 'Emission_Texture']
        if 'HAIR' in material.name:
            nodes_to_keep.append('SphereAddTexture')
        
        for node in nodes:
            if ('RGB' in node.name or 'Value' in node.name or 'Image Texture' in node.name or 
                'UV Map' in node.name or 'Mapping' in node.name):
                if node.label not in nodes_to_keep:
                    material.node_tree.links = [link for link in material.node_tree.links 
                                                if not (link.from_node == node or link.to_node == node)]

@register_wrap
class AvatarToolKit_OT_ConvertMaterials(Operator):
    bl_idname = "avatar_toolkit.convert_materials"
    bl_label = t("MMDOptions.convert_materials.label")
    bl_description = t("MMDOptions.convert_materials.desc")
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context: Context) -> set[str]:
        meshes = get_all_meshes(context)
        init_progress(context, len(meshes))

        for obj in meshes:
            update_progress(self, context, t("MMDOptions.converting_materials").format(name=obj.name))
            self.convert_materials_for_mesh(obj)

        finish_progress(context)
        return {'FINISHED'}

    def convert_materials_for_mesh(self, mesh: Object):
        for mat_slot in mesh.material_slots:
            if mat_slot.material:
                mat = mat_slot.material
                mat.use_nodes = True
                
                # Add Principled BSDF shader
                add_principled_shader(mat)
                
                # Fix MMD shader if present
                fix_mmd_shader(mat)
                
                # Fix VRM shader if present
                fix_vrm_shader(mat)

                # Clean up unused nodes
                self.clean_unused_nodes(mat)

    def clean_unused_nodes(self, material: Material):
        nodes = material.node_tree.nodes
        links = material.node_tree.links

        used_nodes = set()
        output_node = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None)

        if output_node:
            self.traverse_node_tree(output_node, used_nodes)

        for node in nodes:
            if node not in used_nodes:
                nodes.remove(node)

    def traverse_node_tree(self, node, used_nodes):
        used_nodes.add(node)
        for input in node.inputs:
            for link in input.links:
                if link.from_node not in used_nodes:
                    self.traverse_node_tree(link.from_node, used_nodes)

