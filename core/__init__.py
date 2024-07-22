# core/__init__.py

from .register import register_wrap

#to reload all things in this directory and import them properly - @989onan
if "bpy" not in locals():
    import bpy
    import glob
    import os
    from os.path import dirname, basename, isfile, join
    modules = glob.glob(join(dirname(__file__), "*.py"))
    for module_name in [ basename(f)[:-3] for f in modules if isfile(f) and not f.endswith('__init__.py')]:
        exec("from . import "+module_name)
        print("importing " +module_name)
else:
    import importlib
    modules = glob.glob(join(dirname(__file__), "*.py"))
    for module_name in [ basename(f)[:-3] for f in modules if isfile(f) and not f.endswith('__init__.py')]:
        exec("importlib.reload("+module_name+")")
        print("reloading " +module_name)
