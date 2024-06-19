

if "bpy" not in locals():
    import bpy
    from . import ui
    from . import core
    from . import functions
    from .core import register
    from .core.register import __bl_ordered_classes
    from .core.translation import load_translation_dictionary, t
else:
    import importlib
    importlib.reload(ui)
    importlib.reload(core)
    importlib.reload(functions)



settings: dict = {}

def register():
    from os.path import dirname, isfile, join
    import json
    


    print("Registering Avatar Toolkit")
    # Order the classes before registration
    core.register.order_classes()
    
    # Register the UI classes
    
    # Iterate over the classes to register and register them
    for cls in __bl_ordered_classes:
        print("registering " + str(cls))
        bpy.utils.register_class(cls)   
    
def unregister():
    print("Unregistering Avatar Toolkit")
    # Unregister the UI classes
    
    # Iterate over the classes to unregister in reverse order and unregister them
    for cls in reversed(list(__bl_ordered_classes)):
        bpy.utils.unregister_class(cls)
        print("unregistering " + str(cls))
