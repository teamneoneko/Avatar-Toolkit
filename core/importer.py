import bpy

# Importers which don't need much code should be added here, however if a importer needs alot of code
# Like the PMX and PMD importers, they should be added to their own files.


# FBX Importer settings borrowed form Cat's Blender Plugin
def import_fbx(filepath):
    try:
        bpy.ops.import_scene.fbx(
            filepath=filepath,
            automatic_bone_orientation=False,
            use_prepost_rot=False,
            use_anim=False
        )
    except (TypeError, ValueError) as e:
        print(f"Error importing FBX: {str(e)}")
