# ======================================================================================================================
# AgroPulse NVR - Localization & Internationalization (i18n)
# Multi-language support, translation management, locale handling, currency formatting
# ======================================================================================================================

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path

logger = logging.getLogger(__name__)

# ======================================================================================================================
# I18N MODELS
# ======================================================================================================================

class Locale(Enum):
    """Supported locales"""
    EN_US = "en_US"  # English (United States)
    ES_ES = "es_ES"  # Spanish (Spain)
    FR_FR = "fr_FR"  # French (France)
    DE_DE = "de_DE"  # German (Germany)
    PT_BR = "pt_BR"  # Portuguese (Brazil)
    ZH_CN = "zh_CN"  # Chinese (Simplified)
    JA_JP = "ja_JP"  # Japanese
    KO_KR = "ko_KR"  # Korean
    IT_IT = "it_IT"  # Italian
    RU_RU = "ru_RU"  # Russian
    AR_SA = "ar_SA"  # Arabic (Saudi Arabia)
    HI_IN = "hi_IN"  # Hindi (India)

class TextDirection(Enum):
    """Text direction"""
    LTR = "ltr"  # Left-to-right
    RTL = "rtl"  # Right-to-left

@dataclass
class LocaleInfo:
    """Locale information"""
    locale: Locale
    language_code: str
    country_code: str
    display_name: str
    native_name: str
    text_direction: TextDirection
    currency_code: str
    currency_symbol: str
    date_format: str
    time_format: str
    decimal_separator: str
    thousands_separator: str

@dataclass
class Translation:
    """Translation entry"""
    key: str
    locale: Locale
    value: str
    context: Optional[str] = None
    plural_forms: Optional[Dict[str, str]] = None
    last_updated: datetime = field(default_factory=datetime.now)

# ======================================================================================================================
# LOCALE REGISTRY
# ======================================================================================================================

class LocaleRegistry:
    """Registry of supported locales"""
    
    def __init__(self):
        self.locales: Dict[Locale, LocaleInfo] = {}
        self._initialize_locales()
        
        logger.info("[LOCALE-REG] Locale registry initialized")
    
    def _initialize_locales(self):
        """Initialize locale information"""
        self.locales[Locale.EN_US] = LocaleInfo(
            locale=Locale.EN_US,
            language_code="en",
            country_code="US",
            display_name="English (United States)",
            native_name="English",
            text_direction=TextDirection.LTR,
            currency_code="USD",
            currency_symbol="$",
            date_format="%m/%d/%Y",
            time_format="%I:%M %p",
            decimal_separator=".",
            thousands_separator=","
        )
        
        self.locales[Locale.ES_ES] = LocaleInfo(
            locale=Locale.ES_ES,
            language_code="es",
            country_code="ES",
            display_name="Spanish (Spain)",
            native_name="Español",
            text_direction=TextDirection.LTR,
            currency_code="EUR",
            currency_symbol="€",
            date_format="%d/%m/%Y",
            time_format="%H:%M",
            decimal_separator=",",
            thousands_separator="."
        )
        
        self.locales[Locale.FR_FR] = LocaleInfo(
            locale=Locale.FR_FR,
            language_code="fr",
            country_code="FR",
            display_name="French (France)",
            native_name="Français",
            text_direction=TextDirection.LTR,
            currency_code="EUR",
            currency_symbol="€",
            date_format="%d/%m/%Y",
            time_format="%H:%M",
            decimal_separator=",",
            thousands_separator=" "
        )
        
        self.locales[Locale.ZH_CN] = LocaleInfo(
            locale=Locale.ZH_CN,
            language_code="zh",
            country_code="CN",
            display_name="Chinese (Simplified)",
            native_name="简体中文",
            text_direction=TextDirection.LTR,
            currency_code="CNY",
            currency_symbol="¥",
            date_format="%Y年%m月%d日",
            time_format="%H:%M",
            decimal_separator=".",
            thousands_separator=","
        )
        
        self.locales[Locale.AR_SA] = LocaleInfo(
            locale=Locale.AR_SA,
            language_code="ar",
            country_code="SA",
            display_name="Arabic (Saudi Arabia)",
            native_name="العربية",
            text_direction=TextDirection.RTL,
            currency_code="SAR",
            currency_symbol="﷼",
            date_format="%d/%m/%Y",
            time_format="%I:%M %p",
            decimal_separator=".",
            thousands_separator=","
        )
    
    def get_locale_info(self, locale: Locale) -> LocaleInfo:
        """Get locale information"""
        return self.locales.get(locale, self.locales[Locale.EN_US])
    
    def get_supported_locales(self) -> List[LocaleInfo]:
        """Get all supported locales"""
        return list(self.locales.values())
    
    def parse_locale(self, locale_string: str) -> Locale:
        """Parse locale string"""
        try:
            return Locale(locale_string)
        except ValueError:
            # Try language code only
            language_code = locale_string.split('_')[0].lower()
            for locale in self.locales.keys():
                if locale.value.split('_')[0].lower() == language_code:
                    return locale
            
            return Locale.EN_US

# ======================================================================================================================
# TRANSLATION STORE
# ======================================================================================================================

class TranslationStore:
    """Store and manage translations"""
    
    def __init__(self):
        self.translations: Dict[Locale, Dict[str, Translation]] = {}
        
        # Initialize empty dictionaries for each locale
        for locale in Locale:
            self.translations[locale] = {}
        
        logger.info("[TRANS-STORE] Translation store initialized")
    
    def add_translation(self, translation: Translation):
        """Add translation"""
        self.translations[translation.locale][translation.key] = translation
        logger.debug(f"[TRANS-STORE] Added: {translation.locale.value}.{translation.key}")
    
    def get_translation(self, locale: Locale, key: str,
                       default: Optional[str] = None) -> str:
        """Get translation"""
        translation = self.translations.get(locale, {}).get(key)
        
        if translation:
            return translation.value
        
        # Fallback to English
        if locale != Locale.EN_US:
            translation = self.translations.get(Locale.EN_US, {}).get(key)
            if translation:
                logger.debug(f"[TRANS-STORE] Fallback to EN_US for: {key}")
                return translation.value
        
        # Return key if no translation found
        return default or key
    
    def get_plural(self, locale: Locale, key: str,
                  count: int, default: Optional[str] = None) -> str:
        """Get plural translation"""
        translation = self.translations.get(locale, {}).get(key)
        
        if translation and translation.plural_forms:
            # Simple plural rules (can be extended)
            if count == 0 and 'zero' in translation.plural_forms:
                return translation.plural_forms['zero']
            elif count == 1 and 'one' in translation.plural_forms:
                return translation.plural_forms['one']
            elif 'other' in translation.plural_forms:
                return translation.plural_forms['other']
        
        return self.get_translation(locale, key, default)
    
    def has_translation(self, locale: Locale, key: str) -> bool:
        """Check if translation exists"""
        return key in self.translations.get(locale, {})
    
    def get_all_keys(self, locale: Locale) -> List[str]:
        """Get all translation keys for locale"""
        return list(self.translations.get(locale, {}).keys())
    
    def get_missing_translations(self, source_locale: Locale,
                                target_locale: Locale) -> List[str]:
        """Get missing translations"""
        source_keys = set(self.get_all_keys(source_locale))
        target_keys = set(self.get_all_keys(target_locale))
        
        return list(source_keys - target_keys)

# ======================================================================================================================
# TRANSLATION LOADER
# ======================================================================================================================

class TranslationLoader:
    """Load translations from files"""
    
    def __init__(self, translations_dir: str = "translations"):
        self.translations_dir = Path(translations_dir)
        
        logger.info(f"[TRANS-LOADER] Translation loader initialized: {translations_dir}")
    
    def load_translations(self, locale: Locale) -> Dict[str, Translation]:
        """Load translations for locale"""
        file_path = self.translations_dir / f"{locale.value}.json"
        
        if not file_path.exists():
            logger.warning(f"[TRANS-LOADER] Translation file not found: {file_path}")
            return {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            translations = {}
            for key, value in data.items():
                if isinstance(value, dict):
                    # Has plural forms or context
                    translations[key] = Translation(
                        key=key,
                        locale=locale,
                        value=value.get('value', ''),
                        context=value.get('context'),
                        plural_forms=value.get('plural_forms')
                    )
                else:
                    # Simple string
                    translations[key] = Translation(
                        key=key,
                        locale=locale,
                        value=value
                    )
            
            logger.info(f"[TRANS-LOADER] Loaded {len(translations)} translations for {locale.value}")
            return translations
            
        except Exception as e:
            logger.error(f"[TRANS-LOADER] Load error: {e}")
            return {}
    
    def save_translations(self, locale: Locale,
                         translations: Dict[str, Translation]):
        """Save translations to file"""
        file_path = self.translations_dir / f"{locale.value}.json"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            data = {}
            for key, translation in translations.items():
                if translation.plural_forms or translation.context:
                    data[key] = {
                        'value': translation.value,
                        'context': translation.context,
                        'plural_forms': translation.plural_forms
                    }
                else:
                    data[key] = translation.value
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"[TRANS-LOADER] Saved {len(translations)} translations")
            
        except Exception as e:
            logger.error(f"[TRANS-LOADER] Save error: {e}")

# ======================================================================================================================
# FORMATTER
# ======================================================================================================================

class Formatter:
    """Format numbers, dates, and currencies"""
    
    def __init__(self, locale_registry: LocaleRegistry):
        self.locale_registry = locale_registry
        
        logger.info("[FORMATTER] Formatter initialized")
    
    def format_number(self, number: float, locale: Locale,
                     decimals: int = 2) -> str:
        """Format number"""
        locale_info = self.locale_registry.get_locale_info(locale)
        
        # Round to decimals
        rounded = round(number, decimals)
        
        # Split into integer and decimal parts
        int_part = int(rounded)
        dec_part = round((rounded - int_part) * (10 ** decimals))
        
        # Format integer part with thousands separator
        int_str = str(abs(int_part))
        formatted_int = ""
        
        for i, digit in enumerate(reversed(int_str)):
            if i > 0 and i % 3 == 0:
                formatted_int = locale_info.thousands_separator + formatted_int
            formatted_int = digit + formatted_int
        
        # Add sign
        if int_part < 0:
            formatted_int = "-" + formatted_int
        
        # Add decimal part
        if decimals > 0:
            dec_str = str(dec_part).zfill(decimals)
            return f"{formatted_int}{locale_info.decimal_separator}{dec_str}"
        
        return formatted_int
    
    def format_currency(self, amount: float, locale: Locale) -> str:
        """Format currency"""
        locale_info = self.locale_registry.get_locale_info(locale)
        
        formatted_number = self.format_number(amount, locale, decimals=2)
        
        # Currency symbol position varies by locale
        if locale in [Locale.EN_US]:
            return f"{locale_info.currency_symbol}{formatted_number}"
        else:
            return f"{formatted_number} {locale_info.currency_symbol}"
    
    def format_date(self, date: datetime, locale: Locale) -> str:
        """Format date"""
        locale_info = self.locale_registry.get_locale_info(locale)
        return date.strftime(locale_info.date_format)
    
    def format_time(self, time: datetime, locale: Locale) -> str:
        """Format time"""
        locale_info = self.locale_registry.get_locale_info(locale)
        return time.strftime(locale_info.time_format)
    
    def format_datetime(self, dt: datetime, locale: Locale) -> str:
        """Format datetime"""
        date_str = self.format_date(dt, locale)
        time_str = self.format_time(dt, locale)
        return f"{date_str} {time_str}"

# ======================================================================================================================
# I18N CONTEXT
# ======================================================================================================================

class I18nContext:
    """Internationalization context"""
    
    def __init__(self, locale: Locale,
                 translation_store: TranslationStore,
                 formatter: Formatter):
        self.locale = locale
        self.translation_store = translation_store
        self.formatter = formatter
        
        logger.info(f"[I18N-CTX] Context created: {locale.value}")
    
    def t(self, key: str, **kwargs) -> str:
        """Translate (short alias)"""
        translation = self.translation_store.get_translation(self.locale, key)
        
        # Replace variables
        for var_key, var_value in kwargs.items():
            translation = translation.replace(f"{{{var_key}}}", str(var_value))
        
        return translation
    
    def tn(self, key: str, count: int, **kwargs) -> str:
        """Translate with plural"""
        translation = self.translation_store.get_plural(self.locale, key, count)
        
        # Replace count and other variables
        translation = translation.replace('{count}', str(count))
        for var_key, var_value in kwargs.items():
            translation = translation.replace(f"{{{var_key}}}", str(var_value))
        
        return translation
    
    def format_number(self, number: float, decimals: int = 2) -> str:
        """Format number"""
        return self.formatter.format_number(number, self.locale, decimals)
    
    def format_currency(self, amount: float) -> str:
        """Format currency"""
        return self.formatter.format_currency(amount, self.locale)
    
    def format_date(self, date: datetime) -> str:
        """Format date"""
        return self.formatter.format_date(date, self.locale)
    
    def format_datetime(self, dt: datetime) -> str:
        """Format datetime"""
        return self.formatter.format_datetime(dt, self.locale)

# ======================================================================================================================
# I18N MANAGER
# ======================================================================================================================

class I18nManager:
    """Main i18n manager"""
    
    def __init__(self, default_locale: Locale = Locale.EN_US,
                 translations_dir: str = "translations"):
        self.default_locale = default_locale
        self.locale_registry = LocaleRegistry()
        self.translation_store = TranslationStore()
        self.translation_loader = TranslationLoader(translations_dir)
        self.formatter = Formatter(self.locale_registry)
        
        logger.info(f"[I18N-MGR] I18n manager initialized: {default_locale.value}")
    
    def initialize(self):
        """Initialize translations"""
        # Load default translations
        self._load_default_translations()
        
        # Load all locale translations
        for locale in Locale:
            translations = self.translation_loader.load_translations(locale)
            for translation in translations.values():
                self.translation_store.add_translation(translation)
    
    def _load_default_translations(self):
        """Load default English translations"""
        default_translations = {
            # Common
            'common.yes': 'Yes',
            'common.no': 'No',
            'common.save': 'Save',
            'common.cancel': 'Cancel',
            'common.delete': 'Delete',
            'common.edit': 'Edit',
            'common.loading': 'Loading...',
            
            # Auth
            'auth.login': 'Login',
            'auth.logout': 'Logout',
            'auth.register': 'Register',
            'auth.forgot_password': 'Forgot Password',
            
            # Dashboard
            'dashboard.title': 'Dashboard',
            'dashboard.welcome': 'Welcome, {name}!',
            'dashboard.farms': 'Farms',
            'dashboard.devices': 'Devices',
            
            # Farms
            'farms.title': 'Farms',
            'farms.create': 'Create Farm',
            'farms.edit': 'Edit Farm',
            'farms.name': 'Farm Name',
            'farms.location': 'Location',
            
            # Detections
            'detections.title': 'Detections',
            'detections.count': '{count} detection',
            'detections.count_plural': '{count} detections',
            'detections.severity': 'Severity',
            
            # Errors
            'error.generic': 'An error occurred',
            'error.not_found': 'Not found',
            'error.unauthorized': 'Unauthorized',
        }
        
        for key, value in default_translations.items():
            translation = Translation(
                key=key,
                locale=Locale.EN_US,
                value=value
            )
            self.translation_store.add_translation(translation)
    
    def get_context(self, locale: Locale) -> I18nContext:
        """Get i18n context for locale"""
        return I18nContext(locale, self.translation_store, self.formatter)
    
    def add_translation(self, key: str, locale: Locale, value: str):
        """Add translation"""
        translation = Translation(key=key, locale=locale, value=value)
        self.translation_store.add_translation(translation)
    
    def get_supported_locales(self) -> List[LocaleInfo]:
        """Get supported locales"""
        return self.locale_registry.get_supported_locales()
    
    def get_translation_coverage(self, locale: Locale) -> Dict[str, Any]:
        """Get translation coverage"""
        en_keys = set(self.translation_store.get_all_keys(Locale.EN_US))
        locale_keys = set(self.translation_store.get_all_keys(locale))
        
        missing = en_keys - locale_keys
        
        return {
            'total_keys': len(en_keys),
            'translated': len(locale_keys),
            'missing': len(missing),
            'coverage_percent': (len(locale_keys) / len(en_keys) * 100) if en_keys else 0,
            'missing_keys': list(missing)
        }

# ======================================================================================================================
# I18N ORCHESTRATOR
# ======================================================================================================================

class I18nOrchestrator:
    """I18n orchestrator"""
    
    def __init__(self, default_locale: Locale = Locale.EN_US):
        self.i18n_manager = I18nManager(default_locale)
        
        logger.info("[I18N-ORCH] I18n orchestrator initialized")
    
    def initialize(self):
        """Initialize i18n system"""
        self.i18n_manager.initialize()
    
    def get_context(self, locale_string: str) -> I18nContext:
        """Get i18n context from locale string"""
        locale = self.i18n_manager.locale_registry.parse_locale(locale_string)
        return self.i18n_manager.get_context(locale)
    
    def translate(self, locale: Locale, key: str, **kwargs) -> str:
        """Translate key"""
        ctx = self.i18n_manager.get_context(locale)
        return ctx.t(key, **kwargs)
    
    def get_supported_locales(self) -> List[Dict[str, Any]]:
        """Get supported locales"""
        return [
            {
                'code': info.locale.value,
                'display_name': info.display_name,
                'native_name': info.native_name
            }
            for info in self.i18n_manager.get_supported_locales()
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get i18n statistics"""
        total_keys = len(self.i18n_manager.translation_store.get_all_keys(Locale.EN_US))
        
        coverage = {}
        for locale in Locale:
            cov = self.i18n_manager.get_translation_coverage(locale)
            coverage[locale.value] = cov['coverage_percent']
        
        return {
            'total_keys': total_keys,
            'supported_locales': len(Locale),
            'coverage_by_locale': coverage
        }

# ======================================================================================================================
# END OF LOCALIZATION & I18N MODULE
# Lines in this file: ~650+
# Combined total: ~33,350+
# Remaining for 50k: ~16,650 lines
# ======================================================================================================================
