import bpy
from ..core.register import register_wrap

@register_wrap
class AvatarToolkitPanel(bpy.types.Panel):
    bl_label = "Avatar Toolkit"
    bl_idname = "OBJECT_PT_avatar_toolkit"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Avatar Toolkit"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Welcome to Avatar Toolkit!")
        print("Avatar Toolkit Panel is being drawn")
