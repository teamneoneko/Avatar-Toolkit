import numpy as np
import bpy
from bpy.types import Context
from ..core.common import get_selected_armature, get_all_meshes, is_valid_armature
from ..functions.translations import t
from ..core.register import register_wrap

@register_wrap
class AvatarToolkit_OT_RemoveUnusedShapekeys(bpy.types.Operator):
    tolerance: bpy.props.FloatProperty(name=t("Tools.remove_unused_shapekeys.tolerance.label"), default=0.001, description=t("Tools.remove_unused_shapekeys.tolerance.desc"))
    bl_idname = "avatar_toolkit.remove_unused_shapekeys"
    bl_label = t("Tools.remove_unused_shapekeys.label")
    bl_description = t("Tools.remove_unused_shapekeys.desc")
    bl_options = {'REGISTER', 'UNDO'}
    

    @classmethod
    def poll(cls, context: Context) -> bool:
        armature = get_selected_armature(context)
        return armature is not None and is_valid_armature(armature) and (len(get_all_meshes(context)) > 0) and (context.mode == "OBJECT")

    def execute(self, context: Context) -> set[str]:
        #Shamefully taken from: https://blender.stackexchange.com/a/237611
        #at least I am crediting them - @989onan
        for ob in get_all_meshes(context):
            if not ob.data.shape_keys: continue
            if not ob.data.shape_keys.use_relative: continue

            kbs = ob.data.shape_keys.key_blocks
            nverts = len(ob.data.vertices)
            to_delete = []

            # Cache locs for rel keys since many keys have the same rel key
            cache = {}

            locs = np.empty(3*nverts, dtype=np.float32)

            for kb in kbs:
                if kb == kb.relative_key: continue

                kb.data.foreach_get("co", locs)

                if kb.relative_key.name not in cache:
                    rel_locs = np.empty(3*nverts, dtype=np.float32)
                    kb.relative_key.data.foreach_get("co", rel_locs)
                    cache[kb.relative_key.name] = rel_locs
                rel_locs = cache[kb.relative_key.name]

                locs -= rel_locs
                if (np.abs(locs) < self.tolerance).all():
                    to_delete.append(kb.name)

            for kb_name in to_delete:
                if ("-" in kb_name) or ("=" in kb_name) or ("~" in kb_name): #don't delete category names. - @989onan
                    continue
                ob.shape_key_remove(ob.data.shape_keys.key_blocks[kb_name])