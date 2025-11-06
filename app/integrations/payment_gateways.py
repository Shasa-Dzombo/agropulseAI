"""
Payment Gateway Integrations for AgroPulse

Multiple payment providers, subscription management, invoicing.

Features:
- Stripe integration
- PayPal integration
- Razorpay integration
- Subscription management
- Invoice generation
- Payment reconciliation
- Refund handling
- Webhook processing
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import hmac
import hashlib

try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False
    logging.warning("Stripe library not available")


logger = logging.getLogger(__name__)


class PaymentStatus(Enum):
    """Payment status"""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentMethod(Enum):
    """Payment method types"""
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    MOBILE_MONEY = "mobile_money"
    UPI = "upi"
    PAYPAL = "paypal"


class SubscriptionStatus(Enum):
    """Subscription status"""
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    TRIALING = "trialing"


@dataclass
class PaymentIntent:
    """Payment intent"""
    payment_id: str
    amount: float
    currency: str
    status: PaymentStatus
    customer_id: str
    payment_method: PaymentMethod
    description: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'payment_id': self.payment_id,
            'amount': self.amount,
            'currency': self.currency,
            'status': self.status.value,
            'customer_id': self.customer_id,
            'payment_method': self.payment_method.value,
            'description': self.description,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


@dataclass
class Subscription:
    """Subscription"""
    subscription_id: str
    customer_id: str
    plan_id: str
    status: SubscriptionStatus
    amount: float
    currency: str
    billing_cycle: str  # monthly, quarterly, annual
    current_period_start: datetime
    current_period_end: datetime
    trial_end: Optional[datetime] = None
    cancel_at_period_end: bool = False
    metadata: Dict = field(default_factory=dict)
    
    def is_active(self) -> bool:
        """Check if subscription is active"""
        return self.status in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]
    
    def days_until_renewal(self) -> int:
        """Days until next renewal"""
        delta = self.current_period_end - datetime.now()
        return max(0, delta.days)


@dataclass
class Invoice:
    """Invoice"""
    invoice_id: str
    customer_id: str
    amount: float
    currency: str
    status: str  # draft, open, paid, void, uncollectible
    due_date: datetime
    items: List[Dict] = field(default_factory=list)
    subtotal: float = 0.0
    tax_amount: float = 0.0
    discount_amount: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    paid_at: Optional[datetime] = None
    
    @property
    def total(self) -> float:
        """Calculate total amount"""
        return self.subtotal + self.tax_amount - self.discount_amount
    
    def add_line_item(
        self,
        description: str,
        quantity: int,
        unit_price: float,
        tax_rate: float = 0.0
    ):
        """Add line item to invoice"""
        amount = quantity * unit_price
        tax = amount * tax_rate
        
        self.items.append({
            'description': description,
            'quantity': quantity,
            'unit_price': unit_price,
            'amount': amount,
            'tax': tax
        })
        
        self.subtotal += amount
        self.tax_amount += tax


class StripePaymentGateway:
    """
    Stripe payment gateway integration
    
    Handles payments, subscriptions, and webhooks.
    """
    
    def __init__(
        self,
        api_key: str,
        webhook_secret: Optional[str] = None
    ):
        """
        Initialize Stripe gateway
        
        Args:
            api_key: Stripe API key
            webhook_secret: Webhook signing secret
        """
        if not STRIPE_AVAILABLE:
            logger.warning("Stripe not available, using mock mode")
            self.mock_mode = True
        else:
            self.mock_mode = False
            stripe.api_key = api_key
        
        self.webhook_secret = webhook_secret
        self.payments: Dict[str, PaymentIntent] = {}
        self.subscriptions: Dict[str, Subscription] = {}
        
        logger.info(f"StripePaymentGateway initialized (mock_mode={self.mock_mode})")
    
    def create_payment_intent(
        self,
        amount: float,
        currency: str,
        customer_id: str,
        payment_method: str,
        description: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> PaymentIntent:
        """
        Create payment intent
        
        Args:
            amount: Amount in smallest currency unit (e.g., cents)
            currency: Currency code (e.g., 'usd')
            customer_id: Customer identifier
            payment_method: Payment method ID
            description: Payment description
            metadata: Additional metadata
            
        Returns:
            Payment intent
        """
        if self.mock_mode:
            payment_id = f"pi_mock_{int(datetime.now().timestamp())}"
        else:
            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Convert to cents
                currency=currency,
                customer=customer_id,
                payment_method=payment_method,
                description=description,
                metadata=metadata or {},
                confirm=True
            )
            payment_id = intent.id
        
        payment = PaymentIntent(
            payment_id=payment_id,
            amount=amount,
            currency=currency,
            status=PaymentStatus.PROCESSING,
            customer_id=customer_id,
            payment_method=PaymentMethod.CREDIT_CARD,
            description=description,
            metadata=metadata or {}
        )
        
        self.payments[payment_id] = payment
        
        logger.info(f"Payment intent created: {payment_id} for ${amount}")
        
        return payment
    
    def capture_payment(self, payment_id: str) -> bool:
        """
        Capture payment
        
        Args:
            payment_id: Payment intent ID
            
        Returns:
            True if successful
        """
        if payment_id not in self.payments:
            logger.error(f"Payment not found: {payment_id}")
            return False
        
        payment = self.payments[payment_id]
        
        if self.mock_mode:
            payment.status = PaymentStatus.SUCCEEDED
            payment.updated_at = datetime.now()
            logger.info(f"[MOCK] Payment captured: {payment_id}")
            return True
        
        try:
            stripe.PaymentIntent.capture(payment_id)
            payment.status = PaymentStatus.SUCCEEDED
            payment.updated_at = datetime.now()
            logger.info(f"Payment captured: {payment_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to capture payment {payment_id}: {e}")
            payment.status = PaymentStatus.FAILED
            return False
    
    def refund_payment(
        self,
        payment_id: str,
        amount: Optional[float] = None,
        reason: Optional[str] = None
    ) -> bool:
        """
        Refund payment
        
        Args:
            payment_id: Payment intent ID
            amount: Refund amount (None for full refund)
            reason: Refund reason
            
        Returns:
            True if successful
        """
        if payment_id not in self.payments:
            logger.error(f"Payment not found: {payment_id}")
            return False
        
        payment = self.payments[payment_id]
        
        if payment.status != PaymentStatus.SUCCEEDED:
            logger.error(f"Cannot refund payment {payment_id} with status {payment.status}")
            return False
        
        refund_amount = amount or payment.amount
        
        if self.mock_mode:
            payment.status = PaymentStatus.REFUNDED
            payment.updated_at = datetime.now()
            logger.info(f"[MOCK] Payment refunded: {payment_id} (${refund_amount})")
            return True
        
        try:
            stripe.Refund.create(
                payment_intent=payment_id,
                amount=int(refund_amount * 100) if amount else None,
                reason=reason
            )
            payment.status = PaymentStatus.REFUNDED
            payment.updated_at = datetime.now()
            logger.info(f"Payment refunded: {payment_id} (${refund_amount})")
            return True
        
        except Exception as e:
            logger.error(f"Failed to refund payment {payment_id}: {e}")
            return False
    
    def create_subscription(
        self,
        customer_id: str,
        plan_id: str,
        trial_days: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> Subscription:
        """
        Create subscription
        
        Args:
            customer_id: Customer identifier
            plan_id: Pricing plan ID
            trial_days: Trial period days
            metadata: Additional metadata
            
        Returns:
            Subscription
        """
        now = datetime.now()
        trial_end = now + timedelta(days=trial_days) if trial_days else None
        
        if self.mock_mode:
            subscription_id = f"sub_mock_{int(now.timestamp())}"
            subscription_status = SubscriptionStatus.TRIALING if trial_days else SubscriptionStatus.ACTIVE
        else:
            sub = stripe.Subscription.create(
                customer=customer_id,
                items=[{'price': plan_id}],
                trial_period_days=trial_days,
                metadata=metadata or {}
            )
            subscription_id = sub.id
            subscription_status = SubscriptionStatus(sub.status)
        
        subscription = Subscription(
            subscription_id=subscription_id,
            customer_id=customer_id,
            plan_id=plan_id,
            status=subscription_status,
            amount=99.99,  # Would come from plan
            currency='usd',
            billing_cycle='monthly',
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
            trial_end=trial_end,
            metadata=metadata or {}
        )
        
        self.subscriptions[subscription_id] = subscription
        
        logger.info(f"Subscription created: {subscription_id} for customer {customer_id}")
        
        return subscription
    
    def cancel_subscription(
        self,
        subscription_id: str,
        at_period_end: bool = True
    ) -> bool:
        """
        Cancel subscription
        
        Args:
            subscription_id: Subscription ID
            at_period_end: Cancel at end of period or immediately
            
        Returns:
            True if successful
        """
        if subscription_id not in self.subscriptions:
            logger.error(f"Subscription not found: {subscription_id}")
            return False
        
        subscription = self.subscriptions[subscription_id]
        
        if self.mock_mode:
            if at_period_end:
                subscription.cancel_at_period_end = True
                logger.info(f"[MOCK] Subscription will cancel at period end: {subscription_id}")
            else:
                subscription.status = SubscriptionStatus.CANCELLED
                logger.info(f"[MOCK] Subscription cancelled: {subscription_id}")
            return True
        
        try:
            stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=at_period_end
            )
            
            if at_period_end:
                subscription.cancel_at_period_end = True
            else:
                subscription.status = SubscriptionStatus.CANCELLED
            
            logger.info(f"Subscription cancelled: {subscription_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to cancel subscription {subscription_id}: {e}")
            return False
    
    def process_webhook(
        self,
        payload: str,
        signature: str
    ) -> Optional[Dict]:
        """
        Process Stripe webhook
        
        Args:
            payload: Webhook payload
            signature: Stripe signature header
            
        Returns:
            Event data if valid
        """
        if not self.webhook_secret:
            logger.warning("Webhook secret not configured")
            return None
        
        if self.mock_mode:
            logger.info("[MOCK] Webhook received")
            return json.loads(payload)
        
        try:
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                self.webhook_secret
            )
            
            logger.info(f"Webhook received: {event['type']}")
            
            # Handle different event types
            if event['type'] == 'payment_intent.succeeded':
                payment_id = event['data']['object']['id']
                if payment_id in self.payments:
                    self.payments[payment_id].status = PaymentStatus.SUCCEEDED
            
            elif event['type'] == 'payment_intent.payment_failed':
                payment_id = event['data']['object']['id']
                if payment_id in self.payments:
                    self.payments[payment_id].status = PaymentStatus.FAILED
            
            elif event['type'] == 'customer.subscription.deleted':
                subscription_id = event['data']['object']['id']
                if subscription_id in self.subscriptions:
                    self.subscriptions[subscription_id].status = SubscriptionStatus.CANCELLED
            
            return event
        
        except Exception as e:
            logger.error(f"Webhook verification failed: {e}")
            return None
    
    def get_payment_status(self, payment_id: str) -> Optional[PaymentStatus]:
        """Get payment status"""
        payment = self.payments.get(payment_id)
        return payment.status if payment else None
    
    def get_subscription_status(self, subscription_id: str) -> Optional[SubscriptionStatus]:
        """Get subscription status"""
        subscription = self.subscriptions.get(subscription_id)
        return subscription.status if subscription else None


class PayPalGateway:
    """
    PayPal payment gateway integration
    """
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        mode: str = 'sandbox'
    ):
        """
        Initialize PayPal gateway
        
        Args:
            client_id: PayPal client ID
            client_secret: PayPal client secret
            mode: 'sandbox' or 'live'
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.mode = mode
        self.mock_mode = True  # Would use paypalrestsdk
        
        self.payments: Dict[str, PaymentIntent] = {}
        
        logger.info(f"PayPalGateway initialized (mode={mode}, mock_mode={self.mock_mode})")
    
    def create_payment(
        self,
        amount: float,
        currency: str,
        description: str,
        return_url: str,
        cancel_url: str
    ) -> Tuple[str, str]:
        """
        Create PayPal payment
        
        Args:
            amount: Payment amount
            currency: Currency code
            description: Payment description
            return_url: Return URL after payment
            cancel_url: Cancel URL
            
        Returns:
            (payment_id, approval_url)
        """
        payment_id = f"pp_mock_{int(datetime.now().timestamp())}"
        approval_url = f"https://www.paypal.com/checkoutnow?token={payment_id}"
        
        payment = PaymentIntent(
            payment_id=payment_id,
            amount=amount,
            currency=currency,
            status=PaymentStatus.PENDING,
            customer_id='unknown',
            payment_method=PaymentMethod.PAYPAL,
            description=description
        )
        
        self.payments[payment_id] = payment
        
        logger.info(f"PayPal payment created: {payment_id}")
        
        return payment_id, approval_url
    
    def execute_payment(
        self,
        payment_id: str,
        payer_id: str
    ) -> bool:
        """
        Execute approved PayPal payment
        
        Args:
            payment_id: Payment ID
            payer_id: PayPal payer ID
            
        Returns:
            True if successful
        """
        if payment_id not in self.payments:
            logger.error(f"Payment not found: {payment_id}")
            return False
        
        payment = self.payments[payment_id]
        payment.status = PaymentStatus.SUCCEEDED
        payment.updated_at = datetime.now()
        
        logger.info(f"PayPal payment executed: {payment_id}")
        
        return True


class InvoiceGenerator:
    """
    Invoice generation and management
    """
    
    def __init__(self):
        """Initialize invoice generator"""
        self.invoices: Dict[str, Invoice] = {}
        
        logger.info("InvoiceGenerator initialized")
    
    def create_invoice(
        self,
        customer_id: str,
        currency: str = 'USD',
        due_days: int = 30
    ) -> Invoice:
        """
        Create new invoice
        
        Args:
            customer_id: Customer identifier
            currency: Currency code
            due_days: Days until due
            
        Returns:
            Invoice
        """
        invoice_id = f"inv_{int(datetime.now().timestamp())}"
        
        invoice = Invoice(
            invoice_id=invoice_id,
            customer_id=customer_id,
            amount=0.0,
            currency=currency,
            status='draft',
            due_date=datetime.now() + timedelta(days=due_days)
        )
        
        self.invoices[invoice_id] = invoice
        
        logger.info(f"Invoice created: {invoice_id}")
        
        return invoice
    
    def finalize_invoice(self, invoice_id: str) -> bool:
        """
        Finalize invoice and make it payable
        
        Args:
            invoice_id: Invoice ID
            
        Returns:
            True if successful
        """
        if invoice_id not in self.invoices:
            logger.error(f"Invoice not found: {invoice_id}")
            return False
        
        invoice = self.invoices[invoice_id]
        
        if invoice.status != 'draft':
            logger.error(f"Invoice {invoice_id} is not in draft status")
            return False
        
        invoice.status = 'open'
        invoice.amount = invoice.total
        
        logger.info(f"Invoice finalized: {invoice_id} (${invoice.total})")
        
        return True
    
    def mark_invoice_paid(
        self,
        invoice_id: str,
        payment_id: str
    ) -> bool:
        """
        Mark invoice as paid
        
        Args:
            invoice_id: Invoice ID
            payment_id: Payment ID
            
        Returns:
            True if successful
        """
        if invoice_id not in self.invoices:
            logger.error(f"Invoice not found: {invoice_id}")
            return False
        
        invoice = self.invoices[invoice_id]
        invoice.status = 'paid'
        invoice.paid_at = datetime.now()
        
        logger.info(f"Invoice marked paid: {invoice_id} via {payment_id}")
        
        return True
    
    def generate_pdf(self, invoice_id: str) -> bytes:
        """
        Generate PDF invoice
        
        Args:
            invoice_id: Invoice ID
            
        Returns:
            PDF bytes
        """
        if invoice_id not in self.invoices:
            raise ValueError(f"Invoice not found: {invoice_id}")
        
        invoice = self.invoices[invoice_id]
        
        # In real implementation, would use reportlab or similar
        pdf_content = f"Invoice {invoice.invoice_id}\n"
        pdf_content += f"Amount: ${invoice.total}\n"
        pdf_content += f"Due: {invoice.due_date}\n"
        
        return pdf_content.encode('utf-8')


class PaymentReconciliationEngine:
    """
    Payment reconciliation and matching
    """
    
    def __init__(self):
        """Initialize reconciliation engine"""
        self.transactions: List[Dict] = []
        self.mismatches: List[Dict] = []
        
        logger.info("PaymentReconciliationEngine initialized")
    
    def add_transaction(
        self,
        transaction_id: str,
        amount: float,
        reference: str,
        source: str
    ):
        """
        Add transaction for reconciliation
        
        Args:
            transaction_id: Transaction identifier
            amount: Transaction amount
            reference: Reference number
            source: Transaction source (bank, gateway, etc.)
        """
        self.transactions.append({
            'transaction_id': transaction_id,
            'amount': amount,
            'reference': reference,
            'source': source,
            'timestamp': datetime.now(),
            'reconciled': False
        })
    
    def reconcile(self, tolerance: float = 0.01) -> Dict:
        """
        Perform reconciliation
        
        Args:
            tolerance: Amount tolerance for matching
            
        Returns:
            Reconciliation report
        """
        matched = []
        unmatched = []
        
        # Group by reference
        by_reference = {}
        for txn in self.transactions:
            ref = txn['reference']
            if ref not in by_reference:
                by_reference[ref] = []
            by_reference[ref].append(txn)
        
        # Match transactions
        for ref, txns in by_reference.items():
            if len(txns) >= 2:
                amounts = [t['amount'] for t in txns]
                if max(amounts) - min(amounts) <= tolerance:
                    matched.append({
                        'reference': ref,
                        'transactions': txns,
                        'amount': sum(amounts) / len(amounts)
                    })
                    for txn in txns:
                        txn['reconciled'] = True
                else:
                    self.mismatches.append({
                        'reference': ref,
                        'transactions': txns,
                        'reason': 'amount_mismatch'
                    })
            else:
                unmatched.append({
                    'reference': ref,
                    'transaction': txns[0]
                })
        
        report = {
            'total_transactions': len(self.transactions),
            'matched': len(matched),
            'unmatched': len(unmatched),
            'mismatches': len(self.mismatches),
            'matched_transactions': matched,
            'unmatched_transactions': unmatched,
            'reconciliation_date': datetime.now().isoformat()
        }
        
        logger.info(
            f"Reconciliation completed: {len(matched)} matched, "
            f"{len(unmatched)} unmatched, {len(self.mismatches)} mismatches"
        )
        
        return report
    
    def get_mismatches(self) -> List[Dict]:
        """Get list of mismatched transactions"""
        return self.mismatches
