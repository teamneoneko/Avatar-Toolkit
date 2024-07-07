import bpy
from typing import List, Optional
from bpy.types import Operator, Context, Object, TextureNode
from ..core.register import register_wrap
from ..core.common import get_armature, simplify_bonename

@register_wrap
class Atlas_Textures(Operator):
    bl_idname = "avatar_toolkit.atlas_textures"
    bl_label = "Atlas Textures"
    bl_description = """Combines materials and their textures to optimize the model.
Although this combines materials, it may not reduce your VRAM usage. Other tools
like Tuxedo can vastly reduce your VRAM usage as well as many other optimizations,
rather than just duct taping the textures together like material combiner and this tool.
"""
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context: Context) -> set:

        
        return {'FINISHED'}


