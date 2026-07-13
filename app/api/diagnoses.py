from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from datetime import datetime
import uuid
from app.database import get_db
from app.models.diagnosis import Diagnosis, DiagnosisStatus
from app.models.permit import Permit, PermitStatus
from app.models.user import User
from app.schemas.diagnosis import (
    DiagnosisRequest, DiagnosisResponse, DiagnosisComplete
)
from app.auth import get_current_user  # Changed from get_current_farmer
from app.services.ai_service import aws_ai_service
from app.services.blockchain import blockchain_service

router = APIRouter(prefix="/diagnoses", tags=["AI Crop Health Diagnosis"])


@router.post("", response_model=DiagnosisResponse, status_code=status.HTTP_201_CREATED)
async def create_diagnosis(
    diagnosis_data: DiagnosisRequest,
    current_user: User = Depends(get_current_user),  # Changed from get_current_farmer
    db: AsyncSession = Depends(get_db)
):
    """
    Submit images for AI greenhouse crop disease diagnosis.
    
    Supports:
    - Tomatoes, lettuce, peppers, cucumbers, herbs, ornamentals
    - Greenhouse-specific diseases (powdery mildew, Botrytis, aphids, whiteflies)
    - Environmental stress detection (humidity, nutrient deficiencies)
    
    Requires a valid, unused permit (paid via M-Pesa).
    """
    # Verify permit
    result = await db.execute(
        select(Permit).where(
            Permit.permit_token_id == diagnosis_data.permit_token_id,
            Permit.user_id == current_user.id,
            Permit.status == PermitStatus.MINTED,
            Permit.is_used == False
        )
    )
    permit = result.scalar_one_or_none()
    
    if not permit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or already used permit. Please purchase a diagnosis permit."
        )
    
    # Verify permit on blockchain
    is_valid = await blockchain_service.verify_permit(diagnosis_data.permit_token_id)
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permit is not valid on blockchain"
        )
    
    # Create diagnosis record
    new_diagnosis = Diagnosis(
        farmer_id=current_user.id,
        alert_id=diagnosis_data.alert_id,
        permit_id=permit.id,
        status=DiagnosisStatus.PENDING,
        image_urls=diagnosis_data.image_urls,
        diagnosis_metadata=diagnosis_data.metadata,
        triage_diagnosis=diagnosis_data.triage_diagnosis,
        triage_confidence=diagnosis_data.triage_confidence
    )
    
    db.add(new_diagnosis)
    await db.commit()
    await db.refresh(new_diagnosis)
    
    # Mark permit as used
    permit.is_used = True
    permit.used_at = datetime.utcnow()
    
    # Mark as used on blockchain
    await blockchain_service.use_permit(diagnosis_data.permit_token_id)
    
    await db.commit()
    
    # Process diagnosis asynchronously (would normally use Celery)
    # For now, we'll do it synchronously
    await process_diagnosis(new_diagnosis.id, db)
    
    return DiagnosisResponse.model_validate(new_diagnosis)


async def process_diagnosis(diagnosis_id: int, db: AsyncSession):
    """
    Process the diagnosis using AWS AI services
    This would normally be a Celery background task
    """
    # Fetch diagnosis
    result = await db.execute(
        select(Diagnosis).where(Diagnosis.id == diagnosis_id)
    )
    diagnosis = result.scalar_one_or_none()
    
    if not diagnosis:
        return
    
    # Update status
    diagnosis.status = DiagnosisStatus.PROCESSING
    await db.commit()
    
    try:
        # Call AWS AI service
        ai_result = await aws_ai_service.diagnose_crop_disease(
            image_urls=diagnosis.image_urls,
            metadata=diagnosis.diagnosis_metadata
        )
        
        if ai_result.get("success"):
            # Update diagnosis with results
            diagnosis.status = DiagnosisStatus.COMPLETED
            diagnosis.primary_diagnosis = ai_result.get("primary_diagnosis")
            diagnosis.category = ai_result.get("category")
            diagnosis.confidence_score = ai_result.get("confidence_score")
            diagnosis.alternative_diagnoses = ai_result.get("alternative_diagnoses")
            diagnosis.affected_area_percentage = ai_result.get("affected_area_percentage")
            diagnosis.severity_level = ai_result.get("severity_level")
            diagnosis.treatment_recommendations = ai_result.get("treatment_recommendations")
            diagnosis.preventive_measures = ai_result.get("preventive_measures")
            diagnosis.ai_model_version = ai_result.get("ai_model_version")
            diagnosis.processing_time_seconds = ai_result.get("processing_time_seconds")
            diagnosis.completed_at = datetime.utcnow()
        else:
            diagnosis.status = DiagnosisStatus.FAILED
            diagnosis.completed_at = datetime.utcnow()
        
        await db.commit()
        
    except Exception as e:
        print(f"Error processing diagnosis: {e}")
        diagnosis.status = DiagnosisStatus.FAILED
        diagnosis.completed_at = datetime.utcnow()
        await db.commit()


@router.get("/{diagnosis_id}", response_model=DiagnosisComplete)
async def get_diagnosis(
    diagnosis_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed results of a diagnosis
    """
    result = await db.execute(
        select(Diagnosis).where(
            Diagnosis.id == diagnosis_id,
            Diagnosis.farmer_id == current_user.id
        )
    )
    diagnosis = result.scalar_one_or_none()
    
    if not diagnosis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diagnosis not found"
        )
    
    return DiagnosisComplete.model_validate(diagnosis)


@router.get("", response_model=List[DiagnosisResponse])
async def get_user_diagnoses(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 20,
    offset: int = 0
):
    """
    Get all diagnoses for the current user
    """
    result = await db.execute(
        select(Diagnosis)
        .where(Diagnosis.farmer_id == current_user.id)
        .order_by(Diagnosis.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    diagnoses = result.scalars().all()
    
    return [DiagnosisResponse.model_validate(d) for d in diagnoses]


@router.post("/upload-image", response_model=dict)
async def upload_diagnosis_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Upload an image for diagnosis to S3
    Returns the S3 URL to be used in the diagnosis request
    """
    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    # Generate unique filename
    file_extension = file.filename.split(".")[-1]
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    
    # Read file content
    file_content = await file.read()
    
    # Upload to S3
    try:
        image_url = await aws_ai_service.upload_to_s3(
            file_content=file_content,
            file_name=unique_filename
        )
        
        return {
            "success": True,
            "image_url": image_url,
            "filename": unique_filename
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image: {str(e)}"
        )
