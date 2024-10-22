if "bpy" not in locals():
    import bpy
    from . import ui
    from . import core
    from . import functions
    from .core import register
    from .core.register import __bl_ordered_classes
    from .core import properties
    from .core import addon_preferences
    from .core.updater import check_for_update_on_start
else:
    import importlib
    importlib.reload(ui)
    importlib.reload(core)
    importlib.reload(functions)
    importlib.reload(properties)
    importlib.reload(addon_preferences)

def register():
    print("Registering Avatar Toolkit")
    # Register the addon properties
    properties.register()

    # Load the translations
    functions.translations.load_translations()

    # Order the classes before registration
    core.register.order_classes()
    # Register the UI classes
    for cls in core.register.__bl_ordered_classes:
        print("registering " + str(cls))
        bpy.utils.register_class(cls)

    #finally register properties that may use some classes.
    core.register.register_properties()

    bpy.app.handlers.load_post.append(check_for_update_on_start)

    from .functions.mesh_tools import AvatarToolkit_OT_ApplyShapeKey
    
    bpy.types.MESH_MT_shape_key_context_menu.append((lambda self, context: self.layout.separator()))
    bpy.types.MESH_MT_shape_key_context_menu.append((lambda self, context: self.layout.operator(AvatarToolkit_OT_ApplyShapeKey.bl_idname, icon="KEY_HLT")))

def unregister():
    print("Unregistering Avatar Toolkit")
    # Unregister the UI classes
    if check_for_update_on_start in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(check_for_update_on_start)

    # Iterate over the classes to unregister in reverse order and unregister them
    for cls in reversed(list(__bl_ordered_classes)):
        bpy.utils.unregister_class(cls)
        print("unregistering " + str(cls))
    core.register.unregister_properties()
    properties.unregister()
