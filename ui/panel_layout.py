"""Panel ordering and organization guide for Avatar Toolkit UI
This module defines the standard panel order and grouping for the Avatar Toolkit.
"""

# Main Panel
MAIN_PANEL_ORDER = -1  # Always first (parent panel)
QUICK_ACCESS_ORDER = 0
OPTIMIZATION_ORDER = 1
TOOLS_ORDER = 2
CUSTOM_TOOLS_ORDER = 3
CUSTOM_AVATAR_ORDER = 4
TRANSLATION_ORDER = 5
VISEMES_ORDER = 6
EYE_TRACKING_ORDER = 7
TEXTURE_ATLAS_ORDER = 8
VRM_UNITY_ORDER = 9
MMD_ORDER = 10
SETTINGS_ORDER = 11

# Panel open/closed by default
PANELS_OPEN_BY_DEFAULT = {
    'QUICK_ACCESS': False, 
    'OPTIMIZATION': True,   
    'TOOLS': True,          
    'CUSTOM_TOOLS': True,   
    'CUSTOM_AVATAR': True,  
    'VISEMES': True,        
    'EYE_TRACKING': True,   
    'TEXTURE_ATLAS': True,  
    'VRM_UNITY': True,      
    'MMD': True,            
    'SETTINGS': True,       
    'TRANSLATION': True,   
}

def get_panel_order(panel_name: str) -> int:
    """Get the recommended bl_order value for a panel"""
    order_map = {
        'quick_access': QUICK_ACCESS_ORDER,
        'optimization': OPTIMIZATION_ORDER,
        'tools': TOOLS_ORDER,
        'custom_tools': CUSTOM_TOOLS_ORDER,
        'custom_avatar': CUSTOM_AVATAR_ORDER,
        'translation': TRANSLATION_ORDER,
        'visemes': VISEMES_ORDER,
        'eye_tracking': EYE_TRACKING_ORDER,
        'texture_atlas': TEXTURE_ATLAS_ORDER,
        'vrm_unity': VRM_UNITY_ORDER,
        'mmd': MMD_ORDER,
        'settings': SETTINGS_ORDER,
    }
    return order_map.get(panel_name.lower(), 99)

def should_open_by_default(panel_name: str) -> bool:
    """Check if a panel should be open by default"""
    return PANELS_OPEN_BY_DEFAULT.get(panel_name.upper(), True)
