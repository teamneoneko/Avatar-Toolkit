# GPL License

import json
import os
import time
import threading
from typing import Dict, List, Optional, Tuple, Set, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum

import bpy
from bpy.types import Object, Material, ShapeKey

from .translation_service import get_translation_manager, TranslationServiceManager
from .enhanced_dictionaries import get_enhanced_translator, EnhancedDictionaryTranslator
from .logging_setup import logger
from .addon_preferences import get_preference, save_preference
from .translations import t


class TranslationMode(Enum):
    """Translation modes for different approaches"""
    DICTIONARY_ONLY = "dictionary_only"
    API_ONLY = "api_only"
    HYBRID = "hybrid"  # Default: Dictionary first, then API fallback


@dataclass
class TranslationJob:
    """Represents a translation job for batch processing"""
    name: str
    category: str
    source_lang: str = "ja"
    target_lang: str = "en"
    object_ref: Optional[Any] = None  
    property_name: Optional[str] = None 


@dataclass
class TranslationResult:
    """Result of a translation operation"""
    original: str
    translated: str
    method: str  # "dictionary", "api", "failed"
    service: Optional[str] = None
    category: str = "unknown"
    confidence: float = 1.0


class TranslationCache:
    """Persistent translation cache with file storage"""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, str]] = {}
        self._cache_file = self._get_cache_file_path()
        self._cache_lock = threading.Lock()
        self._load_cache()
    
    def _get_cache_file_path(self) -> str:
        """Get the cache file path in user preferences directory"""
        user_path = bpy.utils.resource_path('USER')
        cache_dir = os.path.join(user_path, "config", "avatar_toolkit_prefs")
        os.makedirs(cache_dir, exist_ok=True)
        return os.path.join(cache_dir, "translation_cache.json")
    
    def _load_cache(self) -> None:
        """Load cache from file"""
        try:
            if os.path.exists(self._cache_file):
                # Try UTF-8 first, fallback to other encodings
                try:
                    with open(self._cache_file, 'r', encoding='utf-8') as f:
                        self._cache = json.load(f)
                except UnicodeDecodeError:
                    # Try with UTF-8 error handling
                    with open(self._cache_file, 'r', encoding='utf-8', errors='replace') as f:
                        self._cache = json.load(f)
                logger.debug(f"Loaded translation cache with {len(self._cache)} entries")
            else:
                self._cache = {}
        except Exception as e:
            logger.warning(f"Failed to load translation cache: {e}")
            self._cache = {}
    
    def _save_cache(self) -> None:
        """Save cache to file"""
        try:
            with open(self._cache_file, 'w', encoding='utf-8') as f:
                json.dump(self._cache, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved translation cache with {len(self._cache)} entries")
        except Exception as e:
            logger.error(f"Failed to save translation cache: {e}")
    
    def get(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        """Get cached translation"""
        cache_key = f"{source_lang}_{target_lang}"
        with self._cache_lock:
            if cache_key in self._cache and text in self._cache[cache_key]:
                return self._cache[cache_key][text]
        return None
    
    def put(self, text: str, translation: str, source_lang: str, target_lang: str) -> None:
        """Store translation in cache"""
        cache_key = f"{source_lang}_{target_lang}"
        with self._cache_lock:
            if cache_key not in self._cache:
                self._cache[cache_key] = {}
            self._cache[cache_key][text] = translation
            
        # Save cache periodically (every 10 new entries)
        if len(self._cache.get(cache_key, {})) % 10 == 0:
            self._save_cache()
    
    def clear(self) -> None:
        """Clear all cached translations"""
        with self._cache_lock:
            self._cache.clear()
        self._save_cache()
        logger.info("Translation cache cleared")
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        with self._cache_lock:
            total_entries = sum(len(lang_cache) for lang_cache in self._cache.values())
            return {
                "language_pairs": len(self._cache),
                "total_entries": total_entries
            }


class AvatarToolkitTranslationManager:
    """Main translation manager for Avatar Toolkit"""
    
    def __init__(self):
        self.service_manager: TranslationServiceManager = get_translation_manager()
        self.dictionary_translator: EnhancedDictionaryTranslator = get_enhanced_translator()
        self.cache: TranslationCache = TranslationCache()
        self.translation_mode: TranslationMode = TranslationMode(
            get_preference("translation_mode", "hybrid")
        )
        self._progress_callback: Optional[Callable[[int, int, str], None]] = None
    
    def set_translation_mode(self, mode: TranslationMode) -> None:
        """Set the translation mode"""
        self.translation_mode = mode
        save_preference("translation_mode", mode.value)
        logger.info(f"Translation mode set to: {mode.value}")
    
    def set_progress_callback(self, callback: Optional[Callable[[int, int, str], None]]) -> None:
        """Set progress callback for batch operations"""
        self._progress_callback = callback
    
    def translate_single(self, name: str, category: str = "auto", 
                        source_lang: str = "ja", target_lang: str = "en") -> TranslationResult:
        """Translate a single name with comprehensive fallback logic"""
        # Import safe_decode_text from translation_service
        from .translation_service import safe_decode_text
        
        # Ensure name is properly encoded
        try:
            name = safe_decode_text(name)
        except Exception as e:
            logger.warning(f"Failed to decode name: {e}")
        
        if not name or not name.strip():
            return TranslationResult(name, name, "skipped")
        
        original_name = name.strip()
        
        # Check cache first
        cached_result = self.cache.get(original_name, source_lang, target_lang)
        if cached_result:
            return TranslationResult(original_name, cached_result, "cache", category=category)
        
        # Dictionary translation (always try first in hybrid mode)
        if self.translation_mode in [TranslationMode.DICTIONARY_ONLY, TranslationMode.HYBRID]:
            dict_result, detected_category = self.dictionary_translator.translate_name(original_name, category)
            if dict_result:
                self.cache.put(original_name, dict_result, source_lang, target_lang)
                return TranslationResult(original_name, dict_result, "dictionary", 
                                       category=detected_category, confidence=1.0)
        
        if self.translation_mode in [TranslationMode.API_ONLY, TranslationMode.HYBRID]:
            try:
                api_result, service_name = self.service_manager.translate_with_fallback(
                    original_name, source_lang, target_lang
                )
                if api_result != original_name:  # Translation succeeded
                    self.cache.put(original_name, api_result, source_lang, target_lang)
                    return TranslationResult(original_name, api_result, "api", 
                                           service=service_name, category=category, confidence=0.8)
            except Exception as e:
                logger.warning(f"API translation failed for '{original_name}': {e}")
        
        # No translation available
        return TranslationResult(original_name, original_name, "failed", category=category)
    
    def translate_batch(self, jobs: List[TranslationJob], 
                       apply_results: bool = True) -> List[TranslationResult]:
        """Translate multiple items in batch with progress reporting and interruption handling"""
        results = []
        total_jobs = len(jobs)
        
        logger.info(f"Starting batch translation of {total_jobs} items")
        
        # Group jobs by category for more efficient processing
        jobs_by_category: Dict[str, List[TranslationJob]] = {}
        for job in jobs:
            if job.category not in jobs_by_category:
                jobs_by_category[job.category] = []
            jobs_by_category[job.category].append(job)
        
        completed = 0
        start_time = time.time()
        
        for category, category_jobs in jobs_by_category.items():
            logger.debug(f"Processing {len(category_jobs)} {category} translations")
            
            # Check if we can use optimized batch translation for API calls
            can_use_api_batch = (self.translation_mode in [TranslationMode.API_ONLY, TranslationMode.HYBRID] and 
                                 len(category_jobs) > 3)  
            
            if can_use_api_batch:
                # Try optimized batch translation with API
                batch_results = self._process_category_batch_optimized(category_jobs, completed, total_jobs, start_time)
                if batch_results:
                    # Apply results to Blender objects if requested
                    for i, (job, result) in enumerate(zip(category_jobs, batch_results)):
                        if apply_results and result.method != "failed" and job.object_ref:
                            try:
                                self._apply_translation_to_object(job, result)
                                logger.debug(f"Successfully applied translation: {job.name} -> {result.translated}")
                            except Exception as e:
                                logger.error(f"Failed to apply translation to object {job.name}: {e}")
                                result.method = "apply_failed" 
                                result.translated = job.name
                    
                    results.extend(batch_results)
                    completed += len(category_jobs)
                    
                    progress_percent = (completed / total_jobs) * 100
                    logger.info(f"Batch translation progress: {completed}/{total_jobs} ({progress_percent:.1f}%) - completed {category} batch")
                    continue
            
            # Fallback to individual processing
            for job in category_jobs:
                # Check if we should continue (for potential cancellation support)
                current_time = time.time()
                elapsed_time = current_time - start_time
                
                # Progress callback with detailed status
                if self._progress_callback:
                    avg_time_per_item = elapsed_time / max(completed, 1)
                    remaining_items = total_jobs - completed
                    estimated_remaining = avg_time_per_item * remaining_items
                    
                    status_msg = f"Translating {job.name}"
                    if completed > 0:
                        status_msg += f" (ETA: {estimated_remaining:.1f}s)"
                    
                    self._progress_callback(completed, total_jobs, status_msg)
                
                try:
                    logger.debug(f"Translating job {completed + 1}/{total_jobs}: {job.name} ({job.category})")
                    
                    result = self.translate_single(job.name, job.category, 
                                                 job.source_lang, job.target_lang)
                    
                    if apply_results and result.method != "failed" and job.object_ref:
                        try:
                            self._apply_translation_to_object(job, result)
                            logger.debug(f"Successfully applied translation: {job.name} -> {result.translated}")
                        except Exception as e:
                            logger.error(f"Failed to apply translation to object {job.name}: {e}")
                            result.method = "apply_failed" 
                            result.translated = job.name 
                    
                    results.append(result)
                    
                except Exception as e:
                    logger.error(f"Translation failed for job {job.name}: {e}")
                    # Create a failed result
                    failed_result = TranslationResult(
                        original=job.name,
                        translated=job.name,
                        method="failed",
                        category=job.category
                    )
                    results.append(failed_result)
                
                completed += 1
                
                # Log progress periodically
                if completed % 10 == 0 or completed == total_jobs:
                    progress_percent = (completed / total_jobs) * 100
                    logger.info(f"Batch translation progress: {completed}/{total_jobs} ({progress_percent:.1f}%)")
        
        if self._progress_callback:
            total_time = time.time() - start_time
            self._progress_callback(total_jobs, total_jobs, f"Translation complete ({total_time:.1f}s)")
        
        successful = sum(1 for r in results if r.method not in ["failed", "skipped", "apply_failed"])
        failed = sum(1 for r in results if r.method in ["failed", "apply_failed"])
        skipped = sum(1 for r in results if r.method == "skipped")
        
        dictionary_count = sum(1 for r in results if r.method == "dictionary")
        api_count = sum(1 for r in results if r.method == "api")
        cache_count = sum(1 for r in results if r.method == "cache")
        
        logger.info(f"Batch translation complete: {successful}/{total_jobs} successful, {failed} failed, {skipped} skipped")
        logger.info(f"Translation methods used: Dictionary: {dictionary_count}, API: {api_count}, Cache: {cache_count}")
        
        return results
    
    def _process_category_batch_optimized(self, category_jobs: List[TranslationJob], 
                                        completed: int, total_jobs: int, start_time: float) -> Optional[List[TranslationResult]]:
        """Process a batch of jobs from the same category using optimized API batch translation"""
        from .translation_service import safe_decode_text
        
        if not category_jobs:
            return []
        
        logger.info(f"Starting optimized batch translation for {len(category_jobs)} {category_jobs[0].category} items")
        
        api_batch_jobs = []
        api_batch_texts = []
        results = [None] * len(category_jobs)
        
        # First pass: try dictionary translations and collect API candidates
        for i, job in enumerate(category_jobs):
            if not job.name or not job.name.strip():
                results[i] = TranslationResult(job.name, job.name, "skipped", category=job.category)
                continue
            
            # Ensure name is properly encoded
            try:
                original_name = safe_decode_text(job.name.strip())
            except Exception as e:
                logger.warning(f"Failed to decode job name: {e}")
                original_name = job.name.strip()
                continue
            
            original_name = job.name.strip()
            
            # Check cache first
            cached_result = self.cache.get(original_name, job.source_lang, job.target_lang)
            if cached_result:
                results[i] = TranslationResult(original_name, cached_result, "cache", category=job.category)
                continue
            
            # Try dictionary translation first (if in hybrid mode)
            if self.translation_mode == TranslationMode.HYBRID:
                dict_result, detected_category = self.dictionary_translator.translate_name(original_name, job.category)
                if dict_result:
                    self.cache.put(original_name, dict_result, job.source_lang, job.target_lang)
                    results[i] = TranslationResult(original_name, dict_result, "dictionary", 
                                                 category=detected_category, confidence=1.0)
                    continue
            
            # Add to API batch candidates
            api_batch_jobs.append((i, job))
            api_batch_texts.append(original_name)
        
        # Process API batch if we have candidates
        if api_batch_texts:
            logger.info(f"Sending {len(api_batch_texts)} items to API batch translation")
            
            if self._progress_callback:
                elapsed_time = time.time() - start_time
                avg_time_per_item = elapsed_time / max(completed, 1) if completed > 0 else 1.0
                remaining_items = total_jobs - completed
                estimated_remaining = avg_time_per_item * remaining_items
                
                status_msg = f"Batch translating {len(api_batch_texts)} {category_jobs[0].category} items"
                if completed > 0:
                    status_msg += f" (ETA: {estimated_remaining:.1f}s)"
                
                self._progress_callback(completed, total_jobs, status_msg)
            
            try:
                # Use the service manager's optimized batch translation
                if len(set(job.source_lang for _, job in api_batch_jobs)) == 1 and len(set(job.target_lang for _, job in api_batch_jobs)) == 1:
                    source_lang = api_batch_jobs[0][1].source_lang
                    target_lang = api_batch_jobs[0][1].target_lang
                    
                    batch_results = self.service_manager.batch_translate_with_fallback(
                        api_batch_texts, source_lang, target_lang
                    )
                    
                    for j, (result_idx, job) in enumerate(api_batch_jobs):
                        if j < len(batch_results):
                            translated_text, service_name = batch_results[j]
                            
                            # Cache successful translations
                            if translated_text != job.name:
                                self.cache.put(job.name.strip(), translated_text, job.source_lang, job.target_lang)
                            
                            results[result_idx] = TranslationResult(
                                original=job.name.strip(),
                                translated=translated_text,
                                method="api" if translated_text != job.name else "failed",
                                service=service_name,
                                category=job.category,
                                confidence=0.8
                            )
                        else:
                            # Fallback for missing results
                            results[result_idx] = TranslationResult(job.name, job.name, "failed", category=job.category)
                else:
                    # Mixed language pairs - fallback to individual translations
                    logger.info("Mixed language pairs detected, falling back to individual API translations")
                    for result_idx, job in api_batch_jobs:
                        try:
                            result = self.translate_single(job.name, job.category, job.source_lang, job.target_lang)
                            results[result_idx] = result
                        except Exception as e:
                            logger.error(f"Individual API translation failed for {job.name}: {e}")
                            results[result_idx] = TranslationResult(job.name, job.name, "failed", category=job.category)
                            
            except Exception as e:
                logger.error(f"Batch API translation failed: {e}")
                # Fallback to individual translations
                for result_idx, job in api_batch_jobs:
                    try:
                        result = self.translate_single(job.name, job.category, job.source_lang, job.target_lang)
                        results[result_idx] = result
                    except Exception as individual_e:
                        logger.error(f"Individual fallback translation failed for {job.name}: {individual_e}")
                        results[result_idx] = TranslationResult(job.name, job.name, "failed", category=job.category)
        
        for i, result in enumerate(results):
            if result is None:
                results[i] = TranslationResult(category_jobs[i].name, category_jobs[i].name, "failed", category=category_jobs[i].category)
        
        successful_batch = sum(1 for r in results if r.method not in ["failed", "skipped"])
        logger.info(f"Optimized batch complete: {successful_batch}/{len(category_jobs)} successful")
        
        return results
    
    def _apply_translation_to_object(self, job: TranslationJob, result: TranslationResult) -> None:
        """Apply translation result to a Blender object"""
        if not job.object_ref or not job.property_name:
            return
        
        try:
            setattr(job.object_ref, job.property_name, result.translated)
            logger.debug(f"Applied translation: {job.object_ref.name}.{job.property_name} = '{result.translated}'")
        except Exception as e:
            logger.error(f"Failed to set property {job.property_name}: {e}")
            raise
    
    def translate_armature_bones(self, armature: Object, apply_results: bool = True) -> List[TranslationResult]:
        """Translate all bone names in an armature"""
        from .translation_service import safe_decode_text
        
        if not armature or armature.type != 'ARMATURE':
            return []
        
        jobs = []
        for bone in armature.data.bones:
            try:
                bone_name = safe_decode_text(bone.name)
            except Exception as e:
                logger.warning(f"Failed to decode bone name, using as-is: {e}")
                bone_name = bone.name
            
            jobs.append(TranslationJob(
                name=bone_name,
                category="bones",
                object_ref=bone,
                property_name="name"
            ))
        
        return self.translate_batch(jobs, apply_results)
    
    def translate_object_shapekeys(self, mesh_obj: Object, apply_results: bool = True) -> List[TranslationResult]:
        """Translate all shape key names in a mesh object"""
        from .translation_service import safe_decode_text
        
        if not mesh_obj or mesh_obj.type != 'MESH' or not mesh_obj.data.shape_keys:
            return []
        
        jobs = []
        for shape_key in mesh_obj.data.shape_keys.key_blocks:
            try:
                sk_name = safe_decode_text(shape_key.name)
            except Exception as e:
                logger.warning(f"Failed to decode shape key name, using as-is: {e}")
                sk_name = shape_key.name
            
            jobs.append(TranslationJob(
                name=sk_name,
                category="shapekeys",
                object_ref=shape_key,
                property_name="name"
            ))
        
        return self.translate_batch(jobs, apply_results)
    
    def translate_scene_materials(self, apply_results: bool = True) -> List[TranslationResult]:
        """Translate all material names in the scene"""
        from .translation_service import safe_decode_text
        
        jobs = []
        processed_materials: Set[str] = set()
        
        for obj in bpy.data.objects:
            if obj.type == 'MESH' and obj.data.materials:
                for material in obj.data.materials:
                    if material and material.name not in processed_materials:
                        try:
                            mat_name = safe_decode_text(material.name)
                        except Exception as e:
                            logger.warning(f"Failed to decode material name, using as-is: {e}")
                            mat_name = material.name
                        
                        jobs.append(TranslationJob(
                            name=mat_name,
                            category="materials",
                            object_ref=material,
                            property_name="name"
                        ))
                        processed_materials.add(material.name)
        
        return self.translate_batch(jobs, apply_results)
    
    def translate_scene_objects(self, object_types: Optional[Set[str]] = None, 
                               apply_results: bool = True) -> List[TranslationResult]:
        """Translate all object names in the scene"""
        from .translation_service import safe_decode_text
        
        if object_types is None:
            object_types = {'MESH', 'ARMATURE', 'EMPTY'}
        
        jobs = []
        for obj in bpy.data.objects:
            if obj.type in object_types:
                try:
                    obj_name = safe_decode_text(obj.name)
                except Exception as e:
                    logger.warning(f"Failed to decode object name, using as-is: {e}")
                    obj_name = obj.name
                
                jobs.append(TranslationJob(
                    name=obj_name,
                    category="objects",
                    object_ref=obj,
                    property_name="name"
                ))
        
        return self.translate_batch(jobs, apply_results)
    
    def get_translation_stats(self) -> Dict[str, Any]:
        """Get comprehensive translation statistics"""
        dict_stats = self.dictionary_translator.get_statistics()
        cache_stats = self.cache.get_stats()
        available_services = self.service_manager.get_available_services()
        
        return {
            "dictionary_translations": dict_stats,
            "cache_stats": cache_stats,
            "available_services": available_services,
            "current_mode": self.translation_mode.value,
            "primary_service": get_preference("translation_service", "microsoft")
        }
    
    def clear_all_caches(self) -> None:
        """Clear all translation caches"""
        self.cache.clear()
        for service_id, service in self.service_manager._services.items():
            service.clear_cache()
        logger.info("All translation caches cleared")


_translation_manager: Optional[AvatarToolkitTranslationManager] = None


def get_avatar_translation_manager() -> AvatarToolkitTranslationManager:
    """Get the global Avatar Toolkit translation manager"""
    global _translation_manager
    if _translation_manager is None:
        _translation_manager = AvatarToolkitTranslationManager()
    return _translation_manager


def translate_name_simple(name: str, category: str = "auto") -> str:
    """Simple translation function for quick use"""
    manager = get_avatar_translation_manager()
    result = manager.translate_single(name, category)
    return result.translated


def is_translation_service_available(service_name: str) -> bool:
    """Check if a specific translation service is available"""
    manager = get_avatar_translation_manager()
    available_services = manager.service_manager.get_available_services()
    return any(service_id == service_name for service_id, _ in available_services)


def get_available_translation_services() -> List[Tuple[str, str]]:
    """Get list of available translation services"""
    manager = get_avatar_translation_manager()
    return manager.service_manager.get_available_services()


def get_batch_translation_info() -> Dict[str, Dict[str, Any]]:
    """Get information about batch translation capabilities of available services"""
    manager = get_avatar_translation_manager()
    batch_info = {}
    
    for service_id, service_name in manager.service_manager.get_available_services():
        service = manager.service_manager.get_service(service_id)
        if service:
            batch_info[service_id] = {
                'name': service_name,
                'supports_batch': service.supports_batch_translation(),
                'batch_type': 'native' if service_id == 'deepl' else 'concurrent' if service_id in ['libretranslate', 'mymemory'] else 'individual'
            }
    
    return batch_info


def configure_translation_service(service_id: str, **config) -> bool:
    """Configure a translation service with the provided settings (now with batch support)"""
    try:
        success = False
        if service_id == "deepl":
            from .translation_service import configure_deepl_translator
            success = configure_deepl_translator(
                config.get("api_key", ""),
                config.get("use_free_api", True)
            )
            if success:
                logger.info("DeepL configured with native batch translation support (up to 50 texts per request)")
        elif service_id == "libretranslate":
            from .translation_service import configure_libretranslate_server
            success = configure_libretranslate_server(
                config.get("server_url", "https://libretranslate.com"),
                config.get("api_key", None)
            )
            if success:
                logger.info("LibreTranslate configured with concurrent batch processing (3x faster)")
        elif service_id == "microsoft":
            from .translation_service import configure_microsoft_translator
            success = configure_microsoft_translator(
                config.get("api_key", ""),
                config.get("region", "global")
            )
        
        else:
            logger.error(f"Unknown translation service: {service_id}")
            success = False
        
        return success
    except Exception as e:
        logger.error(f"Failed to configure translation service {service_id}: {e}")
        return False