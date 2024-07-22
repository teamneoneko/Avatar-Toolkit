import bpy
from ..core.register import register_wrap
from ..functions.translations import t

@register_wrap
class AvatarToolkitPanel(bpy.types.Panel):
    bl_label = "Avatar Toolkit"
    bl_idname = "OBJECT_PT_avatar_toolkit"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Avatar Toolkit"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Welcome to Avatar Toolkit, a tool for")
        layout.label(text="creating and editing avatars in blender,")
        layout.label(text="This is an early alpha version, so expect")
        layout.label(text="bugs and issues.")
        #print("Avatar Toolkit Panel is being drawn")
        
