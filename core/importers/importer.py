import bpy
import logging
import os
import typing
from typing import Optional, Callable, Dict, List, Union, Set
from ..common import clear_default_objects
from .import_pmx import import_pmx
from .import_pmd import import_pmd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger: logging.Logger = logging.getLogger(__name__)

import importlib.util

if importlib.util.find_spec("io_scene_valvesource") is not None:
    from io_scene_valvesource.import_smd import SmdImporter

class ImportProgress:
    """Tracks and logs the progress of multi-file imports"""
    def __init__(self, total_files: int):
        self.total: int = total_files
        self.current: int = 0
        
    def update(self, filename: str) -> None:
        """Update import progress and log current file"""
        self.current += 1
        logger.info(f"Importing {filename} ({self.current}/{self.total})")

def validate_file(filepath: str) -> bool:
    """
    Validate if a file exists and is accessible
    Returns: True if file is valid, False otherwise
    """
    if not os.path.exists(filepath):
        logger.error(f"File not found: {filepath}")
        return False
    if not os.path.isfile(filepath):
        logger.error(f"Not a file: {filepath}")
        return False
    return True

def import_multi_files(
    method: Optional[Callable] = None, 
    directory: Optional[str] = None, 
    files: Optional[List[Dict[str, str]]] = None, 
    filepath: str = "",
    progress_callback: Optional[Callable[[str], None]] = None
) -> None:
    """
    Import multiple files using the specified import method
    
    Args:
        method: Import method to use
        directory: Directory containing files
        files: List of files to import
        filepath: Single file path to import
        progress_callback: Callback for progress updates
    """
    try:
        if not method:
            raise ValueError("Import method not specified")

        if not files:
            if not validate_file(filepath):
                return
            method(directory, filepath)
            if progress_callback:
                progress_callback(filepath)
        else:
            progress = ImportProgress(len(files))
            for file in files:
                fullpath: str = os.path.join(directory, os.path.basename(file["name"]))
                if not validate_file(fullpath):
                    continue
                    
                logger.info(f"Importing file: {fullpath}")
                method(directory, fullpath)
                
                if progress_callback:
                    progress_callback(fullpath)
                progress.update(file["name"])
                
    except Exception as e:
        logger.error(f"Import failed: {str(e)}", exc_info=True)
        raise

ImportMethod = Callable[[str, List[Dict[str, str]], str], None]

import_types: Dict[str, ImportMethod] = {
    "fbx": lambda directory, files, filepath: bpy.ops.import_scene.fbx(
        files=files, directory=directory, filepath=filepath, 
        automatic_bone_orientation=False, use_prepost_rot=False, use_anim=False
    ),
    "smd": lambda directory, files, filepath: eval("bpy."+SmdImporter.bl_idname+".(files=files, directory=directory, filepath=filepath)"),
    "dmx": lambda directory, files, filepath: eval("bpy."+SmdImporter.bl_idname+".(files=files, directory=directory, filepath=filepath)"),
    "gltf": lambda directory, files, filepath: bpy.ops.import_scene.gltf(files=files, filepath=filepath),
    "glb": lambda directory, files, filepath: bpy.ops.import_scene.gltf(files=files, filepath=filepath),
    "qc": lambda directory, files, filepath: eval("bpy."+SmdImporter.bl_idname+".(files=files, directory=directory, filepath=filepath)"),
    "obj": lambda directory, files, filepath: bpy.ops.wm.obj_import(files=files, directory=directory, filepath=filepath),
    "dae": lambda directory, files, filepath: import_multi_files(
        directory=directory, 
        files=files, 
        filepath=filepath, 
        method=lambda directory, filepath: bpy.ops.wm.collada_import(
            filepath=filepath, auto_connect=True, find_chains=True, fix_orientation=True
        )
    ),
    "3ds": lambda directory, files, filepath: bpy.ops.import_scene.max3ds(files=files, directory=directory, filepath=filepath),
    "stl": lambda directory, files, filepath: bpy.ops.import_mesh.stl(files=files, directory=directory, filepath=filepath),
    "mtl": lambda directory, files, filepath: bpy.ops.wm.obj_import(files=files, directory=directory, filepath=filepath),
    "x3d": lambda directory, files, filepath: bpy.ops.import_scene.x3d(files=files, directory=directory, filepath=filepath),
    "wrl": lambda directory, files, filepath: bpy.ops.import_scene.x3d(files=files, directory=directory, filepath=filepath),
    "vmd": lambda directory, files, filepath: import_multi_files(
        directory=directory, 
        files=files, 
        filepath=filepath, 
        method=lambda directory, filepath: bpy.ops.tuxedo.import_mmd_animation(directory=directory, filepath=filepath)
    ),
    "vrm": lambda directory, files, filepath: bpy.ops.import_scene.vrm(filepath=filepath),
    "pmx": lambda directory, files, filepath: import_pmx(filepath),
    "pmd": lambda directory, files, filepath: import_pmd(filepath),
    "animx": (lambda directory, files, filepath : bpy.ops.avatar_toolkit.animx_importer(directory=directory,files=files,filepath=filepath)),
}

def concat_imports_filter(imports: Dict[str, ImportMethod]) -> str:
    """Create a file filter string from import types"""
    return "".join(f"*.{importer};" for importer in imports.keys())

imports: str = concat_imports_filter(import_types)
