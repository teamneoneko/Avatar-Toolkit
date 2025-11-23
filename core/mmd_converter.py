"""
MMD Converter - Core conversion logic for MMD models
Handles armature hierarchy and naming conventions
"""
import bpy
import re
from typing import Dict, List, Optional, Tuple, Set
from bpy.types import Object, Bone, Collection, Material, ShapeKey
from .common import get_active_armature
from .dictionaries import simplify_bonename
from .enhanced_dictionaries import mmd_bone_patterns, mmd_to_unity_bone_map, unity_bone_hierarchy
from .logging_setup import logger
from .translations import t
from .mmd.translations import jp_to_en_tuples, translateFromJp


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
        
        # Protected bone name patterns (never remove or modify these)
        protected_patterns = [
            r'.*[bB]reast.*', r'.*[bB]ust.*', r'.*[tT]its.*',  # Breast bones
            r'.*[sS]kirt.*',  # Skirt bones
            r'.*[hH]air.*',  # Hair bones
            r'.*[bB]ag.*',  # Bag/accessory bones
            r'.*[rR]ibbon.*',  # Ribbon bones
            r'.*[tT]ail.*',  # Tail bones
            r'.*[wW]ing.*',  # Wing bones
            r'.*[eE]ar.*',  # Ear bones
            r'.*[sS]leeve.*',  # Sleeve bones
            r'.*[cC]ape.*', r'.*[sS]carf.*',  # Cape/Scarf bones
            r'.*[cC]oat.*', r'.*[dD]ress.*',  # Coat/Dress bones
            r'.*[fF]inger.*', r'.*[tT]humb.*',  # Finger bones
            r'.*[aA]ccessor.*',  # Accessory bones
            r'.*[jJ]oint.*',  # Joint bones
            r'.*[cC]loth.*', r'.*[pP]hys.*',  # Cloth/Physics bones
            r'^tf_.*',  # tf_ prefixed bones (clothing/accessories)
            r'^\+.*',  # + prefixed bones (accessories)
            r'.*[tT]ooth.*',  # Tooth bones
        ]
        compiled_protected = [re.compile(pattern) for pattern in protected_patterns]
        
        # Step 1: Identify and map bones (but only rename/remove bones explicitly in the map)
        for bone in edit_bones:
            bone_name = bone.name
            
            # Check if bone is protected - never touch these
            is_protected = any(pattern.match(bone_name) for pattern in compiled_protected)
            if is_protected:
                logger.debug(f"Protected bone (keeping): {bone_name}")
                continue
            
            # Only process bones that are EXPLICITLY in the map
            unity_name = mmd_to_unity_bone_map.get(bone_name)
            
            if unity_name is None:
                # Only mark for removal if explicitly mapped to None
                if bone_name in mmd_to_unity_bone_map:
                    bones_to_remove.append(bone_name)
                    logger.debug(f"Marking bone for removal: {bone_name}")
                # Otherwise, keep the bone as-is
            elif unity_name != bone_name:
                # Mark for rename only if explicitly mapped
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


def remove_mmd_ik_bones(armature: Object) -> Tuple[bool, List[str]]:
    """
    Remove MMD IK (Inverse Kinematics) and helper bones.
    
    This identifies bones that have zero vertex weights AND match IK/helper patterns.
    Similar to CATS approach: remove bones with no mesh influence that are control/helper bones.
    """
    if not armature or armature.type != 'ARMATURE':
        return False, [t("MMD.error.invalid_armature")]
    
    logger.info(f"Starting MMD IK bone removal for: {armature.name}")
    
    messages = []
    removed_count = 0
    reparented_count = 0
    
    # Store the current mode
    current_mode = bpy.context.mode
    
    try:
        # Switch to object mode to check weights
        if bpy.context.mode != 'OBJECT':
            bpy.context.view_layer.objects.active = armature
            bpy.ops.object.mode_set(mode='OBJECT')
        
        # Get all meshes using this armature
        meshes = [obj for obj in bpy.data.objects 
                 if obj.type == 'MESH' and obj.parent == armature]
        
        # Track bones with weights
        bones_with_weights = set()
        
        for mesh in meshes:
            for vertex_group in mesh.vertex_groups:
                # Check if any vertices have non-zero weights
                has_weight = False
                for vert in mesh.data.vertices:
                    try:
                        weight = vertex_group.weight(vert.index)
                        if weight > 0.001:  # Threshold for "zero" weight
                            has_weight = True
                            break
                    except:
                        continue
                
                if has_weight:
                    bones_with_weights.add(vertex_group.name)
        
        logger.info(f"Found {len(bones_with_weights)} bones with vertex weights")
        
        # Set armature as active object before switching modes
        bpy.context.view_layer.objects.active = armature
        
        # Patterns to identify IK and helper bones (Japanese and English)
        # These are control/helper bones that typically have zero weights
        ik_helper_patterns = [
            r'.*[iI][kK].*',  # Contains IK (IK, ik, etc.)
            r'.*ＩＫ.*',  # Japanese fullwidth IK
            r'.*親.*',  # Japanese "parent"
            r'.*[DCd]$',  # D/C suffix (D-bones, control bones like RightKneeD, RightAnkleD)
            r'.*[Ee][Xx]$',  # EX suffix (extra bones like RightLegTipEX)
            r'.*[Pp]arent$',  # Ends with Parent
            r'.*[Pp]$',  # P suffix (helper bones like ShoulderP)
            r'.*[Cc]$',  # C suffix (control bones like ShoulderC)
            r'^_dummy_.*',  # Dummy bones
            r'^_shadow_.*',  # Shadow bones
            r'.*ダミー.*',  # Japanese "dummy"
            r'.*補助.*',  # Japanese "auxiliary/helper"
            r'.*操作.*',  # Japanese "control/operation"
            r'.*[Tt]arget$',  # Target bones
            r'.*[Gg]roup$',  # Group bones
        ]
        
        # Compile patterns
        compiled_patterns = [re.compile(pattern) for pattern in ik_helper_patterns]
        
        # Protected bone names (main skeleton - never remove these even with zero weights)
        protected_bones = {
            "Hips", "Spine", "Chest", "UpperChest", "Upper Chest", "Neck", "Head",
            "Left shoulder", "Right shoulder", "Shoulder_L", "Shoulder_R",
            "Left arm", "Right arm", "UpperArm_L", "UpperArm_R",
            "Left elbow", "Right elbow", "LowerArm_L", "LowerArm_R",
            "Left wrist", "Right wrist", "Hand_L", "Hand_R",
            "Left leg", "Right leg", "UpperLeg_L", "UpperLeg_R",
            "Left knee", "Right knee", "LowerLeg_L", "LowerLeg_R",
            "Left ankle", "Right ankle", "Foot_L", "Foot_R",
            "Left toe", "Right toe", "Toe_L", "Toe_R",
            "Left eye", "Right eye", "Eye_L", "Eye_R"
        }
        
        # Protected bone name patterns (never remove these)
        protected_patterns = [
            r'.*[bB]reast.*',  # Breast bones
            r'.*[bB]ust.*',  # Bust bones
            r'.*[sS]kirt.*',  # Skirt bones
            r'.*[hH]air.*',  # Hair bones
            r'.*[bB]ag.*',  # Bag/accessory bones
            r'.*[rR]ibbon.*',  # Ribbon bones
            r'.*[tT]ail.*',  # Tail bones
            r'.*[wW]ing.*',  # Wing bones
            r'.*[sS]leeve.*',  # Sleeve bones
            r'.*[cC]ape.*',  # Cape bones
            r'.*[sS]carf.*',  # Scarf bones
            r'.*[cC]oat.*',  # Coat bones
            r'.*[dD]ress.*',  # Dress bones
            r'.*[fF]inger.*',  # Finger bones
            r'.*[tT]humb.*',  # Thumb bones
            r'.*[aA]ccessor.*',  # Accessory bones
            r'.*[cC]loth.*',  # Cloth bones
            r'.*[pP]hys.*',  # Physics bones
        ]
        compiled_protected = [re.compile(pattern) for pattern in protected_patterns]
        
        # Switch to pose mode to remove constraints first
        bpy.ops.object.mode_set(mode='POSE')
        pose_bones = armature.pose.bones
        
        # Identify IK/helper bones to remove (zero weight + matches pattern)
        bones_to_remove = []
        
        for bone in armature.data.bones:
            bone_name = bone.name
            
            # Check if it matches IK/helper pattern FIRST (before protection checks)
            matches_pattern = any(pattern.match(bone_name) for pattern in compiled_patterns)
            
            # Skip if bone has weights (it's actually used by the mesh)
            if bone_name in bones_with_weights:
                if matches_pattern:
                    logger.debug(f"IK pattern match but has weights (keeping): {bone_name}")
                continue
            
            # If matches IK pattern, remove regardless of other checks (except weights)
            if matches_pattern:
                bones_to_remove.append(bone_name)
                logger.debug(f"IK/helper bone identified (zero weight): {bone_name}")
                
                # Remove constraints from this bone
                if bone_name in pose_bones:
                    pose_bone = pose_bones[bone_name]
                    for constraint in list(pose_bone.constraints):
                        constraint_name = constraint.name
                        pose_bone.constraints.remove(constraint)
                        logger.debug(f"Removed constraint '{constraint_name}' from {bone_name}")
                continue
            
            # Skip if in protected set
            if bone_name in protected_bones:
                continue
            
            # Skip if matches protected pattern
            is_protected = any(pattern.match(bone_name) for pattern in compiled_protected)
            if is_protected:
                logger.debug(f"Protected bone (keeping): {bone_name}")
                continue
        
        # Remove constraints that reference bones we're about to delete
        for pose_bone in pose_bones:
            for constraint in list(pose_bone.constraints):
                if hasattr(constraint, 'target') and constraint.target:
                    if hasattr(constraint, 'subtarget') and constraint.subtarget in bones_to_remove:
                        constraint_name = constraint.name
                        pose_bone_name = pose_bone.name
                        pose_bone.constraints.remove(constraint)
                        logger.debug(f"Removed constraint '{constraint_name}' from {pose_bone_name} (referenced deleted bone)")
        
        # Switch to edit mode for bone removal
        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = armature.data.edit_bones
        
        # Reparent children before removing
        for bone_name in bones_to_remove:
            if bone_name in edit_bones:
                bone = edit_bones[bone_name]
                parent_bone = bone.parent
                for child in bone.children:
                    child.parent = parent_bone
                    reparented_count += 1
                    logger.debug(f"Reparented {child.name} from {bone_name} to {parent_bone.name if parent_bone else 'None'}")
        
        # Remove IK/helper bones
        for bone_name in bones_to_remove:
            if bone_name in edit_bones:
                edit_bones.remove(edit_bones[bone_name])
                removed_count += 1
                logger.info(f"Removed IK/helper bone: {bone_name}")
        
    except Exception as e:
        logger.error(f"Error during IK bone removal: {e}", exc_info=True)
        messages.append(t("MMD.ik_removal_failed", error=str(e)))
        return False, messages
    
    finally:
        # Restore original mode
        if current_mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
    
    # Generate messages
    if removed_count > 0:
        messages.append(t("MMD.ik_bones_removed", count=removed_count))
    else:
        messages.append(t("MMD.no_ik_bones_found"))
    
    if reparented_count > 0:
        messages.append(t("MMD.bones_reparented", count=reparented_count))
    
    logger.info(f"IK bone removal complete: {removed_count} removed, {reparented_count} reparented")
    
    return True, messages


def remove_mmd_twist_bones(armature: Object) -> Tuple[bool, List[str]]:
    """
    Remove MMD twist bones.
    
    Twist bone patterns:
    - Contains 'twist', 'Twist'
    - Ends with '_twist'
    - Contains '捩' (Japanese for twist)
    """
    if not armature or armature.type != 'ARMATURE':
        return False, [t("MMD.error.invalid_armature")]
    
    logger.info(f"Starting MMD twist bone removal for: {armature.name}")
    
    messages = []
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
        
        # Patterns to identify twist bones - be specific about twist markers
        twist_patterns = [
            r'.*_[tT]wist$',  # Ends with _twist or _Twist
            r'^[tT]wist_',  # Starts with twist_ or Twist_
            r'.*\.[tT]wist$',  # Ends with .twist or .Twist
            r'^[tT]wist\.',  # Starts with twist. or Twist.
            r'.*[tT]wist$',  # Ends with Twist (no underscore/dot required)
            r'.*捩.*',  # Contains Japanese twist character
        ]
        
        # Compile patterns
        compiled_patterns = [re.compile(pattern) for pattern in twist_patterns]
        
        # Protected bone name patterns (never remove these)
        protected_patterns = [
            r'.*[bB]reast.*',  # Breast bones
            r'.*[bB]ust.*',  # Bust bones
            r'.*[sS]kirt.*',  # Skirt bones
            r'.*[hH]air.*',  # Hair bones
            r'.*[bB]ag.*',  # Bag/accessory bones
            r'.*[rR]ibbon.*',  # Ribbon bones
            r'.*[tT]ail.*',  # Tail bones
            r'.*[wW]ing.*',  # Wing bones
            r'.*[eE]ar.*',  # Ear bones
            r'.*[sS]leeve.*',  # Sleeve bones
            r'.*[cC]ape.*',  # Cape bones
            r'.*[sS]carf.*',  # Scarf bones
            r'.*[cC]oat.*',  # Coat bones
            r'.*[dD]ress.*',  # Dress bones
        ]
        compiled_protected = [re.compile(pattern) for pattern in protected_patterns]
        
        # Identify twist bones (but exclude protected bones)
        for bone in edit_bones:
            bone_name = bone.name
            
            # Check if bone is protected
            is_protected = any(pattern.match(bone_name) for pattern in compiled_protected)
            if is_protected:
                continue
            
            # Check if it's a twist bone
            for pattern in compiled_patterns:
                if pattern.match(bone_name):
                    bones_to_remove.append(bone_name)
                    logger.debug(f"Twist bone identified: {bone_name}")
                    break
        
        # Reparent children before removing
        for bone_name in bones_to_remove:
            if bone_name in edit_bones:
                bone = edit_bones[bone_name]
                parent_bone = bone.parent
                for child in bone.children:
                    child.parent = parent_bone
                    reparented_count += 1
                    logger.debug(f"Reparented {child.name} from {bone_name} to {parent_bone.name if parent_bone else 'None'}")
        
        # Remove twist bones
        for bone_name in bones_to_remove:
            if bone_name in edit_bones:
                edit_bones.remove(edit_bones[bone_name])
                removed_count += 1
                logger.info(f"Removed twist bone: {bone_name}")
        
    except Exception as e:
        logger.error(f"Error during twist bone removal: {e}", exc_info=True)
        messages.append(t("MMD.twist_removal_failed", error=str(e)))
        return False, messages
    
    finally:
        # Restore original mode
        if current_mode != 'EDIT':
            bpy.ops.object.mode_set(mode='OBJECT')
    
    # Generate messages
    if removed_count > 0:
        messages.append(t("MMD.twist_bones_removed", count=removed_count))
    else:
        messages.append(t("MMD.no_twist_bones_found"))
    
    if reparented_count > 0:
        messages.append(t("MMD.bones_reparented", count=reparented_count))
    
    logger.info(f"Twist bone removal complete: {removed_count} removed, {reparented_count} reparented")
    
    return True, messages


def remove_mmd_zero_weight_bones(armature: Object) -> Tuple[bool, List[str]]:
    """
    Remove bones with zero or near-zero vertex weights.
    Protects main skeleton bones from removal.
    """
    if not armature or armature.type != 'ARMATURE':
        return False, [t("MMD.error.invalid_armature")]
    
    logger.info(f"Starting zero weight bone removal for: {armature.name}")
    
    messages = []
    removed_count = 0
    reparented_count = 0
    
    # Store the current mode
    current_mode = bpy.context.mode
    
    try:
        # Switch to object mode to check weights
        if bpy.context.mode != 'OBJECT':
            bpy.context.view_layer.objects.active = armature
            bpy.ops.object.mode_set(mode='OBJECT')
        
        # Get all meshes using this armature
        meshes = [obj for obj in bpy.data.objects 
                 if obj.type == 'MESH' and obj.parent == armature]
        
        # Track bones with weights
        bones_with_weights = set()
        
        for mesh in meshes:
            for vertex_group in mesh.vertex_groups:
                # Check if any vertices have non-zero weights
                has_weight = False
                for vert in mesh.data.vertices:
                    try:
                        weight = vertex_group.weight(vert.index)
                        if weight > 0.001:  # Threshold for "zero" weight
                            has_weight = True
                            break
                    except:
                        continue
                
                if has_weight:
                    bones_with_weights.add(vertex_group.name)
        
        # Switch to edit mode
        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = armature.data.edit_bones
        
        # Protected bone names (main skeleton)
        protected_bones = {
            "Hips", "Spine", "Chest", "UpperChest", "Neck", "Head",
            "Left shoulder", "Right shoulder", "Shoulder_L", "Shoulder_R",
            "Left arm", "Right arm", "UpperArm_L", "UpperArm_R",
            "Left elbow", "Right elbow", "LowerArm_L", "LowerArm_R",
            "Left wrist", "Right wrist", "Hand_L", "Hand_R",
            "Left leg", "Right leg", "UpperLeg_L", "UpperLeg_R",
            "Left knee", "Right knee", "LowerLeg_L", "LowerLeg_R",
            "Left ankle", "Right ankle", "Foot_L", "Foot_R",
            "Left toe", "Right toe", "Toe_L", "Toe_R",
            "Left eye", "Right eye", "Eye_L", "Eye_R"
        }
        
        # Protected bone name patterns (never remove these even with zero weights)
        protected_patterns = [
            r'.*[bB]reast.*',  # Breast bones
            r'.*[bB]ust.*',  # Bust bones
            r'.*[sS]kirt.*',  # Skirt bones
            r'.*[hH]air.*',  # Hair bones
            r'.*[bB]ag.*',  # Bag/accessory bones
            r'.*[rR]ibbon.*',  # Ribbon bones
            r'.*[tT]ail.*',  # Tail bones
            r'.*[wW]ing.*',  # Wing bones
            r'.*[eE]ar.*',  # Ear bones (not Eye)
            r'.*[sS]leeve.*',  # Sleeve bones
            r'.*[cC]ape.*',  # Cape bones
            r'.*[sS]carf.*',  # Scarf bones
            r'.*[cC]oat.*',  # Coat bones
            r'.*[dD]ress.*',  # Dress bones
            r'.*[fF]inger.*',  # Finger bones
            r'.*[tT]humb.*',  # Thumb bones
            r'.*[iI]ndex.*',  # Index finger bones
            r'.*[mM]iddle.*',  # Middle finger bones
            r'.*[rR]ing.*',  # Ring finger bones
            r'.*[pP]ink.*',  # Pinky bones
            r'.*[tT]oe.*',  # Toe bones
            r'.*[aA]ccessor.*',  # Accessory bones
            r'.*[jJ]oint.*',  # Joint bones
            r'.*[cC]loth.*',  # Cloth bones
            r'.*[pP]hys.*',  # Physics bones
        ]
        compiled_protected = [re.compile(pattern) for pattern in protected_patterns]
        
        # Identify zero weight bones (but exclude protected bones)
        bones_to_remove = []
        for bone in edit_bones:
            # Skip if bone has weights
            if bone.name in bones_with_weights:
                continue
            
            # Skip if in protected set
            if bone.name in protected_bones:
                continue
            
            # Skip if matches protected pattern
            is_protected = any(pattern.match(bone.name) for pattern in compiled_protected)
            if is_protected:
                logger.debug(f"Protected bone (zero weight but keeping): {bone.name}")
                continue
            
            bones_to_remove.append(bone.name)
            logger.debug(f"Zero weight bone identified: {bone.name}")
        
        # Reparent children before removing
        for bone_name in bones_to_remove:
            if bone_name in edit_bones:
                bone = edit_bones[bone_name]
                parent_bone = bone.parent
                for child in bone.children:
                    child.parent = parent_bone
                    reparented_count += 1
                    logger.debug(f"Reparented {child.name} from {bone_name} to {parent_bone.name if parent_bone else 'None'}")
        
        # Remove zero weight bones
        for bone_name in bones_to_remove:
            if bone_name in edit_bones:
                edit_bones.remove(edit_bones[bone_name])
                removed_count += 1
                logger.info(f"Removed zero weight bone: {bone_name}")
        
    except Exception as e:
        logger.error(f"Error during zero weight bone removal: {e}", exc_info=True)
        messages.append(t("MMD.zero_weight_removal_failed", error=str(e)))
        return False, messages
    
    finally:
        # Restore original mode
        if current_mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
    
    # Generate messages
    if removed_count > 0:
        messages.append(t("MMD.zero_weight_bones_removed", count=removed_count))
    else:
        messages.append(t("MMD.no_zero_weight_bones_found"))
    
    if reparented_count > 0:
        messages.append(t("MMD.bones_reparented", count=reparented_count))
    
    logger.info(f"Zero weight bone removal complete: {removed_count} removed, {reparented_count} reparented")
    
    return True, messages
