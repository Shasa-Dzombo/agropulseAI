from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from datetime import datetime
from app.database import get_db
from app.models.optimization import ScoutingPlan, OptimizationStatus
from app.models.sensor import Alert
from app.models.user import User, Farm
from app.schemas.optimization import (
    ScoutingPlanRequest, ScoutingPlanResponse, ChatbotMessage, ChatbotResponse
)
from app.auth import get_current_farmer
from app.services.quantum_service import quantum_service
from app.services.claude_ai_service import claude_ai_service, ClaudeNotConfiguredError
from app.config import settings

router = APIRouter(prefix="/optimization", tags=["Quantum Optimization"])


@router.post("/scouting-plan", response_model=ScoutingPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_scouting_plan(
    plan_data: ScoutingPlanRequest,
    current_user: User = Depends(get_current_farmer),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate an optimal farm scouting plan using Quantum Computing
    This is a PREMIUM feature for subscription users
    
    Solves the problem: "I have 30 alerts, 500 KSh budget, and 2 hours. 
    Which alerts should I investigate and in what order?"
    """
    # Verify farm ownership
    result = await db.execute(
        select(Farm).where(Farm.id == plan_data.farm_id, Farm.owner_id == current_user.id)
    )
    farm = result.scalar_one_or_none()
    
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm not found"
        )
    
    # Fetch alerts
    result = await db.execute(
        select(Alert).where(Alert.id.in_(plan_data.alert_ids))
    )
    alerts = result.scalars().all()
    
    if not alerts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid alerts found"
        )
    
    # Convert alerts to dict format for quantum service
    alert_dicts = [
        {
            "id": alert.id,
            "severity": alert.severity,
            "confidence_score": alert.confidence_score or 0.5,
            "alert_type": alert.alert_type,
            "latitude": alert.latitude,
            "longitude": alert.longitude,
            "zone_id": alert.zone_id
        }
        for alert in alerts
    ]
    
    # Create scouting plan record
    new_plan = ScoutingPlan(
        user_id=current_user.id,
        farm_id=plan_data.farm_id,
        status=OptimizationStatus.PENDING,
        available_budget_ksh=plan_data.available_budget_ksh,
        available_time_hours=plan_data.available_time_hours,
        alert_ids=plan_data.alert_ids
    )
    
    db.add(new_plan)
    await db.commit()
    await db.refresh(new_plan)
    
    # Process with quantum optimization
    await process_quantum_optimization(new_plan.id, alert_dicts, db)
    
    # Refresh to get updated results
    await db.refresh(new_plan)
    
    return ScoutingPlanResponse.model_validate(new_plan)


async def process_quantum_optimization(
    plan_id: int,
    alerts: List[dict],
    db: AsyncSession
):
    """
    Process the quantum optimization
    This would normally be a Celery background task
    """
    # Fetch plan
    result = await db.execute(
        select(ScoutingPlan).where(ScoutingPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    
    if not plan:
        return
    
    # Update status
    plan.status = OptimizationStatus.PROCESSING
    await db.commit()
    
    try:
        # Call quantum service
        quantum_result = await quantum_service.optimize_scouting_plan(
            alerts=alerts,
            budget=plan.available_budget_ksh,
            time_available_hours=plan.available_time_hours
        )
        
        if quantum_result.get("success"):
            plan.status = OptimizationStatus.COMPLETED
            plan.optimal_path = quantum_result.get("optimal_path")
            plan.estimated_cost = quantum_result.get("estimated_cost")
            plan.estimated_time_hours = quantum_result.get("estimated_time_hours")
            plan.risk_coverage_percentage = quantum_result.get("risk_coverage_percentage")
            plan.priority_alerts = quantum_result.get("priority_alerts")
            plan.skipped_alerts = quantum_result.get("skipped_alerts")
            plan.reasoning = quantum_result.get("reasoning")
            plan.quantum_backend = quantum_result.get("quantum_backend")
            plan.processing_time_seconds = quantum_result.get("processing_time_seconds")
            plan.algorithm_used = quantum_result.get("algorithm_used")
            plan.completed_at = datetime.utcnow()
        else:
            plan.status = OptimizationStatus.FAILED
            plan.completed_at = datetime.utcnow()
        
        await db.commit()
        
    except Exception as e:
        print(f"Error in quantum optimization: {e}")
        plan.status = OptimizationStatus.FAILED
        plan.completed_at = datetime.utcnow()
        await db.commit()


@router.get("/scouting-plans", response_model=List[ScoutingPlanResponse])
async def get_user_scouting_plans(
    current_user: User = Depends(get_current_farmer),
    db: AsyncSession = Depends(get_db),
    limit: int = 20
):
    """
    Get all scouting plans for the current user
    """
    result = await db.execute(
        select(ScoutingPlan)
        .where(ScoutingPlan.user_id == current_user.id)
        .order_by(ScoutingPlan.created_at.desc())
        .limit(limit)
    )
    plans = result.scalars().all()
    
    return [ScoutingPlanResponse.model_validate(p) for p in plans]


@router.get("/scouting-plans/{plan_id}", response_model=ScoutingPlanResponse)
async def get_scouting_plan(
    plan_id: int,
    current_user: User = Depends(get_current_farmer),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific scouting plan
    """
    result = await db.execute(
        select(ScoutingPlan).where(
            ScoutingPlan.id == plan_id,
            ScoutingPlan.user_id == current_user.id
        )
    )
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scouting plan not found"
        )
    
    return ScoutingPlanResponse.model_validate(plan)


@router.post("/chatbot", response_model=ChatbotResponse)
async def chatbot_query(
    message: ChatbotMessage,
    current_user: User = Depends(get_current_farmer),
    db: AsyncSession = Depends(get_db)
):
    """
    AI Chatbot that can help farmers make decisions
    Can suggest optimal scouting plans based on conversation
    """
    # Simple chatbot logic (in production, use OpenAI GPT or Claude)
    user_message = message.message.lower()
    
    if "plan" in user_message or "scout" in user_message:
        # Check if user has pending alerts
        if message.farm_id:
            result = await db.execute(
                select(Alert).where(
                    Alert.farm_id == message.farm_id,
                    Alert.status == "pending"
                )
            )
            pending_alerts = result.scalars().all()
            
            if pending_alerts:
                return ChatbotResponse(
                    response=f"You have {len(pending_alerts)} pending alerts. Would you like me to create an optimal scouting plan? Please provide your available budget (in KSh) and time (in hours).",
                    suggested_actions=[
                        "Create scouting plan",
                        "View alerts",
                        "Purchase diagnosis permit"
                    ]
                )
    
    elif "diagnosis" in user_message or "scan" in user_message:
        return ChatbotResponse(
            response=f"To get an AI diagnosis, you need a permit (50 KSh). Each permit allows one high-quality diagnosis. Would you like to purchase a permit?",
            suggested_actions=[
                "Purchase permit (50 KSh)",
                "View my permits",
                "Learn more about diagnosis"
            ]
        )
    
    elif "help" in user_message:
        return ChatbotResponse(
            response="I can help you with:\n1. Creating optimal scouting plans\n2. Purchasing diagnosis permits\n3. Viewing your farm alerts\n4. Getting treatment recommendations\n\nWhat would you like to do?",
            suggested_actions=[
                "View alerts",
                "Create scouting plan",
                "Purchase permit",
                "View subscription options"
            ]
        )
    
    else:
        # Falls through here for anything that isn't a recognized
        # plan/diagnosis/help keyword - hand it to Claude instead of the
        # generic static reply.
        try:
            reply = await claude_ai_service.chat(message.message)
            return ChatbotResponse(
                response=reply,
                suggested_actions=["View alerts", "Get help"]
            )
        except ClaudeNotConfiguredError:
            return ChatbotResponse(
                response="I'm here to help you manage your farm efficiently. You can ask me about scouting plans, diagnosis permits, or farm alerts.",
                suggested_actions=[
                    "View alerts",
                    "Get help"
                ]
            )
