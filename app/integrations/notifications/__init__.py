"""
SMS Notification Integration Module
===================================

Multi-provider SMS delivery system for agricultural alerts, payment confirmations,
and advisories. Supports local languages and carrier-specific routing.

Providers:
- Twilio: Global coverage, reliable delivery
- Africa's Talking: African-focused, competitive rates
- Vonage (Nexmo): Global coverage
- Local carriers: Direct integrations for better rates
"""

from .twilio_client import TwilioSMSClient
from .africas_talking import AfricasTalkingSMSClient
from .vonage_client import VonageSMSClient
from .sms_router import SMSRouter, SMSTemplate
from .delivery_tracker import DeliveryTracker
from .bulk_messaging import BulkSMSService
from .localization import SMSLocalizer

__all__ = [
    'TwilioSMSClient',
    'AfricasTalkingSMSClient',
    'VonageSMSClient',
    'SMSRouter',
    'SMSTemplate',
    'DeliveryTracker',
    'BulkSMSService',
    'SMSLocalizer',
]
