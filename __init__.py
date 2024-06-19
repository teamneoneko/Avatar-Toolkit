if "bpy" not in locals():
    import bpy
    from . import ui
    from . import core
    from . import functions
    from .core import register
    from .core.register import __bl_ordered_classes
    from .core import properties
else:
    import importlib
    importlib.reload(ui)
    importlib.reload(core)
    importlib.reload(functions)
    importlib.reload(properties)

def register():
    print("Registering Avatar Toolkit")
    properties.register()
    core.register.order_classes()
    core.register.register_properties()
    for cls in core.register.__bl_ordered_classes:
        print("registering " + str(cls))
        bpy.utils.register_class(cls)

def unregister():
    print("Unregistering Avatar Toolkit")
    for cls in reversed(core.register.__bl_ordered_classes):
        bpy.utils.unregister_class(cls)
        print("unregistering " + str(cls))
    core.register.unregister_properties()
    properties.unregister()
