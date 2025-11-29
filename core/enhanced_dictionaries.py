# GPL License

from typing import Dict, List, Optional, Set, Tuple
from .dictionaries import bone_names, reverse_bone_lookup, simplify_bonename
from .logging_setup import logger

# Enhanced dictionaries for comprehensive translation support

# Shapekey/Morph name translations (Japanese to English)
shapekey_names: Dict[str, List[str]] = {
    # Basic facial expressions
    "neutral": ["ニュートラル", "中立", "通常", "普通", "デフォルト", "basis"],
    "smile": ["笑顔", "スマイル", "えがお", "笑い", "にこり", "ほほえみ", "smile", "happy"],
    "angry": ["怒り", "怒る", "アングリー", "いかり", "おこり", "むかつき", "angry", "mad"],
    "sad": ["悲しい", "かなしい", "悲哀", "サッド", "sad", "sorrow"],
    "surprised": ["驚き", "びっくり", "おどろき", "サプライズ", "surprised", "shock"],
    "disgusted": ["嫌悪", "いやがり", "きもち悪い", "disgusted"],
    "fearful": ["恐怖", "怖い", "こわい", "恐れ", "fearful", "scared"],
    "blink": ["瞬き", "まばたき", "ブリンク", "目閉じ", "blink", "eyeclose"],
    "wink_left": ["ウィンク左", "左目ウィンク", "ひだりめうぃんく", "winkleft", "wink_l"],
    "wink_right": ["ウィンク右", "右目ウィンク", "みぎめうぃんく", "winkright", "wink_r"],
    "eye_close": ["目閉じ", "目を閉じる", "めとじ", "eyeclose", "closedeyes"],
    "eye_wide": ["目見開き", "目を見開く", "びっくり目", "eyewide", "wideeyes"],
    "eye_narrow": ["細目", "目細め", "ほそめ", "eyenarrow", "narroweyes"],  
    "mouth_open": ["口開け", "口を開ける", "くちあけ", "mouthopen", "openmouth"],
    "mouth_smile": ["口角上げ", "口笑顔", "くちえがお", "mouthsmile"],
    "mouth_frown": ["口角下げ", "への字口", "くちしかめ", "mouthfrown"],
    "mouth_pout": ["すぼめ口", "とがらせ口", "mouthpout"],
    "eyebrow_up": ["眉上げ", "眉毛上げ", "まゆあげ", "eyebrowup", "raiseeyebrow"],
    "eyebrow_down": ["眉下げ", "眉寄せ", "まゆさげ", "eyebrowdown", "lowereyebrow"],
    "eyebrow_angry": ["怒り眉", "眉怒り", "まゆいかり", "angrybrow"],
    "cheek_puff": ["頬膨らまし", "ほほふくらまし", "cheekpuff"],
    "cheek_suck": ["頬すぼめ", "ほほすぼめ", "cheeksuck"],
    "joy": ["喜び", "よろこび", "ジョイ", "joy", "happiness"],
    "contempt": ["軽蔑", "けいべつ", "contempt"],
    "confusion": ["困惑", "こんわく", "confusion", "confused"],
    "concentration": ["集中", "しゅうちゅう", "concentration", "focused"],
    
    # VRC Visemes
    "viseme_sil": ["無音", "むおん", "サイレンス", "silence", "sil"],
    "viseme_aa": ["あ", "aa", "mouth_a"],
    "viseme_ih": ["い", "ih", "mouth_i"], 
    "viseme_ou": ["う", "ou", "mouth_u"],
    "viseme_e": ["え", "e", "mouth_e"],
    "viseme_oh": ["お", "oh", "mouth_o"],
    "viseme_ch": ["ち", "ch"],
    "viseme_dd": ["だ", "dd"],
    "viseme_ff": ["ふ", "ff"],
    "viseme_kk": ["か", "kk"],
    "viseme_nn": ["ん", "nn"],
    "viseme_pp": ["ぱ", "pp"],
    "viseme_rr": ["ら", "rr"],
    "viseme_ss": ["さ", "ss"],
    "viseme_th": ["た", "th"],
    
    "basis": ["基本", "きほん", "ベース", "base", "basis", "default"],
    "reset": ["リセット", "初期化", "しょきか", "reset", "clear"],
}

# Material name translations (Japanese to English)  
material_names: Dict[str, List[str]] = {
    # Basic materials
    "skin": ["肌", "はだ", "皮膚", "ひふ", "スキン", "skin", "flesh"],
    "hair": ["髪", "かみ", "毛髪", "もうはつ", "ヘア", "hair"],
    "eyes": ["目", "め", "眼", "がん", "アイ", "eye", "iris"],
    "eyebrow": ["眉", "まゆ", "眉毛", "まゆげ", "eyebrow", "brow"],
    "eyelash": ["まつ毛", "まつげ", "睫毛", "eyelash", "lash"],
    "teeth": ["歯", "は", "歯列", "しれつ", "tooth", "teeth"],
    "tongue": ["舌", "した", "tongue"],
    "nails": ["爪", "つめ", "nail", "nails"],
    "shirt": ["シャツ", "上着", "うわぎ", "shirt", "top"],
    "pants": ["パンツ", "ズボン", "下着", "したぎ", "pants", "trousers"],
    "skirt": ["スカート", "skirt"],
    "dress": ["ドレス", "ワンピース", "dress"],
    "shoes": ["靴", "くつ", "シューズ", "shoe", "shoes"],
    "socks": ["靴下", "くつした", "ソックス", "sock", "socks"],
    "gloves": ["手袋", "てぶくろ", "グローブ", "glove", "gloves"],
    "hat": ["帽子", "ぼうし", "ハット", "hat", "cap"],
    "jacket": ["ジャケット", "上着", "うわぎ", "jacket", "coat"],
    "underwear": ["下着", "したぎ", "パンティー", "underwear", "panties"],
    "bra": ["ブラ", "ブラジャー", "胸当て", "bra", "brassiere"],
    "glasses": ["眼鏡", "めがね", "メガネ", "glasses", "spectacles"],
    "earring": ["イヤリング", "耳飾り", "みみかざり", "earring"],
    "necklace": ["ネックレス", "首飾り", "くびかざり", "necklace"],
    "bracelet": ["ブレスレット", "腕輪", "うでわ", "bracelet"],
    "ring": ["指輪", "ゆびわ", "リング", "ring"],
    "watch": ["時計", "とけい", "ウォッチ", "watch"],
    "bag": ["鞄", "かばん", "バッグ", "bag", "purse"],
    "belt": ["ベルト", "帯", "おび", "belt"],
    "transparent": ["透明", "とうめい", "クリア", "transparent", "clear"],
    "metal": ["金属", "きんぞく", "メタル", "metal"],
    "fabric": ["布", "ぬの", "生地", "きじ", "fabric", "cloth"],
    "leather": ["革", "かわ", "皮", "ひ", "レザー", "leather"],
    "plastic": ["プラスチック", "プラ", "plastic"],
    "glass": ["ガラス", "硝子", "glass"],
    "rubber": ["ゴム", "ラバー", "rubber"],
    "wood": ["木", "き", "木材", "もくざい", "wood", "wooden"],
    "diffuse": ["ディフューズ", "基本色", "きほんしょく", "diffuse", "albedo"],
    "normal": ["ノーマル", "法線", "ほうせん", "normal", "bump"],
    "specular": ["スペキュラー", "反射", "はんしゃ", "specular", "reflection"],
    "emission": ["発光", "はっこう", "エミッション", "emission", "glow"],
    "roughness": ["粗さ", "あらさ", "ラフネス", "roughness"],
    "metallic": ["メタリック", "金属性", "きんぞくせい", "metallic"],
    "subsurface": ["表面下散乱", "サブサーフェス", "subsurface", "sss"],
    
    # Common naming patterns
    "main": ["メイン", "主要", "しゅよう", "main", "primary"],
    "sub": ["サブ", "副", "ふく", "sub", "secondary"],
    "detail": ["詳細", "しょうさい", "ディテール", "detail"],
    "shadow": ["影", "かげ", "シャドウ", "shadow"],
    "highlight": ["ハイライト", "強調", "きょうちょう", "highlight"],
}

# Object name translations (Japanese to English)
object_names: Dict[str, List[str]] = {

    "body": ["体", "からだ", "身体", "しんたい", "ボディ", "body", "torso"],
    "head": ["頭", "あたま", "ヘッド", "head"],
    "face": ["顔", "かお", "フェイス", "face"],
    "neck": ["首", "くび", "ネック", "neck"],
    "chest": ["胸", "むね", "チェスト", "chest", "breast"],
    "back": ["背中", "せなか", "バック", "back"],
    "waist": ["腰", "こし", "ウエスト", "waist"],
    "hip": ["腰", "こし", "ヒップ", "hip"],
    "arm": ["腕", "うで", "アーム", "arm"],
    "hand": ["手", "て", "ハンド", "hand"],
    "finger": ["指", "ゆび", "フィンガー", "finger"],
    "leg": ["足", "あし", "脚", "レッグ", "leg"],
    "foot": ["足", "あし", "フット", "foot"],
    "toe": ["つま先", "つまさき", "トゥ", "toe"],
    "clothing": ["服", "ふく", "衣服", "いふく", "クロージング", "clothing", "clothes"],
    "outfit": ["服装", "ふくそう", "アウトフィット", "outfit"],
    "accessory": ["アクセサリー", "装身具", "そうしんぐ", "accessory"],
    "decoration": ["装飾", "そうしょく", "デコレーション", "decoration"],
    "hair_front": ["前髪", "まえがみ", "フロント髪", "hairfront"],
    "hair_back": ["後ろ髪", "うしろがみ", "バック髪", "hairback"],
    "hair_side": ["横髪", "よこがみ", "サイド髪", "hairside"],
    "ponytail": ["ポニーテール", "一つ結び", "ひとつむすび", "ponytail"],
    "twintail": ["ツインテール", "二つ結び", "ふたつむすび", "twintail"],
    "ahoge": ["あほ毛", "アホ毛", "はね毛", "ahoge", "antenna"],
    "eyeball": ["眼球", "がんきゅう", "目玉", "めだま", "eyeball"],
    "pupil": ["瞳", "ひとみ", "瞳孔", "どうこう", "pupil"],
    "iris": ["虹彩", "こうさい", "アイリス", "iris"],
    "eyelid": ["まぶた", "眼瞼", "がんけん", "eyelid"],
    "nose": ["鼻", "はな", "ノーズ", "nose"],
    "mouth": ["口", "くち", "マウス", "mouth"],
    "lip": ["唇", "くちびる", "リップ", "lip"],
    "ear": ["耳", "みみ", "イヤー", "ear"],
    
    # Common object suffixes
    "left": ["左", "ひだり", "レフト", "left", "l"],
    "right": ["右", "みぎ", "ライト", "right", "r"],
    "upper": ["上", "うえ", "アッパー", "upper", "top"],
    "lower": ["下", "した", "ロワー", "lower", "bottom"],
    "inner": ["内", "うち", "インナー", "inner", "inside"],
    "outer": ["外", "そと", "アウター", "outer", "outside"],
    "front": ["前", "まえ", "フロント", "front"],
    "back": ["後ろ", "うしろ", "バック", "back", "rear"],
}

# Physics object names (for MMD rigid bodies and joints)
physics_names: Dict[str, List[str]] = {
    # Rigid body types
    "rigidbody": ["剛体", "ごうたい", "リジッドボディ", "rigidbody", "rigid"],
    "joint": ["ジョイント", "関節", "かんせつ", "joint", "constraint"],
    "collision": ["当たり判定", "あたりはんてい", "コリジョン", "collision"],
    "hair_physics": ["髪物理", "かみぶつり", "ヘアフィジックス", "hairphys"],
    "hair_root": ["髪根元", "かみねもと", "ヘアルート", "hairroot"],
    "hair_tip": ["髪先", "かみさき", "ヘアティップ", "hairtip"],  
    "cloth_physics": ["布物理", "ぬのぶつり", "クロスフィジックス", "clothphys"],
    "skirt_physics": ["スカート物理", "スカートフィジックス", "skirtphys"],
    "breast_physics": ["胸物理", "むねぶつり", "ブレストフィジックス", "breastphys"],
    "breast_root": ["胸根元", "むねねもと", "ブレストルート", "breastroot"],
    "breast_tip": ["胸先", "むねさき", "ブレストティップ", "breasttip"],
}

# MMD bone name patterns (for detection)
mmd_bone_patterns: List[str] = [
    # Japanese bone names
    '全ての親', 'センター', '上半身', '下半身', '首', '頭',
    '右腕', '左腕', '右ひじ', '左ひじ', '右手首', '左手首',
    '右足', '左足', '右ひざ', '左ひざ', '右足首', '左足首',
    '両目', '左目', '右目', '右肩', '左肩',
    # English bone names (common in MMD exports)
    'center', 'groove', 'waist', 'upperbody', 'upperbody2', 'lowerbody',
    'neck', 'head',
    'shoulder_r', 'shoulder_l', 'arm_r', 'arm_l',
    'elbow_r', 'elbow_l', 'wrist_r', 'wrist_l',
    'leg_r', 'leg_l', 'knee_r', 'knee_l',
    'ankle_r', 'ankle_l', 'toe_r', 'toe_l',
    # Mixed/Romanized patterns
    '센터', 'グルーブ', 'ウエスト',
    # Common MMD suffixes
    '_r', '_l', '.r', '.l'
]

# MMD to Unity bone mapping
# Maps MMD bone names (after English translation) to Unity humanoid bone names
mmd_to_unity_bone_map: Dict[str, Optional[str]] = {
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
unity_bone_hierarchy: Dict[str, Optional[str]] = {
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

# Create reverse lookup dictionaries
reverse_shapekey_lookup: Dict[str, str] = {}
reverse_material_lookup: Dict[str, str] = {}
reverse_object_lookup: Dict[str, str] = {}
reverse_physics_lookup: Dict[str, str] = {}

def _build_reverse_lookups():
    """Build reverse lookup dictionaries for fast translation"""
    global reverse_shapekey_lookup, reverse_material_lookup, reverse_object_lookup, reverse_physics_lookup
    
    for standard_name, variations in shapekey_names.items():
        for variation in variations:
            simplified = simplify_bonename(variation)
            reverse_shapekey_lookup[simplified] = standard_name
    
    for standard_name, variations in material_names.items():
        for variation in variations:
            simplified = simplify_bonename(variation)
            reverse_material_lookup[simplified] = standard_name
    
    for standard_name, variations in object_names.items():
        for variation in variations:
            simplified = simplify_bonename(variation)
            reverse_object_lookup[simplified] = standard_name
    
    for standard_name, variations in physics_names.items():
        for variation in variations:
            simplified = simplify_bonename(variation)
            reverse_physics_lookup[simplified] = standard_name

_build_reverse_lookups()


class EnhancedDictionaryTranslator:
    """Enhanced dictionary translator with support for bones, shapekeys, materials, and objects"""
    
    def __init__(self):
        self.translation_stats = {
            'bones': 0,
            'shapekeys': 0,
            'materials': 0,
            'objects': 0,
            'physics': 0,
            'total': 0
        }
    
    def translate_bone_name(self, name: str) -> Optional[str]:
        """Translate bone name using existing bone dictionary"""
        simplified = simplify_bonename(name)
        if simplified in reverse_bone_lookup:
            self.translation_stats['bones'] += 1
            self.translation_stats['total'] += 1
            return reverse_bone_lookup[simplified]
        return None
        
    def translate_shapekey_name(self, name: str) -> Optional[str]:
        """Translate shapekey/morph name using shapekey dictionary"""
        simplified = simplify_bonename(name)
        if simplified in reverse_shapekey_lookup:
            self.translation_stats['shapekeys'] += 1
            self.translation_stats['total'] += 1
            return reverse_shapekey_lookup[simplified]
        return None
        
    def translate_material_name(self, name: str) -> Optional[str]:
        """Translate material name using material dictionary"""
        simplified = simplify_bonename(name)
        if simplified in reverse_material_lookup:
            self.translation_stats['materials'] += 1
            self.translation_stats['total'] += 1
            return reverse_material_lookup[simplified]
        return None
        
    def translate_object_name(self, name: str) -> Optional[str]:
        """Translate object name using object dictionary"""
        simplified = simplify_bonename(name)
        if simplified in reverse_object_lookup:
            self.translation_stats['objects'] += 1
            self.translation_stats['total'] += 1
            return reverse_object_lookup[simplified]
        return None
        
    def translate_physics_name(self, name: str) -> Optional[str]:
        """Translate physics object name using physics dictionary"""
        simplified = simplify_bonename(name)
        if simplified in reverse_physics_lookup:
            self.translation_stats['physics'] += 1
            self.translation_stats['total'] += 1
            return reverse_physics_lookup[simplified]
        return None
    
    def translate_name(self, name: str, category: str = "auto") -> Tuple[Optional[str], str]:
        """
        Translate name with automatic category detection or specified category
        Returns (translated_name, detected_category)
        """
        if not name or not name.strip():
            return None, "none"
        
        if category == "bones":
            result = self.translate_bone_name(name)
            return (result, "bones") if result else (None, "unknown")
        elif category == "shapekeys":
            result = self.translate_shapekey_name(name)
            return (result, "shapekeys") if result else (None, "unknown")
        elif category == "materials":
            result = self.translate_material_name(name)
            return (result, "materials") if result else (None, "unknown")
        elif category == "objects":
            result = self.translate_object_name(name)
            return (result, "objects") if result else (None, "unknown")
        elif category == "physics":
            result = self.translate_physics_name(name)
            return (result, "physics") if result else (None, "unknown")
        elif category == "auto":
            # Try all categories in order of likelihood
            for cat_name, translate_func in [
                ("bones", self.translate_bone_name),
                ("shapekeys", self.translate_shapekey_name),
                ("materials", self.translate_material_name),
                ("objects", self.translate_object_name),
                ("physics", self.translate_physics_name)
            ]:
                result = translate_func(name)
                if result:
                    return result, cat_name
            return None, "unknown"
        else:
            return None, "invalid_category"
    
    def get_statistics(self) -> Dict[str, int]:
        """Get translation statistics"""
        return self.translation_stats.copy()
    
    def reset_statistics(self) -> None:
        """Reset translation statistics"""
        for key in self.translation_stats:
            self.translation_stats[key] = 0


# Global enhanced dictionary translator instance
_enhanced_translator: Optional[EnhancedDictionaryTranslator] = None


def get_enhanced_translator() -> EnhancedDictionaryTranslator:
    """Get the global enhanced dictionary translator"""
    global _enhanced_translator
    if _enhanced_translator is None:
        _enhanced_translator = EnhancedDictionaryTranslator()
    return _enhanced_translator


def get_all_dictionary_names() -> Dict[str, Dict[str, List[str]]]:
    """Get all dictionary names for reference"""
    return {
        "bones": bone_names,
        "shapekeys": shapekey_names,
        "materials": material_names,
        "objects": object_names,
        "physics": physics_names
    }


def add_custom_translation(category: str, standard_name: str, variations: List[str]) -> bool:
    """Add custom translation to the dictionaries"""
    try:
        if category == "bones":
            if standard_name not in bone_names:
                bone_names[standard_name] = []
            bone_names[standard_name].extend(variations)
        elif category == "shapekeys":
            if standard_name not in shapekey_names:
                shapekey_names[standard_name] = []
            shapekey_names[standard_name].extend(variations)
        elif category == "materials":
            if standard_name not in material_names:
                material_names[standard_name] = []
            material_names[standard_name].extend(variations)
        elif category == "objects":
            if standard_name not in object_names:
                object_names[standard_name] = []
            object_names[standard_name].extend(variations)
        elif category == "physics":
            if standard_name not in physics_names:
                physics_names[standard_name] = []
            physics_names[standard_name].extend(variations)
        else:
            return False
        
        _build_reverse_lookups()
        logger.info(f"Added custom translation for {category}: {standard_name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to add custom translation: {e}")
        return False