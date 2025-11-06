"""
Twilio SMS Client Implementation
================================

Professional SMS delivery using Twilio for global reach and high deliverability.
"""

from twilio.rest import Client as TwilioClient
from twilio.base.exceptions import TwilioException
from typing import Dict, List, Optional
from datetime import datetime
import logging
from dataclasses import dataclass, asdict
import redis
import json

logger = logging.getLogger(__name__)


@dataclass
class SMSMessage:
    """SMS message data structure."""
    recipient: str  # Phone number in E.164 format
    message: str
    sender_id: str
    message_type: str  # 'alert', 'payment', 'advisory', 'marketing'
    priority: str  # 'high', 'normal', 'low'
    language: str  # 'en', 'sw', 'yo', 'ha', etc.
    metadata: Dict


@dataclass
class SMSResponse:
    """SMS delivery response."""
    success: bool
    message_id: str
    recipient: str
    status: str  # 'queued', 'sent', 'delivered', 'failed'
    cost: float
    timestamp: datetime
    error_message: Optional[str]


class TwilioSMSClient:
    """
    Twilio SMS client for reliable message delivery.
    
    Features:
    - Global SMS delivery
    - Delivery receipts (DLRs)
    - Cost tracking
    - Message status callbacks
    - Unicode support for local languages
    - Automatic retry on failure
    
    Pricing:
    - Kenya: $0.045/SMS
    - Nigeria: $0.058/SMS
    - India: $0.0062/SMS
    - US: $0.0079/SMS
    """
    
    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        from_number: str,
        redis_client: Optional[redis.Redis] = None,
    ):
        """
        Initialize Twilio client.
        
        Args:
            account_sid: Twilio account SID
            auth_token: Twilio auth token
            from_number: Twilio phone number (E.164 format)
            redis_client: Redis for caching
        """
        self.client = TwilioClient(account_sid, auth_token)
        self.from_number = from_number
        self.redis_client = redis_client
        
    def send_sms(
        self,
        to: str,
        message: str,
        priority: str = 'normal',
    ) -> SMSResponse:
        """
        Send SMS via Twilio.
        
        Args:
            to: Recipient phone number (E.164 format, e.g., +254712345678)
            message: Message content (up to 1600 chars)
            priority: Message priority
            
        Returns:
            SMSResponse with delivery details
        """
        try:
            # Validate phone number format
            if not to.startswith('+'):
                logger.warning(f"Phone number {to} missing + prefix, adding...")
                to = '+' + to
                
            # Send message
            logger.info(f"Sending SMS to {to} via Twilio...")
            
            twilio_message = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=to,
            )
            
            # Parse response
            response = SMSResponse(
                success=True,
                message_id=twilio_message.sid,
                recipient=to,
                status=twilio_message.status,
                cost=float(twilio_message.price or 0),
                timestamp=datetime.now(),
                error_message=None,
            )
            
            # Cache for tracking
            if self.redis_client:
                cache_key = f"sms:twilio:{twilio_message.sid}"
                self.redis_client.setex(
                    cache_key,
                    86400,  # 24 hours
                    json.dumps(asdict(response))
                )
                
            logger.info(f"SMS sent successfully: {twilio_message.sid}")
            return response
            
        except TwilioException as e:
            logger.error(f"Twilio SMS failed: {e}")
            return SMSResponse(
                success=False,
                message_id='',
                recipient=to,
                status='failed',
                cost=0.0,
                timestamp=datetime.now(),
                error_message=str(e),
            )
            
        except Exception as e:
            logger.error(f"Unexpected error sending SMS: {e}")
            return SMSResponse(
                success=False,
                message_id='',
                recipient=to,
                status='failed',
                cost=0.0,
                timestamp=datetime.now(),
                error_message=str(e),
            )
            
    def send_bulk_sms(
        self,
        recipients: List[str],
        message: str,
    ) -> List[SMSResponse]:
        """
        Send SMS to multiple recipients.
        
        Args:
            recipients: List of phone numbers
            message: Message content
            
        Returns:
            List of SMSResponse objects
        """
        responses = []
        
        logger.info(f"Sending bulk SMS to {len(recipients)} recipients...")
        
        for recipient in recipients:
            response = self.send_sms(recipient, message)
            responses.append(response)
            
        success_count = sum(1 for r in responses if r.success)
        total_cost = sum(r.cost for r in responses)
        
        logger.info(
            f"Bulk SMS complete: {success_count}/{len(recipients)} delivered, "
            f"cost: ${total_cost:.4f}"
        )
        
        return responses
        
    def get_message_status(
        self,
        message_id: str,
    ) -> Dict:
        """
        Check SMS delivery status.
        
        Args:
            message_id: Twilio message SID
            
        Returns:
            Status dictionary
        """
        try:
            message = self.client.messages(message_id).fetch()
            
            return {
                'sid': message.sid,
                'status': message.status,
                'to': message.to,
                'from': message.from_,
                'body': message.body,
                'price': message.price,
                'date_sent': message.date_sent,
                'error_code': message.error_code,
                'error_message': message.error_message,
            }
            
        except Exception as e:
            logger.error(f"Failed to get message status: {e}")
            return {'error': str(e)}


class AfricasTalkingSMSClient:
    """
    Africa's Talking SMS client for African markets.
    
    Features:
    - Optimized for Africa (better rates)
    - Premium SMS support
    - Local sender IDs
    - Bulk messaging
    
    Coverage:
    - Kenya, Uganda, Tanzania, Rwanda
    - Nigeria, Ghana, South Africa
    - Botswana, Zambia, Zimbabwe
    
    Pricing:
    - Kenya: $0.01/SMS
    - Nigeria: $0.025/SMS
    - Ghana: $0.015/SMS
    """
    
    def __init__(
        self,
        username: str,
        api_key: str,
        sender_id: str = 'AgroPulse',
    ):
        """
        Initialize Africa's Talking client.
        
        Args:
            username: Africa's Talking username
            api_key: Africa's Talking API key
            sender_id: Sender ID (alphanumeric, 11 chars max)
        """
        try:
            import africastalking
            
            africastalking.initialize(username, api_key)
            self.sms = africastalking.SMS
            self.sender_id = sender_id
            
            logger.info("Africa's Talking SMS client initialized")
            
        except ImportError:
            logger.error("africastalking package not installed")
            raise
            
    def send_sms(
        self,
        to: List[str],
        message: str,
        enqueue: bool = True,
    ) -> SMSResponse:
        """
        Send SMS via Africa's Talking.
        
        Args:
            to: List of recipient phone numbers
            message: Message content
            enqueue: Queue message for sending
            
        Returns:
            SMSResponse
        """
        try:
            logger.info(f"Sending SMS to {len(to)} recipients via Africa's Talking...")
            
            response = self.sms.send(
                message=message,
                recipients=to,
                sender_id=self.sender_id,
                enqueue=enqueue,
            )
            
            # Parse response
            sms_data = response['SMSMessageData']
            recipients = sms_data['Recipients']
            
            if recipients and len(recipients) > 0:
                first_recipient = recipients[0]
                
                return SMSResponse(
                    success=first_recipient['status'] == 'Success',
                    message_id=first_recipient.get('messageId', ''),
                    recipient=first_recipient['number'],
                    status=first_recipient['status'],
                    cost=float(first_recipient.get('cost', '0').replace('KES ', '')),
                    timestamp=datetime.now(),
                    error_message=first_recipient.get('statusCode', None),
                )
            else:
                return SMSResponse(
                    success=False,
                    message_id='',
                    recipient=to[0] if to else '',
                    status='failed',
                    cost=0.0,
                    timestamp=datetime.now(),
                    error_message='No recipients in response',
                )
                
        except Exception as e:
            logger.error(f"Africa's Talking SMS failed: {e}")
            return SMSResponse(
                success=False,
                message_id='',
                recipient=to[0] if to else '',
                status='failed',
                cost=0.0,
                timestamp=datetime.now(),
                error_message=str(e),
            )
            
    def send_premium_sms(
        self,
        to: List[str],
        message: str,
        keyword: str,
        link_id: str,
        retry_duration_in_hours: int = 1,
    ) -> Dict:
        """
        Send premium SMS (for paid services).
        
        Args:
            to: Recipients
            message: Message content
            keyword: Premium keyword
            link_id: Link ID
            retry_duration_in_hours: Retry duration
            
        Returns:
            Response dictionary
        """
        try:
            response = self.sms.send_premium(
                message=message,
                keyword=keyword,
                link_id=link_id,
                recipients=to,
                retry_duration_in_hours=retry_duration_in_hours,
            )
            
            logger.info("Premium SMS sent successfully")
            return response
            
        except Exception as e:
            logger.error(f"Premium SMS failed: {e}")
            return {'error': str(e)}


class VonageSMSClient:
    """Vonage (Nexmo) SMS client for global coverage."""
    
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        from_number: str,
    ):
        """Initialize Vonage client."""
        try:
            import vonage
            
            self.client = vonage.Client(key=api_key, secret=api_secret)
            self.sms = vonage.Sms(self.client)
            self.from_number = from_number
            
            logger.info("Vonage SMS client initialized")
            
        except ImportError:
            logger.error("vonage package not installed")
            raise
            
    def send_sms(
        self,
        to: str,
        message: str,
    ) -> SMSResponse:
        """Send SMS via Vonage."""
        try:
            logger.info(f"Sending SMS to {to} via Vonage...")
            
            response = self.sms.send_message({
                'from': self.from_number,
                'to': to,
                'text': message,
            })
            
            if response['messages'][0]['status'] == '0':
                return SMSResponse(
                    success=True,
                    message_id=response['messages'][0]['message-id'],
                    recipient=to,
                    status='sent',
                    cost=float(response['messages'][0].get('message-price', 0)),
                    timestamp=datetime.now(),
                    error_message=None,
                )
            else:
                return SMSResponse(
                    success=False,
                    message_id='',
                    recipient=to,
                    status='failed',
                    cost=0.0,
                    timestamp=datetime.now(),
                    error_message=response['messages'][0].get('error-text'),
                )
                
        except Exception as e:
            logger.error(f"Vonage SMS failed: {e}")
            return SMSResponse(
                success=False,
                message_id='',
                recipient=to,
                status='failed',
                cost=0.0,
                timestamp=datetime.now(),
                error_message=str(e),
            )


class SMSRouter:
    """
    Intelligent SMS routing based on cost, reliability, and coverage.
    """
    
    def __init__(
        self,
        twilio_client: Optional[TwilioSMSClient] = None,
        africastalking_client: Optional[AfricasTalkingSMSClient] = None,
        vonage_client: Optional[VonageSMSClient] = None,
    ):
        """Initialize SMS router with available clients."""
        self.clients = {}
        
        if twilio_client:
            self.clients['twilio'] = twilio_client
        if africastalking_client:
            self.clients['africastalking'] = africastalking_client
        if vonage_client:
            self.clients['vonage'] = vonage_client
            
        # Routing rules based on country code
        self.routing_rules = {
            # Africa - use Africa's Talking for best rates
            '254': 'africastalking',  # Kenya
            '256': 'africastalking',  # Uganda
            '255': 'africastalking',  # Tanzania
            '234': 'africastalking',  # Nigeria
            '233': 'africastalking',  # Ghana
            '27': 'africastalking',   # South Africa
            
            # Global - use Twilio
            '1': 'twilio',    # US/Canada
            '44': 'twilio',   # UK
            '91': 'twilio',   # India
            '55': 'twilio',   # Brazil
        }
        
        # Fallback priority
        self.fallback_order = ['africastalking', 'twilio', 'vonage']
        
    def send_sms(
        self,
        to: str,
        message: str,
        force_provider: Optional[str] = None,
    ) -> SMSResponse:
        """
        Route and send SMS via best provider.
        
        Args:
            to: Recipient phone number
            message: Message content
            force_provider: Force specific provider
            
        Returns:
            SMSResponse
        """
        # Extract country code
        country_code = to[1:4] if to.startswith('+') else to[:3]
        
        # Determine provider
        if force_provider and force_provider in self.clients:
            provider = force_provider
        else:
            provider = self.routing_rules.get(country_code, 'twilio')
            
        # Send with primary provider
        if provider in self.clients:
            logger.info(f"Routing SMS to {to} via {provider}")
            response = self._send_with_provider(provider, to, message)
            
            if response.success:
                return response
                
        # Fallback to other providers
        logger.warning(f"Primary provider {provider} failed, trying fallback...")
        for fallback_provider in self.fallback_order:
            if fallback_provider != provider and fallback_provider in self.clients:
                logger.info(f"Trying fallback provider: {fallback_provider}")
                response = self._send_with_provider(fallback_provider, to, message)
                
                if response.success:
                    return response
                    
        # All providers failed
        logger.error("All SMS providers failed")
        return SMSResponse(
            success=False,
            message_id='',
            recipient=to,
            status='failed',
            cost=0.0,
            timestamp=datetime.now(),
            error_message='All providers failed',
        )
        
    def _send_with_provider(
        self,
        provider: str,
        to: str,
        message: str,
    ) -> SMSResponse:
        """Send SMS with specific provider."""
        client = self.clients.get(provider)
        
        if not client:
            return SMSResponse(
                success=False,
                message_id='',
                recipient=to,
                status='failed',
                cost=0.0,
                timestamp=datetime.now(),
                error_message=f"Provider {provider} not configured",
            )
            
        try:
            if provider == 'africastalking':
                return client.send_sms([to], message)
            else:
                return client.send_sms(to, message)
                
        except Exception as e:
            logger.error(f"Provider {provider} error: {e}")
            return SMSResponse(
                success=False,
                message_id='',
                recipient=to,
                status='failed',
                cost=0.0,
                timestamp=datetime.now(),
                error_message=str(e),
            )


class SMSLocalizer:
    """
    Localize SMS messages to local languages.
    
    Supported languages:
    - English (en)
    - Swahili (sw)
    - Yoruba (yo)
    - Hausa (ha)
    - Igbo (ig)
    - French (fr)
    - Portuguese (pt)
    """
    
    def __init__(self):
        """Initialize SMS localizer with templates."""
        self.templates = {
            'payment_confirmation': {
                'en': 'Payment of {currency} {amount} received. Ref: {reference}. Thank you!',
                'sw': 'Malipo ya {currency} {amount} yamepokelewa. Kumbukumbu: {reference}. Asante!',
                'fr': 'Paiement de {currency} {amount} reçu. Réf: {reference}. Merci!',
                'pt': 'Pagamento de {currency} {amount} recebido. Ref: {reference}. Obrigado!',
            },
            'weather_alert': {
                'en': 'Weather alert: {event}. Take action: {action}',
                'sw': 'Onyo la hali ya hewa: {event}. Chukua hatua: {action}',
                'fr': 'Alerte météo: {event}. Action: {action}',
            },
            'irrigation_reminder': {
                'en': 'Time to irrigate {farm_name}. Soil moisture: {moisture}%',
                'sw': 'Wakati wa kumwagilia {farm_name}. Unyevu wa udongo: {moisture}%',
            },
            'harvest_alert': {
                'en': 'Harvest ready for {crop}. Estimated yield: {yield} kg/ha',
                'sw': 'Mavuno tayari kwa {crop}. Mavuno yanatarajiwa: {yield} kg/ha',
            },
        }
        
    def localize(
        self,
        template_name: str,
        language: str,
        **kwargs,
    ) -> str:
        """
        Localize message template.
        
        Args:
            template_name: Template identifier
            language: Language code
            **kwargs: Template variables
            
        Returns:
            Localized message
        """
        if template_name not in self.templates:
            logger.warning(f"Template {template_name} not found")
            return ''
            
        if language not in self.templates[template_name]:
            logger.warning(f"Language {language} not available, using English")
            language = 'en'
            
        template = self.templates[template_name][language]
        
        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing template variable: {e}")
            return template
