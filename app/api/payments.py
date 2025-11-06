from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict
import uuid
from datetime import datetime
from app.database import get_db
from app.models.permit import Payment, Permit, PaymentStatus, PermitStatus
from app.models.user import User
from app.schemas.payment import (
    PaymentInitiate, PaymentResponse, PermitResponse, PaymentCallback
)
from app.auth import get_current_farmer
from app.services.payment import flutterwave_service, mpesa_service
from app.services.blockchain import blockchain_service
from app.config import settings

router = APIRouter(prefix="/payments", tags=["Payments & Permits"])


@router.post("/initiate", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def initiate_payment(
    payment_data: PaymentInitiate,
    current_user: User = Depends(get_current_farmer),
    db: AsyncSession = Depends(get_db)
):
    """
    Initiate a payment for AI diagnosis or subscription
    This triggers the M-Pesa STK push
    """
    # Generate unique transaction reference
    tx_ref = f"AGRO-{uuid.uuid4().hex[:12].upper()}"
    
    # Create payment record
    new_payment = Payment(
        user_id=current_user.id,
        amount=payment_data.amount,
        currency="KES",
        payment_method=payment_data.payment_method,
        status=PaymentStatus.PENDING,
        phone_number=payment_data.phone_number,
        description=payment_data.description,
        flutterwave_tx_ref=tx_ref
    )
    
    db.add(new_payment)
    await db.commit()
    await db.refresh(new_payment)
    
    # Initiate M-Pesa payment via Flutterwave
    if payment_data.payment_method == "mpesa":
        result = await flutterwave_service.initiate_mpesa_payment(
            phone_number=payment_data.phone_number,
            amount=payment_data.amount,
            email=current_user.email or f"{current_user.phone_number}@agropulse.com",
            tx_ref=tx_ref,
            description=payment_data.description
        )
        
        if result.get("status") == "success":
            new_payment.gateway_transaction_id = result.get("data", {}).get("id")
            new_payment.status = PaymentStatus.PROCESSING
            await db.commit()
        else:
            new_payment.status = PaymentStatus.FAILED
            new_payment.failed_reason = result.get("message", "Payment initiation failed")
            await db.commit()
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment failed: {result.get('message')}"
            )
    
    return PaymentResponse.model_validate(new_payment)


@router.post("/webhook/flutterwave")
async def flutterwave_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Webhook endpoint for Flutterwave payment callbacks
    """
    # Verify webhook signature
    signature = request.headers.get("verif-hash")
    
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature"
        )
    
    payload = await request.json()
    
    # Verify webhook
    is_valid = await flutterwave_service.handle_webhook(payload, signature)
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature"
        )
    
    # Process payment
    tx_ref = payload.get("txRef")
    status_code = payload.get("status")
    
    # Find payment
    result = await db.execute(
        select(Payment).where(Payment.flutterwave_tx_ref == tx_ref)
    )
    payment = result.scalar_one_or_none()
    
    if not payment:
        return {"status": "payment not found"}
    
    if status_code == "successful":
        payment.status = PaymentStatus.COMPLETED
        payment.completed_at = datetime.utcnow()
        payment.flutterwave_transaction_id = payload.get("id")
        payment.gateway_reference = payload.get("flwRef")
        
        # Mint blockchain permit
        await mint_permit_for_payment(payment, db)
    else:
        payment.status = PaymentStatus.FAILED
        payment.failed_reason = payload.get("message", "Payment failed")
    
    await db.commit()
    
    return {"status": "processed"}


async def mint_permit_for_payment(payment: Payment, db: AsyncSession):
    """
    Mint a blockchain permit after successful payment
    """
    # Get user's wallet address
    result = await db.execute(
        select(User).where(User.id == payment.user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user or not user.wallet_address:
        # Create a wallet for the user if they don't have one
        # For now, we'll use a default address
        wallet_address = "0x0000000000000000000000000000000000000000"
    else:
        wallet_address = user.wallet_address
    
    # Create permit record
    new_permit = Permit(
        user_id=payment.user_id,
        payment_id=payment.id,
        status=PermitStatus.PENDING,
        permit_type="diagnosis"
    )
    
    db.add(new_permit)
    await db.flush()
    
    # Mint on blockchain
    blockchain_result = await blockchain_service.mint_permit(
        wallet_address=wallet_address,
        permit_type="diagnosis"
    )
    
    if blockchain_result.get("success"):
        new_permit.status = PermitStatus.MINTED
        new_permit.permit_token_id = blockchain_result.get("token_id")
        new_permit.transaction_hash = blockchain_result.get("transaction_hash")
        new_permit.contract_address = settings.PERMIT_CONTRACT_ADDRESS
    else:
        new_permit.status = PermitStatus.PENDING
        # Log error but don't fail the payment
        print(f"Blockchain minting failed: {blockchain_result.get('error')}")
    
    await db.commit()


@router.get("/permits", response_model=list[PermitResponse])
async def get_user_permits(
    current_user: User = Depends(get_current_farmer),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all permits owned by the current user
    """
    result = await db.execute(
        select(Permit).where(
            Permit.user_id == current_user.id,
            Permit.status == PermitStatus.MINTED,
            Permit.is_used == False
        ).order_by(Permit.created_at.desc())
    )
    permits = result.scalars().all()
    
    return [PermitResponse.model_validate(permit) for permit in permits]


@router.get("/permits/{permit_token_id}/verify", response_model=Dict)
async def verify_permit(
    permit_token_id: str,
    current_user: User = Depends(get_current_farmer),
    db: AsyncSession = Depends(get_db)
):
    """
    Verify if a permit is valid and unused
    """
    # Check database
    result = await db.execute(
        select(Permit).where(
            Permit.permit_token_id == permit_token_id,
            Permit.user_id == current_user.id
        )
    )
    permit = result.scalar_one_or_none()
    
    if not permit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permit not found"
        )
    
    # Verify on blockchain
    is_valid_on_chain = await blockchain_service.verify_permit(permit_token_id)
    
    return {
        "valid": not permit.is_used and permit.status == PermitStatus.MINTED and is_valid_on_chain,
        "permit": PermitResponse.model_validate(permit),
        "blockchain_status": "valid" if is_valid_on_chain else "invalid"
    }
