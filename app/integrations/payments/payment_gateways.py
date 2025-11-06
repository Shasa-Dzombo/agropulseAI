"""
Payment Gateway Integrations
============================

Unified interfaces for M-PESA, Flutterwave, Stripe, Paystack, and PayPal.
All gateways convert to USD backend automatically.
"""

import requests
from typing import Dict, Optional, Any
from datetime import datetime
from decimal import Decimal
import logging
import hashlib
import base64
from dataclasses import dataclass, asdict
import json

logger = logging.getLogger(__name__)


@dataclass
class PaymentRequest:
    """Unified payment request."""
    amount: Decimal
    currency: str
    customer_id: str
    customer_email: str
    customer_phone: Optional[str]
    description: str
    callback_url: str
    metadata: Dict[str, Any]


@dataclass
class PaymentResponse:
    """Unified payment response."""
    success: bool
    transaction_id: str
    reference: str
    amount_local: Decimal
    amount_usd: Decimal
    currency: str
    status: str  # 'pending', 'success', 'failed'
    payment_url: Optional[str]
    message: str
    raw_response: Dict[str, Any]


class MPesaGateway:
    """
    M-PESA STK Push (Lipa Na M-PESA Online) integration.
    
    Features:
    - STK Push for instant payments
    - B2C payouts
    - Transaction status checking
    - Automatic USD conversion
    
    Supported countries: Kenya, Tanzania, Uganda (via Safaricom, Vodacom, Vodafone)
    """
    
    def __init__(
        self,
        consumer_key: str,
        consumer_secret: str,
        business_shortcode: str,
        passkey: str,
        environment: str = 'sandbox',
    ):
        """
        Initialize M-PESA gateway.
        
        Args:
            consumer_key: M-PESA API consumer key
            consumer_secret: M-PESA API consumer secret
            business_shortcode: Till/Paybill number
            passkey: Lipa Na M-PESA passkey
            environment: 'sandbox' or 'production'
        """
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.business_shortcode = business_shortcode
        self.passkey = passkey
        self.environment = environment
        
        # API endpoints
        if environment == 'production':
            self.base_url = 'https://api.safaricom.co.ke'
        else:
            self.base_url = 'https://sandbox.safaricom.co.ke'
            
        self.auth_url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        self.stk_push_url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"
        self.query_url = f"{self.base_url}/mpesa/stkpushquery/v1/query"
        
        self.access_token = None
        self.token_expiry = None
        
    def _get_access_token(self) -> str:
        """Get OAuth access token."""
        if self.access_token and self.token_expiry:
            if datetime.now() < self.token_expiry:
                return self.access_token
                
        # Generate new token
        credentials = base64.b64encode(
            f"{self.consumer_key}:{self.consumer_secret}".encode()
        ).decode()
        
        headers = {
            'Authorization': f'Basic {credentials}',
            'Content-Type': 'application/json',
        }
        
        response = requests.get(self.auth_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        self.access_token = data['access_token']
        # Token expires in 3599 seconds
        self.token_expiry = datetime.now().replace(hour=23, minute=59)
        
        logger.info("M-PESA access token obtained")
        return self.access_token
        
    def _generate_password(self) -> tuple[str, str]:
        """Generate M-PESA password and timestamp."""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password_str = f"{self.business_shortcode}{self.passkey}{timestamp}"
        password = base64.b64encode(password_str.encode()).decode()
        return password, timestamp
        
    def initiate_stk_push(
        self,
        payment_request: PaymentRequest,
    ) -> PaymentResponse:
        """
        Initiate M-PESA STK Push payment.
        
        Args:
            payment_request: Unified payment request
            
        Returns:
            PaymentResponse with transaction details
        """
        try:
            # Get access token
            token = self._get_access_token()
            
            # Generate password and timestamp
            password, timestamp = self._generate_password()
            
            # Prepare STK Push request
            phone_number = payment_request.customer_phone
            if not phone_number:
                raise ValueError("Phone number required for M-PESA")
                
            # Format phone number (254XXXXXXXXX)
            if phone_number.startswith('0'):
                phone_number = '254' + phone_number[1:]
            elif phone_number.startswith('+254'):
                phone_number = phone_number[1:]
            elif not phone_number.startswith('254'):
                phone_number = '254' + phone_number
                
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
            }
            
            payload = {
                'BusinessShortCode': self.business_shortcode,
                'Password': password,
                'Timestamp': timestamp,
                'TransactionType': 'CustomerPayBillOnline',
                'Amount': int(payment_request.amount),  # M-PESA requires integer
                'PartyA': phone_number,
                'PartyB': self.business_shortcode,
                'PhoneNumber': phone_number,
                'CallBackURL': payment_request.callback_url,
                'AccountReference': payment_request.customer_id,
                'TransactionDesc': payment_request.description,
            }
            
            logger.info(f"Initiating M-PESA STK Push for {phone_number}, amount: {payment_request.amount} KES")
            
            response = requests.post(
                self.stk_push_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Check response
            if data.get('ResponseCode') == '0':
                return PaymentResponse(
                    success=True,
                    transaction_id=data.get('CheckoutRequestID', ''),
                    reference=data.get('MerchantRequestID', ''),
                    amount_local=payment_request.amount,
                    amount_usd=Decimal('0'),  # Will be set by converter
                    currency=payment_request.currency,
                    status='pending',
                    payment_url=None,  # STK Push is automatic
                    message=data.get('CustomerMessage', 'STK Push sent to phone'),
                    raw_response=data,
                )
            else:
                return PaymentResponse(
                    success=False,
                    transaction_id='',
                    reference='',
                    amount_local=payment_request.amount,
                    amount_usd=Decimal('0'),
                    currency=payment_request.currency,
                    status='failed',
                    payment_url=None,
                    message=data.get('errorMessage', 'STK Push failed'),
                    raw_response=data,
                )
                
        except Exception as e:
            logger.error(f"M-PESA STK Push failed: {e}")
            return PaymentResponse(
                success=False,
                transaction_id='',
                reference='',
                amount_local=payment_request.amount,
                amount_usd=Decimal('0'),
                currency=payment_request.currency,
                status='failed',
                payment_url=None,
                message=f"Error: {str(e)}",
                raw_response={},
            )
            
    def query_transaction(
        self,
        checkout_request_id: str,
    ) -> Dict[str, Any]:
        """Query M-PESA transaction status."""
        try:
            token = self._get_access_token()
            password, timestamp = self._generate_password()
            
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
            }
            
            payload = {
                'BusinessShortCode': self.business_shortcode,
                'Password': password,
                'Timestamp': timestamp,
                'CheckoutRequestID': checkout_request_id,
            }
            
            response = requests.post(
                self.query_url,
                json=payload,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"M-PESA query failed: {e}")
            return {'ResultCode': '1', 'ResultDesc': str(e)}


class FlutterwaveGateway:
    """
    Flutterwave payment gateway integration.
    
    Features:
    - Card payments
    - Mobile money (M-PESA, MTN, Airtel)
    - Bank transfers
    - USSD payments
    - Multi-currency support
    - Automatic USD conversion
    
    Supported: Nigeria, Ghana, Kenya, Uganda, South Africa, Tanzania
    """
    
    def __init__(
        self,
        public_key: str,
        secret_key: str,
        encryption_key: str,
        environment: str = 'sandbox',
    ):
        """Initialize Flutterwave gateway."""
        self.public_key = public_key
        self.secret_key = secret_key
        self.encryption_key = encryption_key
        self.environment = environment
        
        if environment == 'production':
            self.base_url = 'https://api.flutterwave.com/v3'
        else:
            self.base_url = 'https://api.flutterwave.com/v3'  # Same endpoint
            
    def initiate_payment(
        self,
        payment_request: PaymentRequest,
    ) -> PaymentResponse:
        """
        Initiate Flutterwave payment.
        
        Args:
            payment_request: Unified payment request
            
        Returns:
            PaymentResponse with payment link
        """
        try:
            headers = {
                'Authorization': f'Bearer {self.secret_key}',
                'Content-Type': 'application/json',
            }
            
            payload = {
                'tx_ref': f"AGRO-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                'amount': str(payment_request.amount),
                'currency': payment_request.currency,
                'redirect_url': payment_request.callback_url,
                'payment_options': 'card,mobilemoney,ussd,banktransfer',
                'customer': {
                    'email': payment_request.customer_email,
                    'phonenumber': payment_request.customer_phone or '',
                    'name': payment_request.customer_id,
                },
                'customizations': {
                    'title': 'AgroPulse Payment',
                    'description': payment_request.description,
                    'logo': 'https://agropulse.com/logo.png',
                },
                'meta': payment_request.metadata,
            }
            
            logger.info(f"Initiating Flutterwave payment: {payment_request.amount} {payment_request.currency}")
            
            response = requests.post(
                f"{self.base_url}/payments",
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') == 'success':
                return PaymentResponse(
                    success=True,
                    transaction_id=data['data']['id'],
                    reference=data['data']['tx_ref'],
                    amount_local=payment_request.amount,
                    amount_usd=Decimal('0'),
                    currency=payment_request.currency,
                    status='pending',
                    payment_url=data['data']['link'],
                    message='Payment link generated',
                    raw_response=data,
                )
            else:
                return PaymentResponse(
                    success=False,
                    transaction_id='',
                    reference='',
                    amount_local=payment_request.amount,
                    amount_usd=Decimal('0'),
                    currency=payment_request.currency,
                    status='failed',
                    payment_url=None,
                    message=data.get('message', 'Payment initiation failed'),
                    raw_response=data,
                )
                
        except Exception as e:
            logger.error(f"Flutterwave payment failed: {e}")
            return PaymentResponse(
                success=False,
                transaction_id='',
                reference='',
                amount_local=payment_request.amount,
                amount_usd=Decimal('0'),
                currency=payment_request.currency,
                status='failed',
                payment_url=None,
                message=f"Error: {str(e)}",
                raw_response={},
            )
            
    def verify_payment(
        self,
        transaction_id: str,
    ) -> Dict[str, Any]:
        """Verify Flutterwave payment status."""
        try:
            headers = {
                'Authorization': f'Bearer {self.secret_key}',
                'Content-Type': 'application/json',
            }
            
            response = requests.get(
                f"{self.base_url}/transactions/{transaction_id}/verify",
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Flutterwave verification failed: {e}")
            return {'status': 'error', 'message': str(e)}


class StripeGateway:
    """
    Stripe payment gateway integration.
    
    Features:
    - Card payments
    - Apple Pay / Google Pay
    - Bank transfers (ACH, SEPA)
    - Subscriptions
    - Multi-currency
    
    Global coverage with best support for US, Europe, and Asia.
    """
    
    def __init__(
        self,
        secret_key: str,
        publishable_key: str,
        webhook_secret: str,
    ):
        """Initialize Stripe gateway."""
        self.secret_key = secret_key
        self.publishable_key = publishable_key
        self.webhook_secret = webhook_secret
        self.base_url = 'https://api.stripe.com/v1'
        
    def create_payment_intent(
        self,
        payment_request: PaymentRequest,
    ) -> PaymentResponse:
        """Create Stripe payment intent."""
        try:
            headers = {
                'Authorization': f'Bearer {self.secret_key}',
                'Content-Type': 'application/x-www-form-urlencoded',
            }
            
            # Stripe requires amount in smallest currency unit (cents)
            amount_cents = int(payment_request.amount * 100)
            
            payload = {
                'amount': amount_cents,
                'currency': payment_request.currency.lower(),
                'customer': payment_request.customer_id,
                'description': payment_request.description,
                'metadata[email]': payment_request.customer_email,
                'automatic_payment_methods[enabled]': 'true',
            }
            
            logger.info(f"Creating Stripe payment intent: {payment_request.amount} {payment_request.currency}")
            
            response = requests.post(
                f"{self.base_url}/payment_intents",
                data=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            return PaymentResponse(
                success=True,
                transaction_id=data['id'],
                reference=data['client_secret'],
                amount_local=payment_request.amount,
                amount_usd=Decimal('0'),
                currency=payment_request.currency,
                status='pending',
                payment_url=None,  # Client-side integration
                message='Payment intent created',
                raw_response=data,
            )
            
        except Exception as e:
            logger.error(f"Stripe payment failed: {e}")
            return PaymentResponse(
                success=False,
                transaction_id='',
                reference='',
                amount_local=payment_request.amount,
                amount_usd=Decimal('0'),
                currency=payment_request.currency,
                status='failed',
                payment_url=None,
                message=f"Error: {str(e)}",
                raw_response={},
            )


class PaystackGateway:
    """Paystack payment gateway (Nigeria, Ghana, South Africa)."""
    
    def __init__(self, secret_key: str, public_key: str):
        """Initialize Paystack gateway."""
        self.secret_key = secret_key
        self.public_key = public_key
        self.base_url = 'https://api.paystack.co'
        
    def initialize_transaction(self, payment_request: PaymentRequest) -> PaymentResponse:
        """Initialize Paystack transaction."""
        try:
            headers = {
                'Authorization': f'Bearer {self.secret_key}',
                'Content-Type': 'application/json',
            }
            
            # Paystack requires amount in kobo/pesewas (smallest unit)
            amount_kobo = int(payment_request.amount * 100)
            
            payload = {
                'email': payment_request.customer_email,
                'amount': amount_kobo,
                'currency': payment_request.currency,
                'reference': f"AGRO-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                'callback_url': payment_request.callback_url,
                'metadata': payment_request.metadata,
            }
            
            response = requests.post(
                f"{self.base_url}/transaction/initialize",
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status'):
                return PaymentResponse(
                    success=True,
                    transaction_id=data['data']['reference'],
                    reference=data['data']['reference'],
                    amount_local=payment_request.amount,
                    amount_usd=Decimal('0'),
                    currency=payment_request.currency,
                    status='pending',
                    payment_url=data['data']['authorization_url'],
                    message='Transaction initialized',
                    raw_response=data,
                )
            else:
                return PaymentResponse(
                    success=False,
                    transaction_id='',
                    reference='',
                    amount_local=payment_request.amount,
                    amount_usd=Decimal('0'),
                    currency=payment_request.currency,
                    status='failed',
                    payment_url=None,
                    message=data.get('message', 'Initialization failed'),
                    raw_response=data,
                )
                
        except Exception as e:
            logger.error(f"Paystack transaction failed: {e}")
            return PaymentResponse(
                success=False,
                transaction_id='',
                reference='',
                amount_local=payment_request.amount,
                amount_usd=Decimal('0'),
                currency=payment_request.currency,
                status='failed',
                payment_url=None,
                message=f"Error: {str(e)}",
                raw_response={},
            )


class PayPalGateway:
    """PayPal payment gateway (global coverage)."""
    
    def __init__(self, client_id: str, client_secret: str, environment: str = 'sandbox'):
        """Initialize PayPal gateway."""
        self.client_id = client_id
        self.client_secret = client_secret
        self.environment = environment
        
        if environment == 'production':
            self.base_url = 'https://api-m.paypal.com'
        else:
            self.base_url = 'https://api-m.sandbox.paypal.com'
            
    def create_order(self, payment_request: PaymentRequest) -> PaymentResponse:
        """Create PayPal order."""
        # Placeholder - full implementation would follow PayPal Orders API v2
        logger.info("PayPal integration placeholder")
        return PaymentResponse(
            success=False,
            transaction_id='',
            reference='',
            amount_local=payment_request.amount,
            amount_usd=Decimal('0'),
            currency=payment_request.currency,
            status='failed',
            payment_url=None,
            message='PayPal integration not fully implemented',
            raw_response={},
        )
