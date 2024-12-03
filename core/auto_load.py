import os
import bpy
import sys
import typing
import inspect
import pkgutil
import tomllib
import importlib
from pathlib import Path
from typing import List, Dict, Set, Optional, Any, Type, Tuple, Generator, TypeVar

__all__ = (
    "init",
    "register",
    "unregister",
)

T = TypeVar('T')
modules: Optional[List[Any]] = None
ordered_classes: Optional[List[Type]] = None

def init() -> None:
    """Initialize the auto-loader by discovering modules and classes"""
    global modules
    global ordered_classes
    print("Auto-load init starting")
    modules = get_all_submodules(Path(__file__).parent.parent)
    ordered_classes = get_ordered_classes_to_register(modules)
    print(f"Found modules: {modules}")
    print(f"Found classes: {ordered_classes}")

def register() -> None:
    """Register all discovered classes and modules"""
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

def unregister() -> None:
    """Unregister all classes and modules in reverse order"""
    for cls in reversed(ordered_classes):
        bpy.utils.unregister_class(cls)

    for module in modules:
        if module.__name__ == __name__:
            continue
        if hasattr(module, "unregister"):
            module.unregister()

def get_manifest_id() -> str:
    """Get the addon ID from the manifest file"""
    manifest_path = Path(__file__).parent.parent / "blender_manifest.toml"
    with open(manifest_path, "rb") as f:
        manifest = tomllib.load(f)
    return manifest["id"]

def get_all_submodules(directory: Path) -> List[Any]:
    """Discover and import all submodules in the given directory"""
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

def iter_submodules(path: Path, package_name: str) -> Generator[Any, None, None]:
    """Iterate through submodules in a package"""
    for name in sorted(iter_module_names(path)):
        yield importlib.import_module("." + name, package_name)

def iter_module_names(path: Path) -> Generator[str, None, None]:
    """Iterate through module names in a directory"""
    print(f"Scanning path: {path}")
    modules_list = list(pkgutil.iter_modules([str(path)]))
    print(f"Found these modules: {modules_list}")
    for _, module_name, is_pkg in modules_list:
        if not is_pkg:
            print(f"Found module: {module_name}")
            yield module_name

def get_ordered_classes_to_register(modules: List[Any]) -> List[Type]:
    """Get a topologically sorted list of classes to register"""
    return toposort(get_register_deps_dict(modules))

def get_register_deps_dict(modules: List[Any]) -> Dict[Type, Set[Type]]:
    """Get dependencies dictionary for class registration"""
    deps_dict = {}
    classes_to_register = set(iter_classes_to_register(modules))
    for cls in classes_to_register:
        deps_dict[cls] = set(iter_own_register_deps(cls, classes_to_register))
    return deps_dict

def iter_own_register_deps(cls: Type, classes_to_register: Set[Type]) -> Generator[Type, None, None]:
    """Iterate through a class's own registration dependencies"""
    yield from (dep for dep in iter_register_deps(cls) if dep in classes_to_register)

def iter_register_deps(cls: Type) -> Generator[Type, None, None]:
    """Iterate through all registration dependencies of a class"""
    for value in typing.get_type_hints(cls, {}, {}).values():
        dependency = get_dependency_from_annotation(value)
        if dependency is not None:
            yield dependency

def get_dependency_from_annotation(value: Any) -> Optional[Type]:
    """Get dependency type from a type annotation"""
    if isinstance(value, tuple) and len(value) == 2:
        if value[0] in (bpy.props.PointerProperty, bpy.props.CollectionProperty):
            return value[1]["type"]
    return None

def iter_classes_to_register(modules: List[Any]) -> Generator[Type, None, None]:
    """Iterate through classes that need to be registered"""
    base_types = get_register_base_types()
    for cls in get_classes_in_modules(modules):
        if any(base in base_types for base in cls.__bases__):
            if not getattr(cls, "_is_registered", False):
                yield cls

def get_classes_in_modules(modules: List[Any]) -> Set[Type]:
    """Get all classes defined in the modules"""
    classes = set()
    for module in modules:
        for cls in iter_classes_in_module(module):
            classes.add(cls)
    return classes

def iter_classes_in_module(module: Any) -> Generator[Type, None, None]:
    """Iterate through classes defined in a module"""
    for value in module.__dict__.values():
        if inspect.isclass(value):
            yield value

def get_register_base_types() -> Set[Type]:
    """Get set of base types that need registration"""
    return set(getattr(bpy.types, name) for name in [
        "Panel", "Operator", "PropertyGroup",
        "AddonPreferences", "Header", "Menu",
        "Node", "NodeSocket", "NodeTree",
        "UIList", "RenderEngine"
    ])

def toposort(deps_dict: Dict[Type, Set[Type]]) -> List[Type]:
    """Topologically sort classes based on their dependencies"""
    sorted_list = []
    sorted_values = set()
    
    panels_to_sort = [(value, deps) for value, deps in deps_dict.items() 
                      if hasattr(value, 'bl_parent_id')]
    
    base_panels = [(value, deps) for value, deps in deps_dict.items() 
                   if not hasattr(value, 'bl_parent_id')]
    
    for value, deps in base_panels:
        if len(deps) == 0:
            sorted_list.append(value)
            sorted_values.add(value)
    
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
