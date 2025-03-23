import bpy
from typing import Tuple, List, Dict, Set, Optional
from bpy.types import Object, Bone
from ..core.translations import t
from ..core.dictionaries import (
    standard_bones,
    bone_hierarchy,
    finger_hierarchy,
    acceptable_bone_hierarchy,
    acceptable_bone_names
)

def validate_armature(armature: Object) -> Tuple[bool, List[str], bool]:
    """
    Validates armature and returns (is_valid, messages, is_acceptable_standard)
    """
    validation_mode = bpy.context.scene.avatar_toolkit.validation_mode
    messages: List[str] = []
    hierarchy_messages: List[str] = []
    non_standard_messages: List[str] = []
    
    if validation_mode == 'NONE':
        return True, [], False
        
    if not armature or armature.type != 'ARMATURE' or not armature.data.bones:
        return False, [t("Armature.validation.basic_check_failed")], False
        
    found_bones: Dict[str, Bone] = {bone.name: bone for bone in armature.data.bones}
    is_acceptable = check_acceptable_standards(found_bones)
    
    # List all bones in armature
    bone_list = "\n".join([f"- {bone}" for bone in found_bones.keys()])
    messages.append(t("Armature.validation.found_bones", bones=bone_list))
    
    # Basic validation for both STRICT and LIMITED modes
    # Check for missing required bones
    essential_bones = {standard_bones[key] for key in ['hips', 'spine', 'chest', 'neck', 'head']}
    missing_bones = [bone for bone in essential_bones if bone not in found_bones]
    
    if missing_bones:
        missing_list = "\n".join([f"- {bone}" for bone in missing_bones])
        hierarchy_messages.append(t("Armature.validation.missing_bones", bones=missing_list))

    if validation_mode == 'STRICT':
        # Validate bone hierarchy
        for parent, child in bone_hierarchy:
            if parent in found_bones and child in found_bones:
                if not validate_bone_hierarchy(found_bones, parent, child):
                    hierarchy_messages.append(t("Armature.validation.invalid_hierarchy", 
                                    parent=parent, child=child))
        
        # Validate symmetry
        symmetry_pairs = [('arm', 'L', 'R'), ('leg', 'L', 'R')]
        for base, left, right in symmetry_pairs:
            if not validate_symmetry(found_bones, base, left, right):
                hierarchy_messages.append(t("Armature.validation.asymmetric_bones", bone=base))
                
        if (not validate_symmetry(found_bones, 'hand', 'L', 'R') and
            not validate_symmetry(found_bones, 'wrist', 'L', 'R')):
            hierarchy_messages.append(t("Armature.validation.asymmetric_hand_wrist"))
            
        # Validate finger hierarchies
        for side in ['left', 'right']:
            for finger_chain in finger_hierarchy[side]:
                if all(bone in found_bones for bone in finger_chain):
                    if not validate_finger_chain(found_bones, finger_chain):
                        hierarchy_messages.append(t("Armature.validation.invalid_finger", finger=finger_chain[0]))
        
        # Non-standard bones check
        non_standard_bones = []
        required_patterns = [
            'Hips', 'Spine', 'Chest', 'Neck', 'Head',
            'Upper', 'Lower', 'Hand', 'Foot', 'Toe',
            'Thumb', 'Index', 'Middle', 'Ring', 'Pinky',
            'Eye'
        ]
        
        for bone_name in found_bones:
            if any(pattern in bone_name for pattern in required_patterns):
                is_standard = bone_name in standard_bones.values()
                is_acceptable_bone = any(bone_name in names for names in acceptable_bone_names.values())
                if not (is_standard or is_acceptable_bone):
                    non_standard_bones.append(bone_name)
        
        if non_standard_bones:
            non_standard_list = "\n".join([f"- {bone}" for bone in non_standard_bones])
            non_standard_messages.append(t("Armature.validation.non_standard_bones", bones=non_standard_list))
    
    # Combine messages in correct order
    messages.extend(non_standard_messages)
    messages.extend(hierarchy_messages)
    
    is_valid = len(non_standard_messages) == 0 and len(hierarchy_messages) == 0
    
    if not is_valid and is_acceptable:
        if non_standard_bones:
            return False, messages, False
        
        messages = [
            t("Armature.validation.acceptable_standard.success"),
            t("Armature.validation.acceptable_standard.note"),
            t("Armature.validation.acceptable_standard.option")
        ]
        return True, messages, True
        
    return is_valid, messages, False

def validate_bone_hierarchy(bones: Dict[str, Bone], parent_name: str, child_name: str) -> bool:
    """Validate if there is a valid parent-child relationship between bones"""
    if parent_name not in bones or child_name not in bones:
        return False
    return bones[child_name].parent == bones[parent_name]

def validate_symmetry(bones: Dict[str, Bone], base: str, left: str, right: str) -> bool:
    """Validate if matching left and right bones exist for a given base bone name"""
    # Extract left and right bone names from both hierarchies
    left_bone_names = set()
    right_bone_names = set()
    
    # Add standard bones
    for key, value in standard_bones.items():
        if base in key.lower():
            if '_l' in key.lower():
                left_bone_names.add(value)
            elif '_r' in key.lower():
                right_bone_names.add(value)
                
    # Add acceptable bones
    for key, names in acceptable_bone_names.items():
        if base in key.lower():
            if '_l' in key.lower():
                left_bone_names.update(names)
            elif '_r' in key.lower():
                right_bone_names.update(names)
    
    # Check if at least one pair exists and matches
    left_exists = any(name in bones for name in left_bone_names)
    right_exists = any(name in bones for name in right_bone_names)
    
    return left_exists == right_exists

def validate_finger_chain(bones: Dict[str, Bone], chain: Tuple[str, ...]) -> bool:
    """Validate if a finger bone chain has correct hierarchy"""
    for i in range(len(chain) - 1):
        if not validate_bone_hierarchy(bones, chain[i], chain[i + 1]):
            return False
    return True

def check_acceptable_standards(bones: Dict[str, Bone]) -> bool:
    """Check if armature matches acceptable non-standard hierarchy"""
    # Check if bones exist in acceptable list
    for bone_category, acceptable_names in acceptable_bone_names.items():
        found = False
        for name in acceptable_names:
            if name in bones:
                found = True
                break
        if not found:
            return False
    
    # Validate acceptable hierarchy
    for parent, child in acceptable_bone_hierarchy:
        if parent in bones and child in bones:
            if not validate_bone_hierarchy(bones, parent, child):
                return False
                
    return True
