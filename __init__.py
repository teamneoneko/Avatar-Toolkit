import bpy
from . import ui
from .core.register import order_classes

def register():
    print("Registering Avatar Toolkit")
    # Order the classes before registration
    order_classes()
    # Register the UI classes
    ui.register()

def unregister():
    print("Unregistering Avatar Toolkit")
    # Unregister the UI classes
    ui.unregister()
