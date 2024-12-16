modules = None
ordered_classes = None

def register():
    from .core import auto_load
    print("Starting registration")
    auto_load.init()
    auto_load.register()
    print("Registration complete")

def unregister():
    from .core import auto_load
    auto_load.unregister()
