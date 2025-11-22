# GPL License

import json
import time
import requests
import threading
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass
from urllib.parse import urlencode
import uuid

from .logging_setup import logger
from .addon_preferences import save_preference, get_preference


def safe_decode_text(text: str) -> str:
    """Safely decode text that might be in various encodings (UTF-8, Shift-JIS, etc.)"""
    if not text:
        return text
    
    # If it's already a proper string, return it
    if isinstance(text, str):
        try:
            # Test if it's valid UTF-8
            text.encode('utf-8')
            return text
        except (UnicodeDecodeError, UnicodeEncodeError):
            pass
    
    # Try common encodings for Japanese text
    encodings = ['utf-8', 'shift-jis', 'cp932', 'euc-jp', 'iso-2022-jp']
    
    for encoding in encodings:
        try:
            if isinstance(text, bytes):
                return text.decode(encoding)
            else:
                # Try to re-encode and decode
                return text.encode('latin-1', errors='ignore').decode(encoding, errors='ignore')
        except (UnicodeDecodeError, UnicodeEncodeError, AttributeError):
            continue
    
    # Fallback: replace problematic characters
    try:
        if isinstance(text, bytes):
            return text.decode('utf-8', errors='replace')
        else:
            return str(text).encode('utf-8', errors='replace').decode('utf-8')
    except:
        return str(text)


@dataclass
class TranslationRequest:
    """Represents a translation request"""
    text: str
    source_lang: str = "ja"
    target_lang: str = "en"
    category: str = "general" 


@dataclass
class TranslationResult:
    """Represents a translation result"""
    original: str
    translated: str
    service: str
    confidence: float = 1.0
    cached: bool = False


class TranslationError(Exception):
    """Custom exception for translation errors"""
    pass


class TranslationService(ABC):
    """Abstract base class for translation services"""
    
    def __init__(self, name: str):
        self.name = name
        self._cache: Dict[str, str] = {}
        self._rate_limit_lock = threading.Lock()
        self._last_request_time = 0.0
        self._request_count = 0
        self._rate_limit_per_second = 10  # Default rate limit
        
    @abstractmethod
    def translate_text(self, text: str, source_lang: str = "ja", target_lang: str = "en") -> str:
        """Translate a single text string"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the service is available"""
        pass
    
    @abstractmethod
    def get_supported_languages(self) -> List[Tuple[str, str]]:
        """Get list of supported language pairs (code, name)"""
        pass
    
    def batch_translate(self, texts: List[str], source_lang: str = "ja", target_lang: str = "en") -> List[str]:
        """Translate multiple texts with rate limiting - base implementation for services without native batch support"""
        results = []
        for text in texts:
            # Check cache first
            cache_key = f"{source_lang}_{target_lang}_{text}"
            if cache_key in self._cache:
                results.append(self._cache[cache_key])
                continue
                
            # Rate limiting
            with self._rate_limit_lock:
                current_time = time.time()
                if current_time - self._last_request_time < (1.0 / self._rate_limit_per_second):
                    time.sleep((1.0 / self._rate_limit_per_second) - (current_time - self._last_request_time))
                
                try:
                    translated = self.translate_text(text, source_lang, target_lang)
                    self._cache[cache_key] = translated
                    results.append(translated)
                    self._last_request_time = time.time()
                    
                except Exception as e:
                    logger.warning(f"Translation failed for '{text}': {e}")
                    results.append(text) 
                    
        return results
    
    def supports_batch_translation(self) -> bool:
        """Check if service supports native batch translation"""
        return False
    
    def clear_cache(self) -> None:
        """Clear the translation cache"""
        self._cache.clear()
        logger.info(f"Cleared cache for {self.name}")




class DeepLService(TranslationService):
    """DeepL translation service - requires API key"""
    
    def __init__(self, api_key: str = "", use_free_api: bool = True):
        super().__init__("DeepL" + (" (Free)" if use_free_api else " (Pro)"))
        self.api_key = api_key
        self.use_free_api = use_free_api
        self._rate_limit_per_second = 5  # DeepL allows more requests
        self._base_url = "https://api-free.deepl.com" if use_free_api else "https://api.deepl.com"
        
    def translate_text(self, text: str, source_lang: str = "ja", target_lang: str = "en") -> str:
        """Translate text using DeepL API"""
        # Ensure text is properly encoded
        text = safe_decode_text(text)
        logger.info(f"DeepL: Starting translation of '{text}' from {source_lang} to {target_lang}")
        
        if not text or not text.strip():
            logger.debug("Empty text provided, returning as-is")
            return text
            
        if not self.api_key:
            raise TranslationError("DeepL API key is required")
            
        # DeepL language codes mapping
        lang_map = {
            "ja": "JA", "en": "EN", "ko": "KO", "zh": "ZH", 
            "es": "ES", "fr": "FR", "de": "DE", "it": "IT", 
            "pt": "PT", "ru": "RU", "nl": "NL", "pl": "PL"
        }
        source_lang = lang_map.get(source_lang, source_lang.upper())
        target_lang = lang_map.get(target_lang, target_lang.upper())
        
        endpoint = f"{self._base_url}/v2/translate"
        headers = {
            "Authorization": f"DeepL-Auth-Key {self.api_key}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "text": text,
            "source_lang": source_lang,
            "target_lang": target_lang
        }
        
        try:
            logger.debug(f"Making request to DeepL API: {endpoint}")
            response = requests.post(endpoint, headers=headers, data=data, timeout=15)
            logger.debug(f"DeepL response status: {response.status_code}")
            response.raise_for_status()
            
            result = response.json()
            logger.debug(f"DeepL response: {result}")
            
            if "translations" in result and len(result["translations"]) > 0:
                translated_text = result["translations"][0]["text"]
                logger.info(f"DeepL SUCCESS: '{text}' -> '{translated_text}'")
                return translated_text
            else:
                raise TranslationError("DeepL API returned no translations")
                
        except requests.HTTPError as e:
            if e.response.status_code == 401:
                raise TranslationError("DeepL API key is invalid")
            elif e.response.status_code == 403:
                raise TranslationError("DeepL API key access denied or quota exceeded")
            elif e.response.status_code == 456:
                raise TranslationError("DeepL quota exceeded")
            else:
                logger.error(f"DeepL HTTP error: {e}")
                raise TranslationError(f"DeepL API error: {e}")
        except requests.Timeout:
            logger.error("DeepL request timed out")
            raise TranslationError("DeepL request timed out after 15 seconds")
        except requests.RequestException as e:
            logger.error(f"DeepL API request failed: {e}")
            raise TranslationError(f"DeepL API request failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in DeepL: {e}")
            raise TranslationError(f"Unexpected error: {e}")
    
    def is_available(self) -> bool:
        """Check if DeepL service is available"""
        if not self.api_key:
            return False
            
        try:
            headers = {"Authorization": f"DeepL-Auth-Key {self.api_key}"}
            response = requests.get(f"{self._base_url}/v2/usage", headers=headers, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_supported_languages(self) -> List[Tuple[str, str]]:
        """Get supported languages for DeepL"""
        return [
            ("ja", "Japanese"),
            ("en", "English"),
            ("ko", "Korean"), 
            ("zh", "Chinese"),
            ("es", "Spanish"),
            ("fr", "French"),
            ("de", "German"),
            ("it", "Italian"),
            ("pt", "Portuguese"),
            ("ru", "Russian"),
            ("nl", "Dutch"),
            ("pl", "Polish")
        ]
    
    def supports_batch_translation(self) -> bool:
        """DeepL supports native batch translation"""
        return True
    
    def batch_translate(self, texts: List[str], source_lang: str = "ja", target_lang: str = "en") -> List[str]:
        """Translate multiple texts using DeepL batch API"""
        if not texts:
            return []
        
        # Ensure all texts are properly encoded
        texts = [safe_decode_text(text) for text in texts]
        logger.info(f"DeepL: Starting batch translation of {len(texts)} texts from {source_lang} to {target_lang}")
        
        results = [None] * len(texts) 
        uncached_indices = []
        uncached_texts = []
        
        for i, text in enumerate(texts):
            if not text or not text.strip():
                results[i] = text
                continue
                
            cache_key = f"{source_lang}_{target_lang}_{text}"
            if cache_key in self._cache:
                results[i] = self._cache[cache_key]
                continue
            
            uncached_indices.append(i)
            uncached_texts.append(text)
        
        if not uncached_texts:
            logger.info(f"DeepL: All {len(texts)} texts found in cache")
            return results
        
        logger.info(f"DeepL: Translating {len(uncached_texts)} uncached texts")
        
        if not self.api_key:
            logger.error("DeepL API key is required for batch translation")
            for i, idx in enumerate(uncached_indices):
                results[idx] = texts[idx]
            return results
        
        # DeepL language codes mapping
        lang_map = {
            "ja": "JA", "en": "EN", "ko": "KO", "zh": "ZH", 
            "es": "ES", "fr": "FR", "de": "DE", "it": "IT", 
            "pt": "PT", "ru": "RU", "nl": "NL", "pl": "PL"
        }
        source_lang_code = lang_map.get(source_lang, source_lang.upper())
        target_lang_code = lang_map.get(target_lang, target_lang.upper())
        
        # Batch size limit for DeepL
        batch_size = 50
        
        for batch_start in range(0, len(uncached_texts), batch_size):
            batch_end = min(batch_start + batch_size, len(uncached_texts))
            batch_texts = uncached_texts[batch_start:batch_end]
            batch_indices = uncached_indices[batch_start:batch_end]
            
            logger.debug(f"DeepL batch {batch_start//batch_size + 1}: Processing {len(batch_texts)} texts")
            
            endpoint = f"{self._base_url}/v2/translate"
            headers = {
                "Authorization": f"DeepL-Auth-Key {self.api_key}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            # Build form data with multiple text parameters (DeepL supports multiple 'text' params)
            form_data = [
                ('source_lang', source_lang_code),
                ('target_lang', target_lang_code)
            ]
            for text in batch_texts:
                form_data.append(('text', text))
            
            try:
                logger.debug(f"Making batch request to DeepL API: {endpoint}")
                
                import requests
                response = requests.post(endpoint, headers=headers, data=form_data, timeout=30)
                logger.debug(f"DeepL batch response status: {response.status_code}")
                response.raise_for_status()
                
                result = response.json()
                logger.debug(f"DeepL batch response: {result}")
                
                if "translations" in result and len(result["translations"]) == len(batch_texts):
                    for i, translation_data in enumerate(result["translations"]):
                        original_text = batch_texts[i]
                        translated_text = translation_data["text"]
                        original_idx = batch_indices[i]
                        
                        cache_key = f"{source_lang}_{target_lang}_{original_text}"
                        self._cache[cache_key] = translated_text
                        
                        results[original_idx] = translated_text
                        logger.debug(f"DeepL batch SUCCESS: '{original_text}' -> '{translated_text}'")
                else:
                    logger.error(f"DeepL batch API returned unexpected response: {result}")
                    for i, idx in enumerate(batch_indices):
                        results[idx] = batch_texts[i]
                
                # Rate limiting between batches
                if batch_end < len(uncached_texts):
                    time.sleep(1.0 / self._rate_limit_per_second)
                    
            except Exception as e:
                logger.error(f"DeepL batch translation failed: {e}")
                for i, idx in enumerate(batch_indices):
                    results[idx] = batch_texts[i]
        
        # Ensure all results are filled
        for i, result in enumerate(results):
            if result is None:
                results[i] = texts[i]
        
        successful_translations = sum(1 for i, result in enumerate(results) if result != texts[i])
        logger.info(f"DeepL batch translation complete: {successful_translations}/{len(texts)} successfully translated")
        
        return results


class MyMemoryService(TranslationService):
    """MyMemory free translation service - no API key required"""
    
    def __init__(self):
        super().__init__("MyMemory (Free)")
        self._rate_limit_per_second = 1  # Conservative rate limiting for free service
        self._base_url = "https://api.mymemory.translated.net"
        
    def translate_text(self, text: str, source_lang: str = "ja", target_lang: str = "en") -> str:
        """Translate text using MyMemory free API"""
        # Ensure text is properly encoded
        text = safe_decode_text(text)
        logger.info(f"MyMemory: Starting translation of '{text}' from {source_lang} to {target_lang}")
        
        if not text or not text.strip():
            logger.debug("Empty text provided, returning as-is")
            return text
            
        # MyMemory uses different language codes
        lang_map = {"ja": "ja", "en": "en", "ko": "ko", "zh": "zh", "es": "es", "fr": "fr", "de": "de"}
        source_lang = lang_map.get(source_lang, source_lang)
        target_lang = lang_map.get(target_lang, target_lang)
        
        endpoint = f"{self._base_url}/get"
        params = {
            'q': text,
            'langpair': f"{source_lang}|{target_lang}",
            'de': 'neoneko@avatartoolkit.com'  # Optional email for higher quotas
        }
        
        try:
            logger.debug(f"Making request to MyMemory API: {endpoint} with params: {params}")
            response = requests.get(endpoint, params=params, timeout=15)  # Increased timeout
            logger.debug(f"MyMemory response status: {response.status_code}")
            response.raise_for_status()
            
            result = response.json()
            logger.debug(f"MyMemory response: {result}")
            
            if result.get('responseStatus') == 200 and 'responseData' in result:
                translated_text = result['responseData']['translatedText']
                matches = result.get('matches', [])
                if matches and len(matches) > 0:
                    match_quality = matches[0].get('quality', '0')
                    logger.debug(f"MyMemory translation quality: {match_quality}")
                
                logger.info(f"MyMemory SUCCESS: '{text}' -> '{translated_text}'")
                return translated_text
            else:
                error_msg = result.get('responseDetails', 'Unknown error')
                logger.error(f"MyMemory API error: {error_msg}")
                
                if 'QUOTA_EXCEEDED' in error_msg:
                    raise TranslationError(f"MyMemory daily quota (1000 requests) exceeded. Try again tomorrow or switch to another service.")
                else:
                    raise TranslationError(f"MyMemory API error: {error_msg}")
                
        except requests.Timeout as e:
            logger.error(f"MyMemory request timed out: {e}")
            raise TranslationError(f"MyMemory request timed out after 15 seconds")
        except requests.RequestException as e:
            logger.error(f"MyMemory API request failed: {e}")
            raise TranslationError(f"MyMemory API request failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in MyMemory: {e}")
            raise TranslationError(f"Unexpected error: {e}")
    
    def is_available(self) -> bool:
        """Check if MyMemory service is available"""
        try:
            response = requests.get(f"{self._base_url}/get", 
                                  params={'q': 'test', 'langpair': 'en|en'}, 
                                  timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_supported_languages(self) -> List[Tuple[str, str]]:
        """Get supported languages for MyMemory"""
        return [
            ("ja", "Japanese"),
            ("en", "English"),
            ("ko", "Korean"),
            ("zh", "Chinese"),
            ("es", "Spanish"),
            ("fr", "French"),
            ("de", "German"),
            ("it", "Italian"),
            ("pt", "Portuguese"),
            ("ru", "Russian")
        ]
    
    def supports_batch_translation(self) -> bool:
        """MyMemory optimized batch processing"""
        return True
    
    def batch_translate(self, texts: List[str], source_lang: str = "ja", target_lang: str = "en") -> List[str]:
        """Translate multiple texts using MyMemory with optimized batching and caching"""
        if not texts:
            return []
        
        # Ensure all texts are properly encoded
        texts = [safe_decode_text(text) for text in texts]
        logger.info(f"MyMemory: Starting batch translation of {len(texts)} texts from {source_lang} to {target_lang}")
        
        results = [None] * len(texts)
        uncached_indices = []
        uncached_texts = []
        
        for i, text in enumerate(texts):
            if not text or not text.strip():
                results[i] = text
                continue
                
            cache_key = f"{source_lang}_{target_lang}_{text}"
            if cache_key in self._cache:
                results[i] = self._cache[cache_key]
                continue
            
            uncached_indices.append(i)
            uncached_texts.append(text)
        
        if not uncached_texts:
            logger.info(f"MyMemory: All {len(texts)} texts found in cache")
            return results
        
        logger.info(f"MyMemory: Translating {len(uncached_texts)} uncached texts using concurrent processing")
        
        # Use concurrent processing for MyMemory to speed up translations
        import concurrent.futures
        from concurrent.futures import ThreadPoolExecutor
        import threading
        
        def translate_single_text(text_info):
            idx, text = text_info
            try:
                with self._rate_limit_lock:
                    current_time = time.time()
                    if current_time - self._last_request_time < (1.0 / self._rate_limit_per_second):
                        sleep_time = (1.0 / self._rate_limit_per_second) - (current_time - self._last_request_time)
                        time.sleep(sleep_time)
                    self._last_request_time = time.time()
                
                translated = self.translate_text(text, source_lang, target_lang)
                
                cache_key = f"{source_lang}_{target_lang}_{text}"
                self._cache[cache_key] = translated
                
                return idx, translated, None
                
            except Exception as e:
                logger.warning(f"MyMemory concurrent translation failed for '{text}': {e}")
                return idx, text, e
        
        # Use conservative concurrent processing (2 workers max for free service)
        max_workers = min(len(uncached_texts), 2)
        batch_size = 8 
        
        for batch_start in range(0, len(uncached_texts), batch_size):
            batch_end = min(batch_start + batch_size, len(uncached_texts))
            batch_texts = uncached_texts[batch_start:batch_end]
            batch_indices = uncached_indices[batch_start:batch_end]
            
            text_info_batch = [(batch_indices[i], text) for i, text in enumerate(batch_texts)]
            
            logger.debug(f"MyMemory concurrent batch {batch_start//batch_size + 1}: Processing {len(batch_texts)} texts with {max_workers} workers")
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_text = {executor.submit(translate_single_text, text_info): text_info for text_info in text_info_batch}
                
                for future in concurrent.futures.as_completed(future_to_text):
                    try:
                        original_idx, translated_text, error = future.result(timeout=25)
                        results[original_idx] = translated_text
                        
                        if error is None:
                            logger.debug(f"MyMemory concurrent SUCCESS: -> '{translated_text}'")
                        else:
                            logger.debug(f"MyMemory concurrent FAILED: {error}")
                            
                    except concurrent.futures.TimeoutError:
                        text_info = future_to_text[future]
                        original_idx, original_text = text_info
                        results[original_idx] = original_text
                        logger.warning(f"MyMemory concurrent timeout for text: '{original_text}'")
                    except Exception as e:
                        text_info = future_to_text[future]
                        original_idx, original_text = text_info
                        results[original_idx] = original_text
                        logger.error(f"MyMemory concurrent thread error for '{original_text}': {e}")
            
            # Shorter pause between batches since we're not hammering the API
            if batch_end < len(uncached_texts):
                time.sleep(0.5) 
        
        for i, result in enumerate(results):
            if result is None:
                results[i] = texts[i]
        
        successful_translations = sum(1 for i, result in enumerate(results) if result != texts[i])
        logger.info(f"MyMemory concurrent batch translation complete: {successful_translations}/{len(texts)} successfully translated")
        
        return results


class LibreTranslateService(TranslationService):
    """LibreTranslate translation service with configurable server"""
    
    def __init__(self, api_url: str = "https://libretranslate.com", api_key: str = None):
        super().__init__("LibreTranslate")
        # Ensure URL has trailing slash like official implementation
        self.api_url = api_url.rstrip('/') + '/'
        self.api_key = api_key
        self._rate_limit_per_second = 2  # Conservative rate limiting
        self._is_paid_service = "libretranslate.com" in api_url.lower()
        
    def translate_text(self, text: str, source_lang: str = "ja", target_lang: str = "en") -> str:
        """Translate text using LibreTranslate API"""
        # Ensure text is properly encoded
        text = safe_decode_text(text)
        logger.info(f"LibreTranslate: Starting translation of '{text}' from {source_lang} to {target_lang}")
        
        if not text or not text.strip():
            logger.debug("Empty text provided, returning as-is")
            return text
            
        lang_map = {"ja": "ja", "en": "en", "ko": "ko", "zh": "zh", "es": "es", "fr": "fr", "de": "de", "it": "it", "pt": "pt", "ru": "ru"}
        source_lang = lang_map.get(source_lang, source_lang)
        target_lang = lang_map.get(target_lang, target_lang)
        
        endpoint = f"{self.api_url}translate"
        data = {
            "q": text,
            "source": source_lang,
            "target": target_lang
        }
        # Add API key if available (required for libretranslate.com, optional for self-hosted)
        if self.api_key:
            data["api_key"] = self.api_key
        
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            logger.debug(f"Making request to LibreTranslate API: {endpoint}")
            # Use JSON format like official API documentation
            response = requests.post(endpoint, json=data, headers=headers, timeout=15)
            logger.debug(f"LibreTranslate response status: {response.status_code}")
            response.raise_for_status()
            
            result = response.json()
            logger.debug(f"LibreTranslate response: {result}")
            
            if "translatedText" in result:
                translated_text = result["translatedText"]
                logger.info(f"LibreTranslate SUCCESS: '{text}' -> '{translated_text}'")
                return translated_text
            else:
                raise TranslationError("LibreTranslate API returned no translation")
                
        except requests.HTTPError as e:
            if e.response.status_code == 429:
                raise TranslationError("LibreTranslate rate limit exceeded")
            elif e.response.status_code == 400:
                raise TranslationError("LibreTranslate: Invalid language pair or text")
            else:
                logger.error(f"LibreTranslate HTTP error: {e}")
                raise TranslationError(f"LibreTranslate API error: {e}")
        except requests.Timeout:
            logger.error("LibreTranslate request timed out")
            raise TranslationError("LibreTranslate request timed out after 15 seconds")
        except requests.RequestException as e:
            logger.error(f"LibreTranslate API request failed: {e}")
            raise TranslationError(f"LibreTranslate API request failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in LibreTranslate: {e}")
            raise TranslationError(f"Unexpected error: {e}")
    
    def is_available(self) -> bool:
        """Check if LibreTranslate service is available"""
        try:
            endpoint = f"{self.api_url}languages"
            
            params = {}
            if self.api_key:
                params["api_key"] = self.api_key
            
            response = requests.get(endpoint, params=params if params else None, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_supported_languages(self) -> List[Tuple[str, str]]:
        """Get supported languages for LibreTranslate"""
        try:
            endpoint = f"{self.api_url}languages"
            
            params = {}
            if self.api_key:
                params["api_key"] = self.api_key
            
            response = requests.get(endpoint, params=params if params else None, timeout=5)
                
            if response.status_code == 200:
                languages = response.json()
                return [(lang["code"], lang["name"]) for lang in languages]
        except:
            pass
        
        # Fallback to common languages
        return [
            ("ja", "Japanese"),
            ("en", "English"),
            ("ko", "Korean"),
            ("zh", "Chinese"),
            ("es", "Spanish"),
            ("fr", "French"),
            ("de", "German"),
            ("it", "Italian"),
            ("pt", "Portuguese"),
            ("ru", "Russian")
        ]
    
    def supports_batch_translation(self) -> bool:
        """LibreTranslate optimized batch processing (concurrent requests)"""
        return True
    
    def batch_translate(self, texts: List[str], source_lang: str = "ja", target_lang: str = "en") -> List[str]:
        """Translate multiple texts using LibreTranslate with optimized concurrent requests"""
        if not texts:
            return []
        
        # Ensure all texts are properly encoded
        texts = [safe_decode_text(text) for text in texts]
        logger.info(f"LibreTranslate: Starting batch translation of {len(texts)} texts from {source_lang} to {target_lang}")
        
        # Check cache and separate cached vs uncached texts
        results = [None] * len(texts)
        uncached_indices = []
        uncached_texts = []
        
        for i, text in enumerate(texts):
            if not text or not text.strip():
                results[i] = text
                continue
                
            cache_key = f"{source_lang}_{target_lang}_{text}"
            if cache_key in self._cache:
                results[i] = self._cache[cache_key]
                continue
            
            uncached_indices.append(i)
            uncached_texts.append(text)
        
        if not uncached_texts:
            logger.info(f"LibreTranslate: All {len(texts)} texts found in cache")
            return results
        
        logger.info(f"LibreTranslate: Translating {len(uncached_texts)} uncached texts")
        
        # LibreTranslate language mapping
        lang_map = {"ja": "ja", "en": "en", "ko": "ko", "zh": "zh", "es": "es", "fr": "fr", "de": "de", "it": "it", "pt": "pt", "ru": "ru"}
        source_lang_code = lang_map.get(source_lang, source_lang)
        target_lang_code = lang_map.get(target_lang, target_lang)
        
        # Batch process in groups to avoid overwhelming the server
        import concurrent.futures
        from concurrent.futures import ThreadPoolExecutor
        
        def translate_single_text(text_info):
            idx, text = text_info
            try:
                translated = self.translate_text(text, source_lang, target_lang)
                cache_key = f"{source_lang}_{target_lang}_{text}"
                self._cache[cache_key] = translated
                return idx, translated, None
            except Exception as e:
                logger.warning(f"LibreTranslate translation failed for '{text}': {e}")
                return idx, text, e
        
        # Use thread pool for concurrent requests (limited to avoid server overload)
        max_workers = min(len(uncached_texts), 3)
        batch_size = 10  # Process in smaller batches
        
        for batch_start in range(0, len(uncached_texts), batch_size):
            batch_end = min(batch_start + batch_size, len(uncached_texts))
            batch_texts = uncached_texts[batch_start:batch_end]
            batch_indices = uncached_indices[batch_start:batch_end]
            
            text_info_batch = [(batch_indices[i], text) for i, text in enumerate(batch_texts)]
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_text = {executor.submit(translate_single_text, text_info): text_info for text_info in text_info_batch}
                
                for future in concurrent.futures.as_completed(future_to_text):
                    try:
                        original_idx, translated_text, error = future.result(timeout=30)
                        results[original_idx] = translated_text
                        
                        if error is None:
                            logger.debug(f"LibreTranslate SUCCESS: -> '{translated_text}'")
                        else:
                            logger.debug(f"LibreTranslate FAILED: {error}")
                            
                    except concurrent.futures.TimeoutError:
                        text_info = future_to_text[future]
                        original_idx, original_text = text_info
                        results[original_idx] = original_text
                        logger.warning(f"LibreTranslate timeout for text: '{original_text}'")
                    except Exception as e:
                        text_info = future_to_text[future]
                        original_idx, original_text = text_info
                        results[original_idx] = original_text
                        logger.error(f"LibreTranslate thread error for '{original_text}': {e}")
            
            if batch_end < len(uncached_texts):
                time.sleep(0.5)
        
        for i, result in enumerate(results):
            if result is None:
                results[i] = texts[i]
        
        successful_translations = sum(1 for i, result in enumerate(results) if result != texts[i])
        logger.info(f"LibreTranslate batch translation complete: {successful_translations}/{len(texts)} successfully translated")
        
        return results


class TranslationServiceManager:
    """Manages multiple translation services with fallback logic"""
    
    def __init__(self):
        self._services: Dict[str, TranslationService] = {}
        self._primary_service: Optional[str] = None
        self._initialize_services()
        
    def _initialize_services(self):
        """Initialize available translation services"""
        mymemory = MyMemoryService()
        self._services["mymemory"] = mymemory
        
        libretranslate_url = get_preference("libretranslate_url", "https://libretranslate.com")
        libretranslate_api_key = get_preference("libretranslate_api_key", "")
        libretranslate = LibreTranslateService(api_url=libretranslate_url, api_key=libretranslate_api_key if libretranslate_api_key else None)
        self._services["libretranslate"] = libretranslate
        
        deepl_api_key = get_preference("deepl_api_key", "")
        if deepl_api_key:
            deepl = DeepLService(api_key=deepl_api_key, use_free_api=True)
            self._services["deepl"] = deepl
        
        # Set primary service from preferences (default to free service)
        self._primary_service = get_preference("translation_service", "mymemory")
        
        logger.info(f"Initialized translation services: {list(self._services.keys())}")
        logger.info(f"Primary service: {self._primary_service}")
        
    def get_available_services(self) -> List[Tuple[str, str]]:
        """Get list of available translation services"""
        available = []
        for service_id, service in self._services.items():
            if service.is_available():
                available.append((service_id, service.name))
            else:
                logger.debug(f"Service {service.name} is not available")
        return available
        
    def set_primary_service(self, service_id: str) -> bool:
        """Set the primary translation service"""
        if service_id in self._services:
            self._primary_service = service_id
            save_preference("translation_service", service_id)
            logger.info(f"Set primary translation service to: {service_id}")
            return True
        return False
        
    def get_service(self, service_id: Optional[str] = None) -> Optional[TranslationService]:
        """Get a translation service by ID"""
        if service_id is None:
            service_id = self._primary_service
            
        if service_id and service_id in self._services:
            service = self._services[service_id]
            if service.is_available():
                return service
                
        return None
        
    def translate_with_fallback(self, text: str, source_lang: str = "ja", target_lang: str = "en") -> Tuple[str, str]:
        """Translate text with automatic fallback to other services"""
        # Ensure text is properly encoded
        text = safe_decode_text(text)
        if not text or not text.strip():
            return text, "none"
            
        # Try primary service first
        primary_service = self.get_service()
        if primary_service:
            try:
                result = primary_service.translate_text(text, source_lang, target_lang)
                return result, primary_service.name
            except Exception as e:
                logger.warning(f"Primary service {primary_service.name} failed: {e}")
        
        for service_id, service in self._services.items():
            if service_id == self._primary_service:
                continue  
                
            if service.is_available():
                try:
                    result = service.translate_text(text, source_lang, target_lang)
                    logger.info(f"Fallback to {service.name} successful")
                    return result, service.name
                except Exception as e:
                    logger.warning(f"Fallback service {service.name} failed: {e}")
        
        logger.error(f"All translation services failed for: {text}")
        return text, "failed"
        
    def batch_translate_with_fallback(self, texts: List[str], source_lang: str = "ja", target_lang: str = "en") -> List[Tuple[str, str]]:
        """Batch translate with fallback - uses optimized batch processing when available"""
        if not texts:
            return []
            
        logger.info(f"Starting batch translation of {len(texts)} texts using service manager")
        
        primary_service = self.get_service()
        if primary_service:
            try:
                if primary_service.supports_batch_translation():
                    logger.info(f"Using native batch translation with {primary_service.name}")
                    translations = primary_service.batch_translate(texts, source_lang, target_lang)
                    return [(translation, primary_service.name) for translation in translations]
                else:
                    logger.info(f"Service {primary_service.name} does not support batch translation, using individual requests")
                    # Use the base implementation for services without batch support
                    translations = []
                    for text in texts:
                        translated = primary_service.translate_text(text, source_lang, target_lang)
                        translations.append(translated)
                    return [(translation, primary_service.name) for translation in translations]
                    
            except Exception as e:
                logger.warning(f"Batch translation failed with {primary_service.name}: {e}")
        
        results = []
        for text in texts:
            translation, service_name = self.translate_with_fallback(text, source_lang, target_lang)
            results.append((translation, service_name))
            
        return results


# Global translation service manager instance
_translation_manager: Optional[TranslationServiceManager] = None


def get_translation_manager() -> TranslationServiceManager:
    """Get the global translation service manager"""
    global _translation_manager
    if _translation_manager is None:
        _translation_manager = TranslationServiceManager()
    return _translation_manager


def configure_deepl_translator(api_key: str, use_free_api: bool = True) -> bool:
    """Configure DeepL translation service"""
    try:
        save_preference("deepl_api_key", api_key)
        save_preference("deepl_use_free_api", use_free_api)
        
        # Test the API key
        deepl = DeepLService(api_key=api_key, use_free_api=use_free_api)
        if deepl.is_available():
            # Re-initialize the global manager to pick up new service
            global _translation_manager
            _translation_manager = None
            logger.info("DeepL translator configured successfully")
            return True
        else:
            logger.error("DeepL API key test failed")
            return False
    except Exception as e:
        logger.error(f"Failed to configure DeepL translator: {e}")
        return False


def configure_libretranslate_server(server_url: str, api_key: str = None) -> bool:
    """Configure LibreTranslate server URL and optional API key"""
    try:
        if not server_url.strip():
            server_url = "https://libretranslate.com"
            
        # Ensure proper URL format
        if not server_url.startswith(('http://', 'https://')):
            server_url = 'https://' + server_url
            
        save_preference("libretranslate_url", server_url)
        save_preference("libretranslate_api_key", api_key if api_key else "")
        
        # Test the server
        libretranslate = LibreTranslateService(api_url=server_url, api_key=api_key)
        if libretranslate.is_available():
            # Re-initialize the global manager to pick up new service
            global _translation_manager
            _translation_manager = None
            logger.info(f"LibreTranslate server configured successfully: {server_url}")
            return True
        else:
            logger.error(f"LibreTranslate server test failed: {server_url}")
            return False
    except Exception as e:
        logger.error(f"Failed to configure LibreTranslate server: {e}")
        return False




