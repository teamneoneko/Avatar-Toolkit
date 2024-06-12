if "bpy" not in locals():
    import bpy
    from . import panel, quick_access, optimization
else:
    import importlib
    # Reload the modules to reflect changes during development
    importlib.reload(panel)
    importlib.reload(quick_access)
    importlib.reload(optimization)

def register():
    print("UI register called")
    from ..core.register import iter_classes_to_register
    # Iterate over the classes to register and register them
    for cls in iter_classes_to_register():
        bpy.utils.register_class(cls)

def unregister():
    print("UI unregister called")
    from ..core.register import iter_classes_to_register
    # Iterate over the classes to unregister in reverse order and unregister them
    for cls in reversed(list(iter_classes_to_register())):
        bpy.utils.unregister_class(cls)
