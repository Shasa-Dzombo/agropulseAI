"""
Multi-Currency Payment Integration System
=========================================

Global payment processing with automatic geolocation, currency detection,
and unified USD backend. Supports M-PESA, Flutterwave, Stripe, and local
payment methods across Africa, Asia, and Latin America.

Architecture:
1. Geolocation API → Detect user country
2. Currency API → Get real-time exchange rates
3. Payment Gateway Aggregator → Process local payments
4. USD Conversion Backend → Unified business account

Supported Methods:
- Mobile Money: M-PESA (Kenya), MTN (Ghana/Uganda), Airtel Money
- Local Cards: Flutterwave, Paystack (Africa)
- International: Stripe, PayPal
- Bank Transfer: Local bank integrations
"""

from .geolocation import (
    GeolocationService,
    CurrencyDetector,
    CountryMapper,
)
from .exchange_rates import (
    ExchangeRateService,
    CurrencyConverter,
    RateCache,
)
from .payment_gateways import (
    StripeGateway,
    FlutterwaveGateway,
    MPesaGateway,
    PaystackGateway,
    PayPalGateway,
)
from .payment_router import (
    PaymentRouter,
    GatewaySelector,
    FallbackHandler,
)
from .models import (
    Payment,
    Transaction,
    PaymentMethod,
    Currency,
)

__all__ = [
    # Geolocation
    'GeolocationService',
    'CurrencyDetector',
    'CountryMapper',
    
    # Exchange rates
    'ExchangeRateService',
    'CurrencyConverter',
    'RateCache',
    
    # Payment gateways
    'StripeGateway',
    'FlutterwaveGateway',
    'MPesaGateway',
    'PaystackGateway',
    'PayPalGateway',
    
    # Routing
    'PaymentRouter',
    'GatewaySelector',
    'FallbackHandler',
    
    # Models
    'Payment',
    'Transaction',
    'PaymentMethod',
    'Currency',
]
