"""
MMD Converter - Core conversion logic for MMD models
Handles armature hierarchy and naming conventions
"""
import bpy
from typing import Dict, List, Optional, Tuple, Set
from bpy.types import Object, Bone, Collection
from .common import get_active_armature
from .dictionaries import simplify_bonename
from .enhanced_dictionaries import mmd_bone_patterns
from .logging_setup import logger
from .translations import t


def detect_mmd_armature(armature: Object) -> bool:
    """Detect if armature uses MMD bone naming conventions"""

    if not armature or armature.type != 'ARMATURE':
        return False
    
    found_mmd_bones = 0
    for bone in armature.data.bones:
        bone_name_lower = bone.name.lower()
        if any(pattern.lower() in bone_name_lower for pattern in mmd_bone_patterns):
            found_mmd_bones += 1
            logger.debug(f"Found MMD bone: {bone.name}")
    
    # Consider it MMD if we find at least 5 MMD bones
    logger.debug(f"Found {found_mmd_bones} MMD bones in armature {armature.name}")
    return found_mmd_bones >= 5


def get_armature_parent_object(armature: Object) -> Optional[Object]:
    """Get the parent object of the armature (typically an Empty in MMD imports)"""
    if armature and armature.parent:
        return armature.parent
    return None


def make_armature_main_parent(armature: Object) -> Tuple[bool, str]:
    """Make the armature the main parent object by removing any parent empties
    and reparenting all children to the armature."""

    if not armature or armature.type != 'ARMATURE':
        return False, t("MMD.error.invalid_armature")
    
    logger.info(f"Making armature '{armature.name}' the main parent")
    
    # Store original parent
    original_parent = armature.parent
    
    if not original_parent:
        logger.info("Armature already has no parent")
        return True, t("MMD.armature_already_root")
    
    parent_name = original_parent.name
    parent_type = original_parent.type
    
    logger.info(f"Found parent: {parent_name} (type: {parent_type})")
    
    # Get all children of the parent
    siblings = [child for child in original_parent.children if child != armature]

    armature.parent = None
    
    # Reparent siblings to the armature
    reparented_count = 0
    for sibling in siblings:
        sibling.parent = armature
        reparented_count += 1
        logger.debug(f"Reparented {sibling.name} to armature")
    
    # If the parent was an Empty and now has no children, remove it
    if parent_type == 'EMPTY' and len(original_parent.children) == 0:
        try:
            bpy.data.objects.remove(original_parent, do_unlink=True)
            logger.info(f"Removed empty parent object: {parent_name}")
            message = t("MMD.parent_removed_and_reparented", 
                       parent_name=parent_name, 
                       count=reparented_count)
        except Exception as e:
            logger.warning(f"Could not remove parent empty: {str(e)}")
            message = t("MMD.parent_unlinked_and_reparented",
                       parent_name=parent_name,
                       count=reparented_count)
    else:
        message = t("MMD.parent_unlinked", parent_name=parent_name)
    
    logger.info(f"Successfully made armature the main parent. Reparented {reparented_count} objects")
    return True, message


def rename_armature_to_standard(armature: Object) -> Tuple[bool, str]:
    """Rename the armature object to 'Armature' (standard Blender convention)"""
    if not armature or armature.type != 'ARMATURE':
        return False, t("MMD.error.invalid_armature")
    
    old_name = armature.name
    
    # Check if already named 'Armature'
    if old_name == 'Armature':
        logger.info("Armature already named 'Armature'")
        return True, t("MMD.armature_already_named")
    
    logger.info(f"Renaming armature from '{old_name}' to 'Armature'")
    
    try:
        armature.name = 'Armature'
        # Blender might append .001 if name exists, check actual result (Wonder if needed)
        actual_name = armature.name
        
        if actual_name == 'Armature':
            message = t("MMD.armature_renamed", old_name=old_name, new_name='Armature')
        else:
            message = t("MMD.armature_renamed_with_suffix", 
                       old_name=old_name, 
                       new_name=actual_name)
            logger.warning(f"Name collision, armature named: {actual_name}")
        
        logger.info(f"Successfully renamed armature to: {actual_name}")
        return True, message
        
    except Exception as e:
        logger.error(f"Failed to rename armature: {str(e)}")
        return False, t("MMD.error.rename_failed", error=str(e))


def convert_mmd_armature(armature: Object, 
                        make_parent: bool = True, 
                        rename_armature: bool = True) -> Tuple[bool, List[str]]:
    """Convert MMD armature to standard Blender format"""
    if not armature or armature.type != 'ARMATURE':
        return False, [t("MMD.error.invalid_armature")]
    
    logger.info(f"Starting MMD armature conversion for: {armature.name}")
    
    # Check if this is an MMD armature
    if not detect_mmd_armature(armature):
        return False, [t("MMD.error.not_mmd_armature")]
    
    messages = []
    overall_success = True
    
    # Step 1: Make armature the main parent
    if make_parent:
        success, message = make_armature_main_parent(armature)
        messages.append(message)
        if not success:
            overall_success = False
            logger.warning("Failed to make armature main parent")
    
    # Step 2: Rename armature
    if rename_armature:
        success, message = rename_armature_to_standard(armature)
        messages.append(message)
        if not success:
            overall_success = False
            logger.warning("Failed to rename armature")
    
    if overall_success:
        logger.info("MMD armature conversion completed successfully")
        messages.append(t("MMD.conversion_complete"))
    else:
        logger.warning("MMD armature conversion completed with errors")
    
    return overall_success, messages
