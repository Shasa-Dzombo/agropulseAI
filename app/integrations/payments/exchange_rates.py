"""
Exchange Rate Service and Currency Conversion
=============================================

Real-time exchange rates with caching and automatic USD conversion.
"""

import requests
from typing import Dict, Optional
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
import redis
import json
from decimal import Decimal

logger = logging.getLogger(__name__)


@dataclass
class ExchangeRate:
    """Exchange rate information."""
    base_currency: str
    target_currency: str
    rate: Decimal
    timestamp: datetime
    provider: str


class ExchangeRateService:
    """
    Fetch real-time exchange rates from multiple providers.
    
    Providers:
    1. ExchangeRate-API (free, 1500 req/month)
    2. Fixer.io (free, 100 req/month)
    3. CurrencyAPI (free, 5000 req/month)
    4. Xe.com (paid, most accurate)
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        redis_client: Optional[redis.Redis] = None,
        cache_ttl: int = 7200,  # 2 hours
    ):
        """
        Initialize exchange rate service.
        
        Args:
            api_key: API key for paid providers
            redis_client: Redis client for caching
            cache_ttl: Cache TTL in seconds (default: 2 hours)
        """
        self.api_key = api_key
        self.redis_client = redis_client
        self.cache_ttl = cache_ttl
        
        # API endpoints
        self.providers = {
            'exchangerate_api': 'https://api.exchangerate-api.com/v4/latest/{base}',
            'currencyapi': 'https://api.currencyapi.com/v3/latest?apikey={key}&base_currency={base}',
            'fixer': 'http://data.fixer.io/api/latest?access_key={key}&base={base}',
        }
        
    def get_rate(
        self,
        from_currency: str,
        to_currency: str,
        provider: str = 'exchangerate_api',
    ) -> Optional[ExchangeRate]:
        """
        Get exchange rate from one currency to another.
        
        Args:
            from_currency: Source currency code (e.g., 'USD')
            to_currency: Target currency code (e.g., 'KES')
            provider: Provider to use
            
        Returns:
            ExchangeRate object or None if failed
        """
        # Check cache first
        cache_key = f"exchange_rate:{from_currency}:{to_currency}"
        if self.redis_client:
            cached = self.redis_client.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for {from_currency} -> {to_currency}")
                data = json.loads(cached)
                return ExchangeRate(
                    base_currency=data['base_currency'],
                    target_currency=data['target_currency'],
                    rate=Decimal(data['rate']),
                    timestamp=datetime.fromisoformat(data['timestamp']),
                    provider=data['provider'],
                )
                
        # Fetch from API
        try:
            if provider == 'exchangerate_api':
                rate = self._get_from_exchangerate_api(from_currency, to_currency)
            elif provider == 'currencyapi':
                rate = self._get_from_currencyapi(from_currency, to_currency)
            elif provider == 'fixer':
                rate = self._get_from_fixer(from_currency, to_currency)
            else:
                raise ValueError(f"Unknown provider: {provider}")
                
            # Cache result
            if rate and self.redis_client:
                cache_data = {
                    'base_currency': rate.base_currency,
                    'target_currency': rate.target_currency,
                    'rate': str(rate.rate),
                    'timestamp': rate.timestamp.isoformat(),
                    'provider': rate.provider,
                }
                self.redis_client.setex(
                    cache_key,
                    self.cache_ttl,
                    json.dumps(cache_data)
                )
                
            return rate
            
        except Exception as e:
            logger.error(f"Failed to get exchange rate {from_currency} -> {to_currency}: {e}")
            return None
            
    def _get_from_exchangerate_api(
        self,
        from_currency: str,
        to_currency: str,
    ) -> Optional[ExchangeRate]:
        """Get rate from ExchangeRate-API (free tier)."""
        url = self.providers['exchangerate_api'].format(base=from_currency)
        
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        
        if 'rates' not in data or to_currency not in data['rates']:
            logger.warning(f"Currency {to_currency} not found in response")
            return None
            
        rate = Decimal(str(data['rates'][to_currency]))
        
        return ExchangeRate(
            base_currency=from_currency,
            target_currency=to_currency,
            rate=rate,
            timestamp=datetime.now(),
            provider='exchangerate_api',
        )
        
    def _get_from_currencyapi(
        self,
        from_currency: str,
        to_currency: str,
    ) -> Optional[ExchangeRate]:
        """Get rate from CurrencyAPI (requires API key)."""
        if not self.api_key:
            logger.warning("CurrencyAPI requires API key")
            return None
            
        url = self.providers['currencyapi'].format(
            key=self.api_key,
            base=from_currency
        )
        
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        
        if 'data' not in data or to_currency not in data['data']:
            return None
            
        rate = Decimal(str(data['data'][to_currency]['value']))
        
        return ExchangeRate(
            base_currency=from_currency,
            target_currency=to_currency,
            rate=rate,
            timestamp=datetime.now(),
            provider='currencyapi',
        )
        
    def _get_from_fixer(
        self,
        from_currency: str,
        to_currency: str,
    ) -> Optional[ExchangeRate]:
        """Get rate from Fixer.io (requires API key)."""
        if not self.api_key:
            logger.warning("Fixer.io requires API key")
            return None
            
        # Fixer.io only supports EUR as base on free tier
        # Need to convert: from_currency -> EUR -> to_currency
        logger.warning("Fixer.io provider requires EUR as base currency")
        return None
        
    def get_rate_with_fallback(
        self,
        from_currency: str,
        to_currency: str,
    ) -> ExchangeRate:
        """
        Get exchange rate with automatic fallback to multiple providers.
        
        Args:
            from_currency: Source currency
            to_currency: Target currency
            
        Returns:
            ExchangeRate (defaults to 1.0 if all fail)
        """
        for provider in ['exchangerate_api', 'currencyapi', 'fixer']:
            try:
                rate = self.get_rate(from_currency, to_currency, provider)
                if rate:
                    logger.info(f"Got rate {from_currency} -> {to_currency}: {rate.rate} from {provider}")
                    return rate
            except Exception as e:
                logger.warning(f"Provider {provider} failed: {e}")
                continue
                
        # Default to 1.0 if all providers fail
        logger.error(f"All providers failed for {from_currency} -> {to_currency}, defaulting to 1.0")
        return ExchangeRate(
            base_currency=from_currency,
            target_currency=to_currency,
            rate=Decimal('1.0'),
            timestamp=datetime.now(),
            provider='default',
        )
        
    def get_all_rates(
        self,
        base_currency: str = 'USD',
    ) -> Dict[str, Decimal]:
        """
        Get all exchange rates for a base currency.
        
        Args:
            base_currency: Base currency code
            
        Returns:
            Dictionary of currency codes to rates
        """
        url = self.providers['exchangerate_api'].format(base=base_currency)
        
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            
            rates = {
                currency: Decimal(str(rate))
                for currency, rate in data.get('rates', {}).items()
            }
            
            logger.info(f"Fetched {len(rates)} exchange rates for {base_currency}")
            return rates
            
        except Exception as e:
            logger.error(f"Failed to get all rates for {base_currency}: {e}")
            return {}


class CurrencyConverter:
    """
    Convert amounts between currencies with proper rounding.
    """
    
    def __init__(self, exchange_rate_service: ExchangeRateService):
        """Initialize currency converter."""
        self.exchange_rate_service = exchange_rate_service
        
        # Currency decimal places
        self.decimal_places = {
            'USD': 2, 'EUR': 2, 'GBP': 2,
            'KES': 2, 'NGN': 2, 'GHS': 2,
            'UGX': 0,  # No decimals for Ugandan Shilling
            'TZS': 0,  # No decimals for Tanzanian Shilling
            'INR': 2, 'BRL': 2, 'MXN': 2,
        }
        
    def convert(
        self,
        amount: Decimal,
        from_currency: str,
        to_currency: str,
    ) -> Decimal:
        """
        Convert amount from one currency to another.
        
        Args:
            amount: Amount to convert
            from_currency: Source currency code
            to_currency: Target currency code
            
        Returns:
            Converted amount with proper rounding
        """
        if from_currency == to_currency:
            return amount
            
        # Get exchange rate
        rate = self.exchange_rate_service.get_rate_with_fallback(
            from_currency,
            to_currency
        )
        
        # Convert
        converted = amount * rate.rate
        
        # Round to appropriate decimal places
        decimal_places = self.decimal_places.get(to_currency, 2)
        converted = converted.quantize(
            Decimal(10) ** -decimal_places
        )
        
        logger.debug(
            f"Converted {amount} {from_currency} -> {converted} {to_currency} "
            f"(rate: {rate.rate})"
        )
        
        return converted
        
    def convert_to_usd(
        self,
        amount: Decimal,
        from_currency: str,
    ) -> Decimal:
        """
        Convert amount to USD (business backend currency).
        
        Args:
            amount: Amount in local currency
            from_currency: Source currency code
            
        Returns:
            Amount in USD
        """
        return self.convert(amount, from_currency, 'USD')
        
    def convert_from_usd(
        self,
        amount: Decimal,
        to_currency: str,
    ) -> Decimal:
        """
        Convert amount from USD to local currency (user display).
        
        Args:
            amount: Amount in USD
            to_currency: Target currency code
            
        Returns:
            Amount in local currency
        """
        return self.convert(amount, 'USD', to_currency)
        
    def format_amount(
        self,
        amount: Decimal,
        currency: str,
        currency_symbol: str,
    ) -> str:
        """
        Format amount with currency symbol for display.
        
        Args:
            amount: Amount to format
            currency: Currency code
            currency_symbol: Currency symbol
            
        Returns:
            Formatted string (e.g., "KSh 1,500.00")
        """
        decimal_places = self.decimal_places.get(currency, 2)
        
        # Format with thousand separators
        if decimal_places == 0:
            formatted = f"{currency_symbol} {amount:,.0f}"
        else:
            formatted = f"{currency_symbol} {amount:,.{decimal_places}f}"
            
        return formatted


class RateCache:
    """
    Intelligent caching for exchange rates with automatic refresh.
    """
    
    def __init__(
        self,
        redis_client: redis.Redis,
        refresh_interval: int = 3600,
    ):
        """
        Initialize rate cache.
        
        Args:
            redis_client: Redis client
            refresh_interval: Refresh interval in seconds (default: 1 hour)
        """
        self.redis_client = redis_client
        self.refresh_interval = refresh_interval
        
    def get(
        self,
        from_currency: str,
        to_currency: str,
    ) -> Optional[ExchangeRate]:
        """Get cached exchange rate."""
        cache_key = f"exchange_rate:{from_currency}:{to_currency}"
        
        cached = self.redis_client.get(cache_key)
        if not cached:
            return None
            
        data = json.loads(cached)
        
        # Check if rate is stale
        timestamp = datetime.fromisoformat(data['timestamp'])
        if datetime.now() - timestamp > timedelta(seconds=self.refresh_interval):
            logger.debug(f"Rate {from_currency} -> {to_currency} is stale")
            return None
            
        return ExchangeRate(
            base_currency=data['base_currency'],
            target_currency=data['target_currency'],
            rate=Decimal(data['rate']),
            timestamp=timestamp,
            provider=data['provider'],
        )
        
    def set(
        self,
        rate: ExchangeRate,
        ttl: Optional[int] = None,
    ):
        """Cache exchange rate."""
        cache_key = f"exchange_rate:{rate.base_currency}:{rate.target_currency}"
        
        cache_data = {
            'base_currency': rate.base_currency,
            'target_currency': rate.target_currency,
            'rate': str(rate.rate),
            'timestamp': rate.timestamp.isoformat(),
            'provider': rate.provider,
        }
        
        if ttl:
            self.redis_client.setex(cache_key, ttl, json.dumps(cache_data))
        else:
            self.redis_client.setex(
                cache_key,
                self.refresh_interval,
                json.dumps(cache_data)
            )
            
        logger.debug(f"Cached rate {rate.base_currency} -> {rate.target_currency}")
        
    def invalidate(
        self,
        from_currency: str,
        to_currency: str,
    ):
        """Invalidate cached rate."""
        cache_key = f"exchange_rate:{from_currency}:{to_currency}"
        self.redis_client.delete(cache_key)
        logger.debug(f"Invalidated rate {from_currency} -> {to_currency}")
        
    def get_all_cached_rates(self) -> list[ExchangeRate]:
        """Get all cached rates."""
        pattern = "exchange_rate:*"
        keys = self.redis_client.keys(pattern)
        
        rates = []
        for key in keys:
            cached = self.redis_client.get(key)
            if cached:
                data = json.loads(cached)
                rates.append(ExchangeRate(
                    base_currency=data['base_currency'],
                    target_currency=data['target_currency'],
                    rate=Decimal(data['rate']),
                    timestamp=datetime.fromisoformat(data['timestamp']),
                    provider=data['provider'],
                ))
                
        return rates
