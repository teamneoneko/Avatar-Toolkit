import os
import bpy
import sys
import typing
import inspect
import pkgutil
import tomllib
import importlib
from pathlib import Path

__all__ = (
    "init",
    "register",
    "unregister",
)

modules = None
ordered_classes = None

def init():
    global modules
    global ordered_classes
    print("Auto-load init starting")
    modules = get_all_submodules(Path(__file__).parent.parent)
    ordered_classes = get_ordered_classes_to_register(modules)
    print(f"Found modules: {modules}")
    print(f"Found classes: {ordered_classes}")

def register():
    print("Registering classes")
    for cls in ordered_classes:
        print(f"Registering: {cls}")
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            continue

    for module in modules:
        if module.__name__ == __name__:
            continue
        if hasattr(module, "register"):
            module.register()

def unregister():
    for cls in reversed(ordered_classes):
        bpy.utils.unregister_class(cls)

    for module in modules:
        if module.__name__ == __name__:
            continue
        if hasattr(module, "unregister"):
            module.unregister()

def get_manifest_id():
    manifest_path = Path(__file__).parent.parent / "blender_manifest.toml"
    with open(manifest_path, "rb") as f:
        manifest = tomllib.load(f)
    return manifest["id"]

def get_all_submodules(directory):
    modules = []
    addon_id = get_manifest_id()
    for root, dirs, files in os.walk(directory):
        if "__pycache__" in root:
            continue
        path = Path(root)
        if path == directory:
            package_name = f"bl_ext.user_default.{addon_id}"
        else:
            relative_path = path.relative_to(directory).as_posix().replace('/', '.')
            package_name = f"bl_ext.user_default.{addon_id}.{relative_path}"
        for name in sorted(iter_module_names(path)):
            modules.append(importlib.import_module(f".{name}", package_name))
    return modules

def iter_submodules(path, package_name):
    for name in sorted(iter_module_names(path)):
        yield importlib.import_module("." + name, package_name)

def iter_module_names(path):
    print(f"Scanning path: {path}")  # Debug path
    modules_list = list(pkgutil.iter_modules([str(path)]))
    print(f"Found these modules: {modules_list}")  # Debug modules
    for _, module_name, is_pkg in modules_list:
        if not is_pkg:
            print(f"Found module: {module_name}")
            yield module_name



def get_ordered_classes_to_register(modules):
    return toposort(get_register_deps_dict(modules))

def get_register_deps_dict(modules):
    deps_dict = {}
    classes_to_register = set(iter_classes_to_register(modules))
    for cls in classes_to_register:
        deps_dict[cls] = set(iter_own_register_deps(cls, classes_to_register))
    return deps_dict

def iter_own_register_deps(cls, classes_to_register):
    yield from (dep for dep in iter_register_deps(cls) if dep in classes_to_register)

def iter_register_deps(cls):
    for value in typing.get_type_hints(cls, {}, {}).values():
        dependency = get_dependency_from_annotation(value)
        if dependency is not None:
            yield dependency

def get_dependency_from_annotation(value):
    if isinstance(value, tuple) and len(value) == 2:
        if value[0] in (bpy.props.PointerProperty, bpy.props.CollectionProperty):
            return value[1]["type"]
    return None

def iter_classes_to_register(modules):
    base_types = get_register_base_types()
    for cls in get_classes_in_modules(modules):
        if any(base in base_types for base in cls.__bases__):
            if not getattr(cls, "_is_registered", False):
                yield cls

def get_classes_in_modules(modules):
    classes = set()
    for module in modules:
        for cls in iter_classes_in_module(module):
            classes.add(cls)
    return classes

def iter_classes_in_module(module):
    for value in module.__dict__.values():
        if inspect.isclass(value):
            yield value

def get_register_base_types():
    return set(getattr(bpy.types, name) for name in [
        "Panel", "Operator", "PropertyGroup",
        "AddonPreferences", "Header", "Menu",
        "Node", "NodeSocket", "NodeTree",
        "UIList", "RenderEngine"
    ])

def toposort(deps_dict):
    sorted_list = []
    sorted_values = set()
    
    # First pass: Register panels without parents
    panels_to_sort = [(value, deps) for value, deps in deps_dict.items() 
                      if hasattr(value, 'bl_parent_id')]
    
    base_panels = [(value, deps) for value, deps in deps_dict.items() 
                   if not hasattr(value, 'bl_parent_id')]
    
    # Add base panels first
    for value, deps in base_panels:
        if len(deps) == 0:
            sorted_list.append(value)
            sorted_values.add(value)
    
    # Then add child panels
    while len(deps_dict) > len(sorted_values):
        unsorted = []
        for value, deps in deps_dict.items():
            if value not in sorted_values:
                if len(deps - sorted_values) == 0:
                    sorted_list.append(value)
                    sorted_values.add(value)
                else:
                    unsorted.append(value)
    
    return sorted_list

