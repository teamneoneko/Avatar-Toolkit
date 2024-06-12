import bpy
import typing

# List to store the classes to register
__bl_classes = []
# List to store the ordered classes for registration
__bl_ordered_classes = []

def register_wrap(cls):
    # Check if the class has a 'bl_rna' attribute (indicating it's a Blender class)
    if hasattr(cls, 'bl_rna'):
        # Add the class to the list of classes to register
        __bl_classes.append(cls)
    return cls

def order_classes():
    global __bl_ordered_classes
    # Create a copy of the classes list to store the ordered classes
    __bl_ordered_classes = __bl_classes.copy()

def iter_classes_to_register():
    # Iterate over the ordered classes and yield each class for registration
    for cls in __bl_ordered_classes:
        yield cls
