if "bpy" not in locals():
    import bpy
    from . import ui
    from . import core
    from . import functions
    from .core import register
    from .core.register import __bl_ordered_classes
    from .core import properties
    from .core import addon_preferences
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
    for cls in __bl_ordered_classes:
        print("registering" + str(cls))
        bpy.utils.register_class(cls)   
    
    
    
    # Register the properties
    for cls in core.register.__bl_ordered_classes:
        print("registering " + str(cls))
        bpy.utils.register_class(cls)

    #finally register properties that may use some classes.
    core.register.register_properties()

def unregister():
    print("Unregistering Avatar Toolkit")
    # Unregister the UI classes

    # Iterate over the classes to unregister in reverse order and unregister them
    for cls in reversed(list(__bl_ordered_classes)):
        bpy.utils.unregister_class(cls)
        print("unregistering " + str(cls))
    core.register.unregister_properties()
    properties.unregister()
