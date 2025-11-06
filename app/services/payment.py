import httpx
from typing import Optional
from app.config import settings
from datetime import datetime
import hashlib
import json


class FlutterwaveService:
    def __init__(self):
        self.base_url = "https://api.flutterwave.com/v3"
        self.secret_key = settings.FLUTTERWAVE_SECRET_KEY
        self.public_key = settings.FLUTTERWAVE_PUBLIC_KEY
    
    async def initiate_mpesa_payment(
        self,
        phone_number: str,
        amount: float,
        email: str,
        tx_ref: str,
        description: str = "AgroPulse AI Diagnosis"
    ) -> dict:
        """
        Initiate M-Pesa STK Push payment via Flutterwave
        """
        url = f"{self.base_url}/charges?type=mpesa"
        
        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "tx_ref": tx_ref,
            "amount": str(amount),
            "currency": "KES",
            "email": email,
            "phone_number": phone_number,
            "fullname": "AgroPulse User",
            "meta": {
                "description": description
            }
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def verify_transaction(self, transaction_id: str) -> dict:
        """
        Verify a transaction status
        """
        url = f"{self.base_url}/transactions/{transaction_id}/verify"
        
        headers = {
            "Authorization": f"Bearer {self.secret_key}"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def handle_webhook(self, payload: dict, signature: str) -> bool:
        """
        Verify and handle webhook from Flutterwave
        """
        # Verify webhook signature
        hash_object = hashlib.sha256(
            settings.FLUTTERWAVE_SECRET_KEY.encode()
        )
        expected_signature = hash_object.hexdigest()
        
        if signature != expected_signature:
            return False
        
        return True


class MPesaService:
    """
    Direct M-Pesa integration (alternative to Flutterwave)
    """
    def __init__(self):
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.shortcode = settings.MPESA_SHORTCODE
        self.base_url = "https://sandbox.safaricom.co.ke"  # Change to production URL
        self.access_token = None
    
    async def get_access_token(self) -> Optional[str]:
        """
        Get OAuth access token from M-Pesa API
        """
        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    auth=(self.consumer_key, self.consumer_secret)
                )
                response.raise_for_status()
                data = response.json()
                self.access_token = data.get("access_token")
                return self.access_token
        except Exception as e:
            print(f"Error getting M-Pesa access token: {e}")
            return None
    
    async def stk_push(
        self,
        phone_number: str,
        amount: int,
        account_reference: str,
        transaction_desc: str
    ) -> dict:
        """
        Initiate STK Push (Lipa Na M-Pesa Online)
        """
        if not self.access_token:
            await self.get_access_token()
        
        url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        # Format phone number (254...)
        if phone_number.startswith("0"):
            phone_number = "254" + phone_number[1:]
        
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": self._generate_password(timestamp),
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone_number,
            "PartyB": self.shortcode,
            "PhoneNumber": phone_number,
            "CallBackURL": "https://yourdomain.com/api/v1/payments/mpesa/callback",
            "AccountReference": account_reference,
            "TransactionDesc": transaction_desc
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            return {
                "ResponseCode": "1",
                "ResponseDescription": str(e)
            }
    
    def _generate_password(self, timestamp: str) -> str:
        """
        Generate M-Pesa password
        """
        import base64
        passkey = "your_mpesa_passkey"  # Get from Safaricom
        data = f"{self.shortcode}{passkey}{timestamp}"
        return base64.b64encode(data.encode()).decode()


# Singleton instances
flutterwave_service = FlutterwaveService()
mpesa_service = MPesaService()
