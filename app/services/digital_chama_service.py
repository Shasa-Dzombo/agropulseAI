"""
Digital Chama AI Service
AI-powered farmer cooperative coordination

Core Ideas:
1. Contextual Conversation Router (AI Moderator)
2. Predictive Group Buying Optimization
3. Financial Health & Risk Scoring (SACCO)
4. Dynamic Harvest Bundle Pricing & Market Matching
5. Automated Resource & Logistics Management
6. Smart Contract & Governance Bot
7. Verifiable Reputation Ledger
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_
import logging
import hashlib
import json

from app.database import get_db
from app.models.chama import (
    Chama, ChamaMember, SACCOAccount, SACCOTransaction,
    GroupBuy, HarvestBundle, EquipmentBooking, ChatMessage,
    ReputationScore, DisputeCase, ChatMessageCategory,
    TransactionType, DisputeStatus
)
from app.services.quantum_service import quantum_service

logger = logging.getLogger(__name__)


class DigitalChamaAIService:
    """
    AI-powered coordination for farmer cooperatives
    """
    
    # ========================================================================
    # CORE IDEA 1: CONTEXTUAL CONVERSATION ROUTER (AI MODERATOR)
    # ========================================================================
    
    async def route_chat_message(
        self,
        db: AsyncSession,
        chama_id: int,
        member_id: int,
        message_text: str,
        image_url: Optional[str] = None
    ) -> Dict:
        """
        AI Moderator: Classify and route farmer inquiries
        
        Categories:
        - Pest/Disease Inquiry → Tag Agri-Officer
        - Fertilizer Query → RAG Knowledge Base
        - Harvest Timing → RAG Knowledge Base
        - Equipment Booking → Equipment system
        - SACCO Loan → SACCO system
        - General Chat → Community forum
        """
        # Classify message using AI
        category, confidence = self._classify_message(message_text, image_url)
        
        # Generate AI response if applicable
        ai_response = None
        redirected_to = None
        tagged_officer = False
        
        if category == ChatMessageCategory.PEST_DISEASE:
            # Tag Agri-Officer for expert response
            tagged_officer = True
            ai_response = "🔔 Tagged Agri-Officer for expert diagnosis. They will respond shortly."
            
        elif category == ChatMessageCategory.FERTILIZER_QUERY:
            # Use RAG to query knowledge base
            ai_response = await self._query_knowledge_base(message_text, "fertilizer")
            
        elif category == ChatMessageCategory.HARVEST_TIMING:
            # Use RAG for planting/harvest guidance
            ai_response = await self._query_knowledge_base(message_text, "harvest_timing")
            
        elif category == ChatMessageCategory.EQUIPMENT_BOOKING:
            # Redirect to equipment booking
            redirected_to = "equipment_booking"
            ai_response = "📅 I can help you book equipment. Use the Equipment Booking tool."
            
        elif category == ChatMessageCategory.SACCO_LOAN:
            # Redirect to SACCO system
            redirected_to = "sacco_loan"
            ai_response = "💰 Check your loan eligibility in the SACCO section."
            
        # Store message
        chat_msg = ChatMessage(
            chama_id=chama_id,
            member_id=member_id,
            message_text=message_text,
            image_url=image_url,
            ai_category=category,
            ai_confidence=confidence,
            ai_tagged_officer=tagged_officer,
            ai_response=ai_response,
            redirected_to=redirected_to,
            timestamp=datetime.utcnow()
        )
        db.add(chat_msg)
        await db.commit()
        await db.refresh(chat_msg)
        
        return {
            "message_id": chat_msg.id,
            "category": category.value,
            "confidence": confidence,
            "ai_response": ai_response,
            "tagged_officer": tagged_officer,
            "redirected_to": redirected_to
        }
    
    def _classify_message(
        self,
        message_text: str,
        image_url: Optional[str] = None
    ) -> Tuple[ChatMessageCategory, float]:
        """
        Classify message using NLP + Computer Vision
        
        In production: Fine-tuned BERT model + ResNet for images
        """
        text_lower = message_text.lower()
        
        # Keyword-based classification (simplified)
        pest_keywords = ["pest", "insect", "disease", "spots", "yellow", "leaves", "rot", "worm"]
        fertilizer_keywords = ["fertilizer", "dap", "can", "npk", "manure", "compost"]
        harvest_keywords = ["harvest", "plant", "when", "timing", "season", "ready"]
        equipment_keywords = ["tractor", "planter", "sprayer", "grading belt", "equipment", "booking"]
        sacco_keywords = ["loan", "borrow", "sacco", "savings", "credit"]
        
        if any(kw in text_lower for kw in pest_keywords) or image_url:
            return ChatMessageCategory.PEST_DISEASE, 0.85
        elif any(kw in text_lower for kw in fertilizer_keywords):
            return ChatMessageCategory.FERTILIZER_QUERY, 0.90
        elif any(kw in text_lower for kw in harvest_keywords):
            return ChatMessageCategory.HARVEST_TIMING, 0.88
        elif any(kw in text_lower for kw in equipment_keywords):
            return ChatMessageCategory.EQUIPMENT_BOOKING, 0.92
        elif any(kw in text_lower for kw in sacco_keywords):
            return ChatMessageCategory.SACCO_LOAN, 0.93
        else:
            return ChatMessageCategory.GENERAL_CHAT, 0.75
    
    async def _query_knowledge_base(
        self,
        query: str,
        topic: str
    ) -> str:
        """
        RAG (Retrieval-Augmented Generation) Knowledge Base
        
        In production: Vector database (Pinecone) + GPT-4
        """
        # Simulated knowledge base responses
        if "fertilizer" in topic:
            return """
            💡 **Fertilizer Recommendation (DAP)**:
            - Application rate: 50kg/acre for maize
            - Timing: At planting, place in furrow
            - Top-dressing: Use CAN 2-3 weeks after emergence
            - Cost-saving tip: Join Group Buy for 15% discount!
            
            Source: Kenya Agricultural Research Institute (KARI)
            """
        elif "harvest" in topic:
            return """
            📅 **Optimal Planting Time (Kisii Region)**:
            - Long rains: March-May (plant in March)
            - Short rains: October-December (plant in October)
            - Rice: Plant at start of rainy season for 120-day maturity
            
            🔔 Your AgroPulse AI Calendar recommends: Plant in 14 days
            
            Source: Kenya Meteorological Department
            """
        else:
            return "ℹ️ I'm still learning. An Agri-Officer will respond soon."
    
    # ========================================================================
    # CORE IDEA 2: PREDICTIVE GROUP BUYING OPTIMIZATION
    # ========================================================================
    
    async def predict_input_demand(
        self,
        db: AsyncSession,
        chama_id: Optional[int] = None,
        county: Optional[str] = None,
        product_category: str = "fertilizer"
    ) -> Dict:
        """
        Predict demand for agricultural inputs
        
        Data sources:
        1. Farm Calendars (fertilizer application dates)
        2. Group Buy History (historical demand)
        3. Weather Data (rain forecasts increase demand)
        """
        # Get relevant Chamas
        query = select(Chama)
        if chama_id:
            query = query.where(Chama.id == chama_id)
        elif county:
            query = query.where(Chama.county == county)
        
        result = await db.execute(query)
        chamas = result.scalars().all()
        
        # Get historical group buy data
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        group_buy_query = select(GroupBuy).where(
            and_(
                GroupBuy.product_category == product_category,
                GroupBuy.created_at >= thirty_days_ago
            )
        )
        result = await db.execute(group_buy_query)
        historical_buys = result.scalars().all()
        
        # Calculate demand prediction
        total_farmers = sum([c.total_members for c in chamas])
        historical_avg = np.mean([b.target_quantity for b in historical_buys]) if historical_buys else 50
        
        # Simple prediction model
        # In production: LSTM time series forecasting
        base_demand = total_farmers * 2  # 2 bags per farmer
        seasonal_factor = 1.5 if datetime.utcnow().month in [3, 4, 10, 11] else 1.0  # Planting season
        weather_factor = 1.2  # Heavy rains forecasted (would pull from weather API)
        
        predicted_demand = int(base_demand * seasonal_factor * weather_factor)
        confidence = 0.85
        
        # Calculate savings from aggregation
        unit_price_ksh = 5000  # Price per bag
        bulk_discount_percent = min(15, predicted_demand / 100)  # Up to 15% for large orders
        savings_per_unit = unit_price_ksh * (bulk_discount_percent / 100)
        total_savings_ksh = savings_per_unit * predicted_demand
        
        return {
            "product_category": product_category,
            "predicted_demand_units": predicted_demand,
            "confidence": confidence,
            "participating_chamas": len(chamas),
            "total_farmers": total_farmers,
            "time_horizon": "next_30_days",
            "recommendation": {
                "action": "start_aggregation",
                "target_quantity": predicted_demand,
                "expected_bulk_discount_percent": bulk_discount_percent,
                "estimated_savings_ksh": total_savings_ksh,
                "savings_per_farmer_ksh": total_savings_ksh / max(total_farmers, 1)
            },
            "optimal_vendor": {
                "name": "Kisii Agro-Dealers Co-op",
                "rating": 4.5,
                "price_ksh_per_unit": unit_price_ksh * (1 - bulk_discount_percent / 100),
                "delivery_time_days": 7
            }
        }
    
    async def create_proactive_group_buy(
        self,
        db: AsyncSession,
        chama_id: int,
        demand_prediction: Dict
    ) -> Dict:
        """
        Automatically create Group Buy based on AI prediction
        """
        group_buy = GroupBuy(
            chama_id=chama_id,
            product_name=f"{demand_prediction['product_category'].upper()} (50kg bags)",
            product_category=demand_prediction['product_category'],
            product_unit="bag",
            unit_price_ksh=demand_prediction['optimal_vendor']['price_ksh_per_unit'],
            bulk_discount_percent=demand_prediction['recommendation']['expected_bulk_discount_percent'],
            final_unit_price_ksh=demand_prediction['optimal_vendor']['price_ksh_per_unit'],
            target_quantity=demand_prediction['predicted_demand_units'],
            current_quantity=0,
            status="open",
            deadline=datetime.utcnow() + timedelta(days=14),
            vendor_name=demand_prediction['optimal_vendor']['name'],
            vendor_rating=demand_prediction['optimal_vendor']['rating'],
            ai_recommended=True,
            predicted_demand=demand_prediction['predicted_demand_units'],
            created_by_member_id=1,  # System-created
            created_at=datetime.utcnow()
        )
        db.add(group_buy)
        await db.commit()
        await db.refresh(group_buy)
        
        return {
            "group_buy_id": group_buy.id,
            "message": f"🤖 AI created Group Buy for {group_buy.product_name}",
            "savings_opportunity_ksh": demand_prediction['recommendation']['estimated_savings_ksh']
        }
    
    # ========================================================================
    # CORE IDEA 3: FINANCIAL HEALTH & RISK SCORING (SACCO)
    # ========================================================================
    
    async def calculate_loan_risk_score(
        self,
        db: AsyncSession,
        member_id: int
    ) -> Dict:
        """
        Dynamic Micro-Loan Risk Scoring
        
        Factors:
        1. Historical Savings Consistency
        2. Farm Asset Verification (drone/GPS)
        3. AgroPulse Yield Prediction
        4. Loan Repayment History
        """
        # Get member and account
        result = await db.execute(
            select(ChamaMember).where(ChamaMember.id == member_id)
        )
        member = result.scalar_one_or_none()
        
        if not member:
            raise ValueError(f"Member {member_id} not found")
        
        result = await db.execute(
            select(SACCOAccount).where(SACCOAccount.member_id == member_id)
        )
        account = result.scalar_one_or_none()
        
        if not account:
            raise ValueError(f"SACCO account not found for member {member_id}")
        
        # === FACTOR 1: Savings Consistency ===
        # Check contribution history
        contribution_query = select(SACCOTransaction).where(
            and_(
                SACCOTransaction.member_id == member_id,
                SACCOTransaction.transaction_type == TransactionType.CONTRIBUTION
            )
        ).order_by(SACCOTransaction.timestamp.desc()).limit(12)
        
        result = await db.execute(contribution_query)
        recent_contributions = result.scalars().all()
        
        if len(recent_contributions) >= 6:
            savings_consistency_score = 90.0
        elif len(recent_contributions) >= 3:
            savings_consistency_score = 70.0
        else:
            savings_consistency_score = 40.0
        
        # === FACTOR 2: Farm Asset Verification ===
        # In production: Pull from drone scan data
        farm_asset_value_ksh = member.farm_size_acres * 50000 if member.farm_size_acres else 0
        farm_asset_score = min(100, (farm_asset_value_ksh / 100000) * 100)
        
        # === FACTOR 3: Yield Prediction ===
        # In production: Pull from AgroPulse AI Calendar
        predicted_income_ksh = member.farm_size_acres * 80000 if member.farm_size_acres else 0  # 80k per acre
        yield_score = min(100, (predicted_income_ksh / 200000) * 100)
        
        # === FACTOR 4: Loan Repayment History ===
        if account.loan_repayment_score > 95:
            repayment_score = 100.0
        elif account.loan_repayment_score > 80:
            repayment_score = 80.0
        else:
            repayment_score = 50.0
        
        # === CALCULATE OVERALL RISK SCORE ===
        risk_score = (
            savings_consistency_score * 0.30 +
            farm_asset_score * 0.20 +
            yield_score * 0.30 +
            repayment_score * 0.20
        )
        
        # Update account
        account.risk_score = risk_score
        account.savings_consistency_score = savings_consistency_score
        account.farm_asset_value_ksh = farm_asset_value_ksh
        account.predicted_annual_income_ksh = predicted_income_ksh
        
        # Calculate available credit
        base_credit = account.savings_balance_ksh * 3  # 3x savings
        risk_multiplier = risk_score / 100
        available_credit_ksh = base_credit * risk_multiplier
        account.available_credit_ksh = available_credit_ksh
        
        # Recommended loan terms
        if risk_score >= 80:
            interest_rate = 3.0  # Low risk = low rate
            max_loan_ksh = available_credit_ksh
        elif risk_score >= 60:
            interest_rate = 5.0
            max_loan_ksh = available_credit_ksh * 0.8
        else:
            interest_rate = 8.0
            max_loan_ksh = available_credit_ksh * 0.5
        
        await db.commit()
        
        return {
            "member_id": member_id,
            "risk_score": round(risk_score, 2),
            "risk_category": "Low" if risk_score >= 80 else "Medium" if risk_score >= 60 else "High",
            "components": {
                "savings_consistency": round(savings_consistency_score, 2),
                "farm_assets": round(farm_asset_score, 2),
                "yield_prediction": round(yield_score, 2),
                "repayment_history": round(repayment_score, 2)
            },
            "loan_recommendation": {
                "max_loan_amount_ksh": round(max_loan_ksh, 2),
                "interest_rate_percent": interest_rate,
                "recommended_duration_months": 6,
                "monthly_payment_ksh": round((max_loan_ksh * (1 + interest_rate / 100)) / 6, 2)
            },
            "message": f"✅ {'Loan Approved' if risk_score >= 60 else '⚠️ Loan Risky'}"
        }
    
    async def send_behavioral_nudge(
        self,
        db: AsyncSession,
        member_id: int
    ) -> Optional[Dict]:
        """
        Personalized financial coaching nudges
        """
        # Get account
        result = await db.execute(
            select(SACCOAccount).where(SACCOAccount.member_id == member_id)
        )
        account = result.scalar_one_or_none()
        
        if not account:
            return None
        
        nudges = []
        
        # Check spending patterns
        # In production: Analyze actual spending data
        if account.consecutive_contributions < 3:
            nudges.append({
                "type": "savings_reminder",
                "message": "📊 You've missed recent contributions. Regular savings unlock better loan rates!",
                "action_url": "/sacco/contribute"
            })
        
        # Check loan status
        if account.active_loan and account.loan_balance_ksh < 1000:
            nudges.append({
                "type": "loan_payoff_celebration",
                "message": "🎉 Almost done! Just 1,000 KSh left on your loan. Your credit score will increase!",
                "action_url": "/sacco/repay"
            })
        
        # Group buy savings opportunity
        nudges.append({
            "type": "savings_opportunity",
            "message": "💰 Group Buy for DAP is open! Save 15% by joining now.",
            "action_url": "/group_buys/active"
        })
        
        return {
            "member_id": member_id,
            "nudges": nudges,
            "nudge_count": len(nudges)
        }
    
    # ========================================================================
    # CORE IDEA 7: VERIFIABLE REPUTATION LEDGER
    # ========================================================================
    
    async def calculate_reputation_score(
        self,
        db: AsyncSession,
        member_id: int
    ) -> Dict:
        """
        Build farmer reputation score from ecosystem data
        
        Components:
        - Financial: SACCO performance
        - Agronomic: Best practices adherence
        - Quality: Crop grades from belt
        - Commercial: Group participation
        """
        # Get member
        result = await db.execute(
            select(ChamaMember).where(ChamaMember.id == member_id)
        )
        member = result.scalar_one_or_none()
        
        if not member:
            raise ValueError(f"Member {member_id} not found")
        
        # Get SACCO account
        result = await db.execute(
            select(SACCOAccount).where(SACCOAccount.member_id == member_id)
        )
        account = result.scalar_one_or_none()
        
        # === FINANCIAL SCORE ===
        financial_score = 50.0
        if account:
            # Repayment rate
            repayment_component = account.loan_repayment_score * 0.6
            # Savings consistency
            savings_component = account.savings_consistency_score * 0.4
            financial_score = repayment_component + savings_component
        
        # === AGRONOMIC SCORE ===
        # In production: Pull from AgroPulse AI Calendar adherence
        agronomic_score = 75.0  # Placeholder
        
        # === QUALITY SCORE ===
        # In production: Average grade from grading belt
        quality_score = 80.0  # Placeholder (Grade A = 100, Grade B = 70, Reject = 30)
        average_grade = "A"
        
        # === COMMERCIAL SCORE ===
        # Count group buy participation
        group_buy_query = select(func.count(GroupBuy.id)).where(
            GroupBuy.chama_id == member.chama_id
        )
        result = await db.execute(group_buy_query)
        total_group_buys = result.scalar() or 0
        
        commercial_score = min(100, total_group_buys * 10)  # 10 points per participation
        
        # === CALCULATE TOTAL SCORE ===
        total_score = (
            financial_score * 0.35 +
            agronomic_score * 0.25 +
            quality_score * 0.25 +
            commercial_score * 0.15
        )
        
        # Determine certification level
        if total_score >= 90:
            certification = "5-Star"
        elif total_score >= 80:
            certification = "Platinum"
        elif total_score >= 70:
            certification = "Gold"
        elif total_score >= 60:
            certification = "Silver"
        else:
            certification = "Bronze"
        
        # Create blockchain-verifiable hash
        reputation_data = {
            "member_id": member_id,
            "total_score": total_score,
            "financial_score": financial_score,
            "agronomic_score": agronomic_score,
            "quality_score": quality_score,
            "commercial_score": commercial_score,
            "timestamp": datetime.utcnow().isoformat()
        }
        reputation_hash = hashlib.sha256(
            json.dumps(reputation_data, sort_keys=True).encode()
        ).hexdigest()
        
        # Store or update reputation score
        result = await db.execute(
            select(ReputationScore).where(
                ReputationScore.member_id == member_id
            ).order_by(ReputationScore.calculated_at.desc()).limit(1)
        )
        existing_score = result.scalar_one_or_none()
        
        reputation_score = ReputationScore(
            member_id=member_id,
            total_score=total_score,
            financial_score=financial_score,
            agronomic_score=agronomic_score,
            quality_score=quality_score,
            commercial_score=commercial_score,
            sacco_repayment_rate_percent=account.loan_repayment_score if account else 100.0,
            average_crop_grade=average_grade,
            total_group_buys_participated=total_group_buys,
            certification_level=certification,
            blockchain_reputation_hash=reputation_hash,
            calculated_at=datetime.utcnow(),
            next_calculation_at=datetime.utcnow() + timedelta(days=30)
        )
        db.add(reputation_score)
        
        # Update member
        member.reputation_score = total_score
        
        await db.commit()
        await db.refresh(reputation_score)
        
        return {
            "member_id": member_id,
            "total_score": round(total_score, 2),
            "certification_level": certification,
            "component_scores": {
                "financial": round(financial_score, 2),
                "agronomic": round(agronomic_score, 2),
                "quality": round(quality_score, 2),
                "commercial": round(commercial_score, 2)
            },
            "metrics": {
                "sacco_repayment_rate_percent": account.loan_repayment_score if account else 100.0,
                "average_crop_grade": average_grade,
                "group_buys_participated": total_group_buys,
                "years_of_membership": round(
                    (datetime.utcnow() - member.joined_date).days / 365, 1
                )
            },
            "blockchain_hash": reputation_hash,
            "farmer_passport": f"{certification} Certified Farmer with {round(total_score, 0)}% Trust Score",
            "message": f"🏆 {certification} Certification Achieved!"
        }


# Singleton instance
digital_chama_ai_service = DigitalChamaAIService()
