"""
MMD Converter - Core conversion logic for MMD models
Handles armature hierarchy and naming conventions
"""
import bpy
from typing import Dict, List, Optional, Tuple, Set
from bpy.types import Object, Bone, Collection, Material, ShapeKey
from .common import get_active_armature
from .dictionaries import simplify_bonename
from .enhanced_dictionaries import mmd_bone_patterns
from .logging_setup import logger
from .translations import t
from .mmd.translations import jp_to_en_tuples, translateFromJp


# MMD to Unity bone mapping
# Maps MMD bone names (after English translation) to Unity humanoid bone names
mmd_to_unity_bone_map = {
    # Root and core
    "ParentNode": None,  # Remove this
    "Center": "Hips",
    "センター": "Hips",
    "Groove": None,  # Remove this
    "グルーブ": None,
    "Waist": None,  # Will be merged into Hips
    
    # Spine chain
    "LowerBody": "Hips",
    "下半身": "Hips",
    "UpperBody": "Spine",
    "上半身": "Spine",
    "UpperBody2": "Chest",
    "上半身2": "Chest",
    "Neck": "Neck",
    "首": "Neck",
    "Head": "Head",
    "頭": "Head",
    
    # Right leg
    "RightLeg": "Right leg",
    "右足": "Right leg",
    "RightLegD": None,  # Remove D variant
    "RightKnee": "Right knee",
    "右ひざ": "Right knee",
    "RightAnkle": "Right ankle",
    "右足首": "Right ankle",
    "RightToe": "Right toe",
    "右つま先": "Right toe",
    
    # Left leg  
    "LeftLeg": "Left leg",
    "左足": "Left leg",
    "LeftLegD": None,  # Remove D variant
    "LeftKnee": "Left knee",
    "左ひざ": "Left knee",
    "LeftAnkle": "Left ankle",
    "左足首": "Left ankle",
    "LeftToe": "Left toe",
    "左つま先": "Left toe",
    
    # Right arm
    "RightShoulder": "Right shoulder",
    "右肩": "Right shoulder",
    "RightArm": "Right arm",
    "右腕": "Right arm",
    "RightElbow": "Right elbow",
    "右ひじ": "Right elbow",
    "RightWrist": "Right wrist",
    "右手首": "Right wrist",
    
    # Left arm
    "LeftShoulder": "Left shoulder",
    "左肩": "Left shoulder",
    "LeftArm": "Left arm",
    "左腕": "Left arm",
    "LeftElbow": "Left elbow",
    "左ひじ": "Left elbow",
    "LeftWrist": "Left wrist",
    "左手首": "Left wrist",
    
    # Cancel/Helper bones (remove these)
    "WaistCancelRight": None,
    "WaistCancelLeft": None,
    "LegIKParentRight": None,
    "LegIKParentLeft": None,
}


# Unity humanoid bone hierarchy
# Defines parent-child relationships for Unity standard
unity_bone_hierarchy = {
    "Hips": None,  # Root bone
    "Spine": "Hips",
    "Chest": "Spine",
    "Neck": "Chest",
    "Head": "Neck",
    
    # Arms
    "Left shoulder": "Chest",
    "Left arm": "Left shoulder",
    "Left elbow": "Left arm",
    "Left wrist": "Left elbow",
    
    "Right shoulder": "Chest",
    "Right arm": "Right shoulder",
    "Right elbow": "Right arm",
    "Right wrist": "Right elbow",
    
    # Legs
    "Left leg": "Hips",
    "Left knee": "Left leg",
    "Left ankle": "Left knee",
    "Left toe": "Left ankle",
    
    "Right leg": "Hips",
    "Right knee": "Right leg",
    "Right ankle": "Right knee",
    "Right toe": "Right ankle",
}


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


def translate_mmd_name(name: str, category: str = "auto") -> Tuple[str, str]:
    """Translate MMD name using MMD dictionary first, then translation services"""
    if not name or not name.strip():
        return name, "unchanged"
    
    original_name = name.strip()
    
    # Step 1: Try MMD built-in dictionary translation
    mmd_translated = translateFromJp(original_name)
    
    # Check if MMD dictionary actually translated something
    if mmd_translated != original_name and mmd_translated:
        logger.debug(f"MMD dictionary translated: '{original_name}' -> '{mmd_translated}'")
        return mmd_translated, "mmd_dictionary"
    
    # Step 2: If MMD dictionary didn't translate or only partially translated,
    # use Avatar Toolkit translation services
    try:
        from .translation_manager import get_avatar_translation_manager
        
        manager = get_avatar_translation_manager()
        result = manager.translate_single(original_name, category=category, source_lang="ja", target_lang="en")
        
        if result.translated != original_name:
            logger.debug(f"API translated: '{original_name}' -> '{result.translated}' (method: {result.method})")
            return result.translated, "api_translation"
    except Exception as e:
        logger.warning(f"Translation service failed for '{original_name}': {e}")
    
    # Step 3: No translation available
    logger.debug(f"No translation available for: '{original_name}'")
    return original_name, "unchanged"


def translate_mmd_armature_bones(armature: Object, apply_translation: bool = True) -> Tuple[int, int, List[str]]:
    """Translate all bone names in an MMD armature"""
    if not armature or armature.type != 'ARMATURE':
        return 0, 0, [t("MMD.error.invalid_armature")]
    
    logger.info(f"Starting bone translation for armature: {armature.name}")
    
    successful = 0
    failed = 0
    messages = []
    bone_translations = {}
    
    # Store the current mode
    current_mode = bpy.context.mode
    if current_mode != 'EDIT':
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode='EDIT')
    
    try:
        for bone in armature.data.edit_bones:
            original_name = bone.name
            translated_name, method = translate_mmd_name(original_name, category="bones")
            
            if translated_name != original_name:
                bone_translations[original_name] = (translated_name, method)
                
                if apply_translation:
                    try:
                        bone.name = translated_name
                        logger.info(f"Translated bone: '{original_name}' -> '{translated_name}' ({method})")
                        successful += 1
                    except Exception as e:
                        logger.error(f"Failed to rename bone '{original_name}': {e}")
                        failed += 1
                else:
                    successful += 1
            else:
                logger.debug(f"Bone '{original_name}' not translated")
    
    finally:
        # Restore original mode
        if current_mode != 'EDIT':
            bpy.ops.object.mode_set(mode='OBJECT')
    
    # Generate summary messages
    if successful > 0:
        messages.append(t("MMD.bones_translated", count=successful))
    if failed > 0:
        messages.append(t("MMD.bones_failed", count=failed))
    
    mmd_dict_count = sum(1 for _, (_, method) in bone_translations.items() if method == "mmd_dictionary")
    api_count = sum(1 for _, (_, method) in bone_translations.items() if method == "api_translation")
    
    logger.info(f"Bone translation complete: {successful} successful, {failed} failed")
    logger.info(f"Translation methods: MMD Dictionary: {mmd_dict_count}, API: {api_count}")
    
    return successful, failed, messages


def translate_mmd_materials(armature: Object, apply_translation: bool = True) -> Tuple[int, int, List[str]]:
    """Translate all material names for meshes parented to the armature"""
    if not armature or armature.type != 'ARMATURE':
        return 0, 0, [t("MMD.error.invalid_armature")]
    
    logger.info(f"Starting material translation for armature: {armature.name}")
    
    successful = 0
    failed = 0
    messages = []
    processed_materials = set()
    
    # Get all mesh objects parented to this armature
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.parent == armature and obj.data.materials:
            for mat in obj.data.materials:
                if mat and mat.name not in processed_materials:
                    processed_materials.add(mat.name)
                    original_name = mat.name
                    translated_name, method = translate_mmd_name(original_name, category="materials")
                    
                    if translated_name != original_name and apply_translation:
                        try:
                            mat.name = translated_name
                            logger.info(f"Translated material: '{original_name}' -> '{translated_name}' ({method})")
                            successful += 1
                        except Exception as e:
                            logger.error(f"Failed to rename material '{original_name}': {e}")
                            failed += 1
                    elif translated_name != original_name:
                        successful += 1
    
    if successful > 0:
        messages.append(t("MMD.materials_translated", count=successful))
    if failed > 0:
        messages.append(t("MMD.materials_failed", count=failed))
    
    logger.info(f"Material translation complete: {successful} successful, {failed} failed")
    
    return successful, failed, messages


def translate_mmd_shapekeys(armature: Object, apply_translation: bool = True) -> Tuple[int, int, List[str]]:
    """Translate all shape key names for meshes parented to the armature"""
    if not armature or armature.type != 'ARMATURE':
        return 0, 0, [t("MMD.error.invalid_armature")]
    
    logger.info(f"Starting shape key translation for armature: {armature.name}")
    
    successful = 0
    failed = 0
    messages = []
    
    # Get all mesh objects parented to this armature
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.parent == armature and obj.data.shape_keys:
            for shape_key in obj.data.shape_keys.key_blocks:
                original_name = shape_key.name
                translated_name, method = translate_mmd_name(original_name, category="shapekeys")
                
                if translated_name != original_name and apply_translation:
                    try:
                        shape_key.name = translated_name
                        logger.info(f"Translated shape key: '{original_name}' -> '{translated_name}' ({method})")
                        successful += 1
                    except Exception as e:
                        logger.error(f"Failed to rename shape key '{original_name}': {e}")
                        failed += 1
                elif translated_name != original_name:
                    successful += 1
    
    if successful > 0:
        messages.append(t("MMD.shapekeys_translated", count=successful))
    if failed > 0:
        messages.append(t("MMD.shapekeys_failed", count=failed))
    
    logger.info(f"Shape key translation complete: {successful} successful, {failed} failed")
    
    return successful, failed, messages


def translate_mmd_objects(armature: Object, apply_translation: bool = True) -> Tuple[int, int, List[str]]:
    """Translate object names parented to the armature"""
    if not armature or armature.type != 'ARMATURE':
        return 0, 0, [t("MMD.error.invalid_armature")]
    
    logger.info(f"Starting object name translation for armature: {armature.name}")
    
    successful = 0
    failed = 0
    messages = []
    
    # Get all objects parented to this armature
    for obj in bpy.data.objects:
        if obj.parent == armature:
            original_name = obj.name
            translated_name, method = translate_mmd_name(original_name, category="objects")
            
            if translated_name != original_name and apply_translation:
                try:
                    obj.name = translated_name
                    logger.info(f"Translated object: '{original_name}' -> '{translated_name}' ({method})")
                    successful += 1
                except Exception as e:
                    logger.error(f"Failed to rename object '{original_name}': {e}")
                    failed += 1
            elif translated_name != original_name:
                successful += 1
    
    if successful > 0:
        messages.append(t("MMD.objects_translated", count=successful))
    if failed > 0:
        messages.append(t("MMD.objects_failed", count=failed))
    
    logger.info(f"Object translation complete: {successful} successful, {failed} failed")
    
    return successful, failed, messages


def translate_mmd_everything(armature: Object, 
                            translate_bones: bool = True,
                            translate_materials: bool = True, 
                            translate_shapekeys: bool = True,
                            translate_objects: bool = True) -> Tuple[bool, List[str]]:
    """
    Translate all MMD names (bones, materials, shape keys, objects)
    
    Args:
        armature: The armature object
        translate_bones: Whether to translate bone names
        translate_materials: Whether to translate material names
        translate_shapekeys: Whether to translate shape key names
        translate_objects: Whether to translate object names
        
    Returns:
        Tuple of (success, messages)
    """
    if not armature or armature.type != 'ARMATURE':
        return False, [t("MMD.error.invalid_armature")]
    
    logger.info(f"Starting comprehensive MMD translation for: {armature.name}")
    
    all_messages = []
    total_successful = 0
    total_failed = 0
    
    # Translate bones
    if translate_bones:
        success, failed, messages = translate_mmd_armature_bones(armature, apply_translation=True)
        total_successful += success
        total_failed += failed
        all_messages.extend(messages)
    
    # Translate materials
    if translate_materials:
        success, failed, messages = translate_mmd_materials(armature, apply_translation=True)
        total_successful += success
        total_failed += failed
        all_messages.extend(messages)
    
    # Translate shape keys
    if translate_shapekeys:
        success, failed, messages = translate_mmd_shapekeys(armature, apply_translation=True)
        total_successful += success
        total_failed += failed
        all_messages.extend(messages)
    
    # Translate objects
    if translate_objects:
        success, failed, messages = translate_mmd_objects(armature, apply_translation=True)
        total_successful += success
        total_failed += failed
        all_messages.extend(messages)
    
    # Summary
    if total_successful > 0:
        all_messages.append(t("MMD.translation_complete", total=total_successful))
    
    logger.info(f"Comprehensive MMD translation complete: {total_successful} successful, {total_failed} failed")
    
    return total_failed == 0, all_messages


def restructure_mmd_to_unity_bones(armature: Object) -> Tuple[bool, List[str]]:
    """Restructure MMD bone hierarchy to Unity humanoid format."""
    if not armature or armature.type != 'ARMATURE':
        return False, [t("MMD.error.invalid_armature")]
    
    logger.info(f"Starting MMD to Unity bone restructuring for: {armature.name}")
    
    messages = []
    renamed_count = 0
    removed_count = 0
    reparented_count = 0
    
    # Store the current mode
    current_mode = bpy.context.mode
    if current_mode != 'EDIT':
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode='EDIT')
    
    try:
        edit_bones = armature.data.edit_bones
        bones_to_remove = []
        bone_renames = {}
        
        # Step 1: Identify and map bones
        for bone in edit_bones:
            bone_name = bone.name
            
            # Check if bone should be renamed
            unity_name = mmd_to_unity_bone_map.get(bone_name)
            
            if unity_name is None and bone_name not in mmd_to_unity_bone_map:
                # Try to find a match by checking if bone name contains a key
                for mmd_name, unity_target in mmd_to_unity_bone_map.items():
                    if mmd_name.lower() in bone_name.lower():
                        unity_name = unity_target
                        break
            
            if unity_name is None:
                # Mark for removal
                bones_to_remove.append(bone_name)
                logger.debug(f"Marking bone for removal: {bone_name}")
            elif unity_name != bone_name:
                # Mark for rename
                bone_renames[bone_name] = unity_name
                logger.debug(f"Planning rename: {bone_name} -> {unity_name}")
        
        # Step 2: Handle bone merging (e.g., LowerBody + Center -> Hips)
        unity_bone_sources = {}
        for old_name, new_name in bone_renames.items():
            if new_name not in unity_bone_sources:
                unity_bone_sources[new_name] = []
            unity_bone_sources[new_name].append(old_name)
        
        # For bones with multiple sources, keep the first one and remove others
        for unity_name, sources in unity_bone_sources.items():
            if len(sources) > 1:
                logger.info(f"Multiple bones map to '{unity_name}': {sources}")
                # Keep the first, mark others for removal and reparent their children
                keep_bone = sources[0]
                for source in sources[1:]:
                    if source in edit_bones:
                        # Reparent children to the kept bone
                        bone_to_remove = edit_bones[source]
                        keep_bone_obj = edit_bones[keep_bone]
                        for child in bone_to_remove.children:
                            child.parent = keep_bone_obj
                            reparented_count += 1
                        bones_to_remove.append(source)
                        if source in bone_renames:
                            del bone_renames[source]
        
        # Step 3: Reparent bones to be removed (move children to parent)
        for bone_name in bones_to_remove:
            if bone_name in edit_bones:
                bone = edit_bones[bone_name]
                parent_bone = bone.parent
                for child in bone.children:
                    child.parent = parent_bone
                    reparented_count += 1
                    logger.debug(f"Reparented {child.name} from {bone_name} to {parent_bone.name if parent_bone else 'None'}")
        
        # Step 4: Remove marked bones
        for bone_name in bones_to_remove:
            if bone_name in edit_bones:
                edit_bones.remove(edit_bones[bone_name])
                removed_count += 1
                logger.info(f"Removed bone: {bone_name}")
        
        # Step 5: Rename bones
        for old_name, new_name in bone_renames.items():
            if old_name in edit_bones:
                bone = edit_bones[old_name]
                try:
                    bone.name = new_name
                    renamed_count += 1
                    logger.info(f"Renamed bone: {old_name} -> {new_name}")
                except Exception as e:
                    logger.error(f"Failed to rename bone {old_name}: {e}")
        
        # Step 6: Fix hierarchy to match Unity standard
        for bone in edit_bones:
            expected_parent_name = unity_bone_hierarchy.get(bone.name)
            if expected_parent_name is not None:
                # This bone should have a specific parent
                if expected_parent_name in edit_bones:
                    expected_parent = edit_bones[expected_parent_name]
                    if bone.parent != expected_parent:
                        bone.parent = expected_parent
                        reparented_count += 1
                        logger.debug(f"Fixed hierarchy: {bone.name} -> parent: {expected_parent_name}")
            elif expected_parent_name is None and unity_bone_hierarchy.get(bone.name) is not None:
                # This should be a root bone
                if bone.parent is not None:
                    bone.parent = None
                    reparented_count += 1
                    logger.debug(f"Made {bone.name} a root bone")
        
    except Exception as e:
        logger.error(f"Error during bone restructuring: {e}", exc_info=True)
        messages.append(t("MMD.restructure_failed", error=str(e)))
        return False, messages
    
    finally:
        # Restore original mode
        if current_mode != 'EDIT':
            bpy.ops.object.mode_set(mode='OBJECT')
    
    # Generate messages
    if renamed_count > 0:
        messages.append(t("MMD.bones_restructured", count=renamed_count))
    if removed_count > 0:
        messages.append(t("MMD.bones_removed", count=removed_count))
    if reparented_count > 0:
        messages.append(t("MMD.bones_reparented", count=reparented_count))
    
    logger.info(f"Bone restructuring complete: {renamed_count} renamed, {removed_count} removed, {reparented_count} reparented")
    
    return True, messages
