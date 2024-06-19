import bpy
import typing

# List to store the classes to register
__bl_classes = []
# List to store the ordered classes for registration
__bl_ordered_classes = []
# List to store props to register
__bl_props = []

def register_wrap(cls):
    # Check if the class has a 'bl_rna' attribute (indicating it's a Blender class)
    if hasattr(cls, 'bl_rna'):
        # Add the class to the list of classes to register
        __bl_classes.append(cls)
    return cls

# Register all properties
def register_property(prop):
    __bl_props.append(prop)

def register_properties():
    for prop in __bl_props:
        setattr(prop[0], prop[1], prop[2])

def unregister_properties():
    for prop in reversed(__bl_props):
        delattr(prop[0], prop[1])

#- @989onan had to add this from Cats. This is extremely important else you will be screamed at by register order issues!
# Find order to register to solve dependencies

#################################################

def toposort(deps_dict):
    sorted_list = []
    sorted_values = set()
    while len(deps_dict) > 0:
        unsorted = []
        for value, deps in deps_dict.items():
            if len(deps) == 0:
                sorted_list.append(value)
                sorted_values.add(value)
            else:
                unsorted.append(value)
        deps_dict = {value : deps_dict[value] - sorted_values for value in unsorted}
    
    sort_order(sorted_list) #to sort by 'bl_order' so we can choose how things may appear in the ui
    return sorted_list



def order_classes():
    deps_dict = {}
    classes_to_register = set(iter_classes_to_register())
    for class_obj in classes_to_register:
        deps_dict[class_obj] = set(iter_own_register_deps(class_obj, classes_to_register))

    __bl_ordered_classes.clear()
    # Then put everything else sorted into the list
    for class_obj in toposort(deps_dict):
        __bl_ordered_classes.append(class_obj)
        
    print(__bl_ordered_classes)
    __bl_classes.clear()


def iter_classes_to_register():
    for class_obj in __bl_classes:
        yield class_obj


def iter_own_register_deps(class_obj, own_classes):
    yield from (dep for dep in iter_register_deps(class_obj) if dep in own_classes)


def iter_register_deps(class_obj):
    for value in typing.get_type_hints(class_obj, {}, {}, True).values():
        dependency = get_dependency_from_annotation(value)
        if dependency is not None:
            yield dependency
    if hasattr(class_obj, "bl_parent_id"):
        if class_obj.bl_parent_id != "":
            for dependency in __bl_classes:
                if dependency.bl_idname == class_obj.bl_parent_id:
                    yield dependency

def get_dependency_from_annotation(value):
    if isinstance(value, tuple) and len(value) == 2:
        if value[0] in (bpy.props.PointerProperty, bpy.props.CollectionProperty):
            return value[1]["type"]
    return None


# Find order to register to solve dependencies
#################################################

def toposort(deps_dict):
    sorted_list = []
    sorted_values = set()
    while len(deps_dict) > 0:
        unsorted = []
        for value, deps in deps_dict.items():
            if len(deps) == 0:
                sorted_list.append(value)
                sorted_values.add(value)
            else:
                unsorted.append(value)
        deps_dict = {value : deps_dict[value] - sorted_values for value in unsorted}
    
    return sorted_list

