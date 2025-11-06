"""
Geolocation and Currency Detection Service
==========================================

Automatic detection of user location and currency based on IP address.
"""

import requests
from typing import Dict, Optional, Tuple
import logging
from dataclasses import dataclass
from functools import lru_cache
import redis
import json
from datetime import timedelta

logger = logging.getLogger(__name__)


@dataclass
class LocationInfo:
    """User location information."""
    country: str
    country_code: str
    currency: str
    currency_symbol: str
    region: str
    city: str
    latitude: float
    longitude: float
    timezone: str
    flag_emoji: str


class GeolocationService:
    """
    Detect user location from IP address using multiple providers.
    
    Providers:
    1. ip-api.com (free, 45 req/min)
    2. Geoapify (10k req/day free)
    3. Abstract API (20k req/month free)
    """
    
    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        cache_ttl: int = 3600,
    ):
        """
        Initialize geolocation service.
        
        Args:
            redis_client: Redis client for caching
            cache_ttl: Cache TTL in seconds (default: 1 hour)
        """
        self.redis_client = redis_client
        self.cache_ttl = cache_ttl
        
        # API endpoints
        self.providers = {
            'ip_api': 'http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,region,city,lat,lon,timezone,currency',
            'geoapify': 'https://api.geoapify.com/v1/ipinfo?ip={ip}&apiKey={api_key}',
            'abstract': 'https://ipgeolocation.abstractapi.com/v1/?api_key={api_key}&ip_address={ip}',
        }
        
        # Country to currency mapping
        self.country_currency_map = {
            'KE': {'currency': 'KES', 'symbol': 'KSh', 'name': 'Kenyan Shilling'},
            'NG': {'currency': 'NGN', 'symbol': '₦', 'name': 'Nigerian Naira'},
            'GH': {'currency': 'GHS', 'symbol': '₵', 'name': 'Ghanaian Cedi'},
            'UG': {'currency': 'UGX', 'symbol': 'USh', 'name': 'Ugandan Shilling'},
            'TZ': {'currency': 'TZS', 'symbol': 'TSh', 'name': 'Tanzanian Shilling'},
            'ZA': {'currency': 'ZAR', 'symbol': 'R', 'name': 'South African Rand'},
            'IN': {'currency': 'INR', 'symbol': '₹', 'name': 'Indian Rupee'},
            'PK': {'currency': 'PKR', 'symbol': '₨', 'name': 'Pakistani Rupee'},
            'BD': {'currency': 'BDT', 'symbol': '৳', 'name': 'Bangladeshi Taka'},
            'BR': {'currency': 'BRL', 'symbol': 'R$', 'name': 'Brazilian Real'},
            'MX': {'currency': 'MXN', 'symbol': '$', 'name': 'Mexican Peso'},
            'US': {'currency': 'USD', 'symbol': '$', 'name': 'US Dollar'},
            'GB': {'currency': 'GBP', 'symbol': '£', 'name': 'British Pound'},
            'EU': {'currency': 'EUR', 'symbol': '€', 'name': 'Euro'},
        }
        
        # Country flag emojis
        self.flag_emojis = {
            'KE': '🇰🇪', 'NG': '🇳🇬', 'GH': '🇬🇭', 'UG': '🇺🇬',
            'TZ': '🇹🇿', 'ZA': '🇿🇦', 'IN': '🇮🇳', 'PK': '🇵🇰',
            'BD': '🇧🇩', 'BR': '🇧🇷', 'MX': '🇲🇽', 'US': '🇺🇸',
            'GB': '🇬🇧', 'EU': '🇪🇺',
        }
        
    def get_location_from_ip(
        self,
        ip_address: str,
        provider: str = 'ip_api',
    ) -> Optional[LocationInfo]:
        """
        Get location information from IP address.
        
        Args:
            ip_address: User IP address
            provider: Provider to use ('ip_api', 'geoapify', 'abstract')
            
        Returns:
            LocationInfo object or None if failed
        """
        # Check cache first
        cache_key = f"geolocation:{ip_address}"
        if self.redis_client:
            cached = self.redis_client.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for IP {ip_address}")
                data = json.loads(cached)
                return LocationInfo(**data)
                
        # Call API
        try:
            if provider == 'ip_api':
                location = self._get_from_ip_api(ip_address)
            elif provider == 'geoapify':
                location = self._get_from_geoapify(ip_address)
            elif provider == 'abstract':
                location = self._get_from_abstract(ip_address)
            else:
                raise ValueError(f"Unknown provider: {provider}")
                
            # Cache result
            if location and self.redis_client:
                self.redis_client.setex(
                    cache_key,
                    self.cache_ttl,
                    json.dumps(location.__dict__)
                )
                
            return location
            
        except Exception as e:
            logger.error(f"Geolocation failed for {ip_address}: {e}")
            return None
            
    def _get_from_ip_api(self, ip_address: str) -> Optional[LocationInfo]:
        """Get location from ip-api.com (free tier)."""
        url = self.providers['ip_api'].format(ip=ip_address)
        
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('status') == 'fail':
            logger.warning(f"ip-api.com failed: {data.get('message')}")
            return None
            
        country_code = data.get('countryCode', 'US')
        currency_info = self.country_currency_map.get(
            country_code,
            {'currency': 'USD', 'symbol': '$', 'name': 'US Dollar'}
        )
        
        return LocationInfo(
            country=data.get('country', 'Unknown'),
            country_code=country_code,
            currency=currency_info['currency'],
            currency_symbol=currency_info['symbol'],
            region=data.get('region', ''),
            city=data.get('city', ''),
            latitude=data.get('lat', 0.0),
            longitude=data.get('lon', 0.0),
            timezone=data.get('timezone', 'UTC'),
            flag_emoji=self.flag_emojis.get(country_code, '🌍'),
        )
        
    def _get_from_geoapify(self, ip_address: str) -> Optional[LocationInfo]:
        """Get location from Geoapify (requires API key)."""
        # Placeholder - requires API key configuration
        logger.warning("Geoapify provider not fully implemented")
        return None
        
    def _get_from_abstract(self, ip_address: str) -> Optional[LocationInfo]:
        """Get location from Abstract API (requires API key)."""
        # Placeholder - requires API key configuration
        logger.warning("Abstract API provider not fully implemented")
        return None
        
    def detect_location_with_fallback(
        self,
        ip_address: str,
    ) -> LocationInfo:
        """
        Detect location with automatic fallback to multiple providers.
        
        Args:
            ip_address: User IP address
            
        Returns:
            LocationInfo (defaults to US if all fail)
        """
        for provider in ['ip_api', 'geoapify', 'abstract']:
            try:
                location = self.get_location_from_ip(ip_address, provider)
                if location:
                    logger.info(f"Located {ip_address} in {location.country} ({location.currency})")
                    return location
            except Exception as e:
                logger.warning(f"Provider {provider} failed: {e}")
                continue
                
        # Default to US if all providers fail
        logger.warning(f"All providers failed for {ip_address}, defaulting to US")
        return LocationInfo(
            country='United States',
            country_code='US',
            currency='USD',
            currency_symbol='$',
            region='',
            city='',
            latitude=37.7749,
            longitude=-122.4194,
            timezone='America/Los_Angeles',
            flag_emoji='🇺🇸',
        )


class CurrencyDetector:
    """
    Detect and validate currency for payment processing.
    """
    
    def __init__(self, geolocation_service: GeolocationService):
        """Initialize currency detector."""
        self.geolocation_service = geolocation_service
        
        # Supported currencies
        self.supported_currencies = {
            'USD', 'EUR', 'GBP', 'KES', 'NGN', 'GHS', 'UGX',
            'TZS', 'ZAR', 'INR', 'PKR', 'BDT', 'BRL', 'MXN',
        }
        
    def detect_currency_from_ip(
        self,
        ip_address: str,
    ) -> Tuple[str, str, str]:
        """
        Detect currency from IP address.
        
        Args:
            ip_address: User IP address
            
        Returns:
            Tuple of (currency_code, currency_symbol, country_name)
        """
        location = self.geolocation_service.detect_location_with_fallback(ip_address)
        
        return (
            location.currency,
            location.currency_symbol,
            location.country,
        )
        
    def is_currency_supported(self, currency_code: str) -> bool:
        """Check if currency is supported."""
        return currency_code.upper() in self.supported_currencies
        
    def get_payment_methods_for_currency(
        self,
        currency_code: str,
    ) -> list[str]:
        """
        Get available payment methods for a currency.
        
        Args:
            currency_code: ISO 4217 currency code
            
        Returns:
            List of available payment methods
        """
        currency = currency_code.upper()
        
        # African currencies
        if currency in ['KES', 'UGX', 'TZS']:
            return ['mpesa', 'airtel_money', 'bank_transfer', 'card']
        elif currency in ['NGN', 'GHS']:
            return ['flutterwave', 'paystack', 'bank_transfer', 'card']
            
        # Asian currencies
        elif currency in ['INR', 'PKR', 'BDT']:
            return ['paytm', 'upi', 'bank_transfer', 'card']
            
        # Latin American currencies
        elif currency in ['BRL', 'MXN']:
            return ['pix', 'oxxo', 'bank_transfer', 'card']
            
        # International currencies
        elif currency in ['USD', 'EUR', 'GBP']:
            return ['stripe', 'paypal', 'apple_pay', 'google_pay', 'card']
            
        else:
            return ['card', 'bank_transfer']


class CountryMapper:
    """
    Map countries to regions, payment providers, and tax rules.
    """
    
    def __init__(self):
        """Initialize country mapper."""
        self.regions = {
            'east_africa': ['KE', 'UG', 'TZ', 'RW', 'BI'],
            'west_africa': ['NG', 'GH', 'CI', 'SN', 'ML'],
            'south_africa': ['ZA', 'BW', 'NA', 'ZM', 'ZW'],
            'south_asia': ['IN', 'PK', 'BD', 'LK', 'NP'],
            'latin_america': ['BR', 'MX', 'AR', 'CO', 'CL'],
            'north_america': ['US', 'CA'],
            'europe': ['GB', 'DE', 'FR', 'IT', 'ES'],
        }
        
        self.payment_providers = {
            'east_africa': ['mpesa', 'flutterwave'],
            'west_africa': ['flutterwave', 'paystack'],
            'south_africa': ['payfast', 'stripe'],
            'south_asia': ['razorpay', 'paytm'],
            'latin_america': ['mercadopago', 'stripe'],
            'north_america': ['stripe', 'paypal'],
            'europe': ['stripe', 'adyen'],
        }
        
    def get_region(self, country_code: str) -> str:
        """Get region for a country code."""
        for region, countries in self.regions.items():
            if country_code in countries:
                return region
        return 'other'
        
    def get_preferred_providers(self, country_code: str) -> list[str]:
        """Get preferred payment providers for a country."""
        region = self.get_region(country_code)
        return self.payment_providers.get(region, ['stripe'])
        
    def get_tax_rate(self, country_code: str) -> float:
        """Get VAT/sales tax rate for a country."""
        tax_rates = {
            'KE': 0.16,  # 16% VAT
            'NG': 0.075,  # 7.5% VAT
            'GH': 0.15,  # 15% VAT
            'UG': 0.18,  # 18% VAT
            'IN': 0.18,  # 18% GST
            'US': 0.00,  # Varies by state
            'GB': 0.20,  # 20% VAT
            'EU': 0.20,  # Average EU VAT
        }
        return tax_rates.get(country_code, 0.0)
